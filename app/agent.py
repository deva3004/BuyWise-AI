# app/agent.py
#
# Manual tool-calling loop, no framework. This is deliberately the
# unabstracted version of what LangGraph would later wrap: send messages +
# tool definitions -> if the model asks for a tool call, run it ourselves
# and feed the result back -> repeat until the model calls submit_decision.

import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from dotenv import load_dotenv
from groq import Groq
from pydantic import ValidationError

from app.schemas import SearchOffersArgs, SearchPoliciesArgs, SubmitDecisionArgs
from app.tools import TOOL_DEFINITIONS, TOOL_REGISTRY

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# One JSON line per completed run — run_id, the tool-call/result sequence,
# and the final decision. stdout/log-stream, not a DB table: cheapest
# option that still gives the eval harness (Phase 4, next) something to
# read runs back from, with no schema/migration to maintain for a 15-day
# scope.
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("agent")

MODEL_NAME = "openai/gpt-oss-20b"

# Hard cap on tool-call round trips. Without this, a model that keeps
# calling tools (bad args, confused reasoning, etc.) loops forever and
# racks up API calls with no way out.
MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = (
    "You are a shopping decision agent. Use the available tools to look up "
    "offers and seller policies, then finish by calling submit_decision "
    "with one of BUY, WAIT, or RE-EVALUATE and your reasoning. Offers "
    "returned by search_offers have already been filtered against hard "
    "seller-eligibility rules (rating, blocked status) — never second-guess "
    "or override that filtering yourself. You must call submit_decision to "
    "finish; do not answer in plain text."
)

# Not a real action — never registered in TOOL_REGISTRY. The loop
# intercepts a call to this tool by name instead of executing it, and
# treats its arguments as the agent's final structured answer.
DECISION_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "submit_decision",
        "description": "Submit the final BUY/WAIT/RE-EVALUATE decision with reasoning. Call this to end the conversation.",
        "parameters": {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["BUY", "WAIT", "RE-EVALUATE"],
                },
                "reasoning": {"type": "string"},
            },
            "required": ["decision", "reasoning"],
        },
    },
}


@dataclass
class AgentDecision:
    decision: str
    reasoning: str


# Strict mode: an LLM sending "42" instead of 42 for variant_id is exactly
# the kind of drift this boundary exists to catch, not silently coerce.
TOOL_ARG_MODELS = {
    "search_offers": SearchOffersArgs,
    "search_policies": SearchPoliciesArgs,
    "submit_decision": SubmitDecisionArgs,
}


def run_agent(user_message: str) -> AgentDecision:
    trace = {
        "run_id": str(uuid.uuid4()),
        "user_message": user_message,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "events": [],
    }

    def finish(decision: AgentDecision) -> AgentDecision:
        trace["decision"] = decision.decision
        trace["reasoning"] = decision.reasoning
        trace["ended_at"] = datetime.now(timezone.utc).isoformat()
        _logger.info(json.dumps(trace))
        return decision

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    tools = TOOL_DEFINITIONS + [DECISION_TOOL_DEFINITION]

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = _client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return finish(AgentDecision(
                decision="unable_to_decide",
                reasoning=message.content
                or "Model returned no tool calls and no decision.",
            ))

        messages.append(message)

        for tool_call in message.tool_calls:
            if tool_call.function.name == "submit_decision":
                decision = _parse_decision(tool_call)
                trace["events"].append({
                    "iteration": iteration,
                    "tool": tool_call.function.name,
                    "args": tool_call.function.arguments,
                    "result": {"decision": decision.decision, "reasoning": decision.reasoning},
                })
                return finish(decision)

            result = _execute_tool_call(tool_call)
            trace["events"].append({
                "iteration": iteration,
                "tool": tool_call.function.name,
                "args": tool_call.function.arguments,
                "result": result,
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return finish(AgentDecision(
        decision="unable_to_decide",
        reasoning="Reached the tool-call limit without a final decision.",
    ))


def _validate_tool_args(tool_call) -> tuple[dict | None, dict | None]:
    """Shared validation boundary for every tool call, real or terminal.
    Returns (parsed_args, None) on success or (None, error_dict) on
    failure. A JSON-Schema in TOOL_DEFINITIONS is only a hint to the model
    — nothing enforces it on the way back until this runs.
    """
    model_cls = TOOL_ARG_MODELS.get(tool_call.function.name)
    if model_cls is None:
        return None, {"error": f"Unknown tool: {tool_call.function.name}"}

    try:
        raw = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return None, {"error": "Tool arguments were not valid JSON"}

    try:
        parsed = model_cls.model_validate(raw)
    except ValidationError as exc:
        return None, {"error": _format_validation_error(tool_call.function.name, exc)}

    return parsed.model_dump(), None


def _format_validation_error(tool_name: str, exc: ValidationError) -> str:
    first = exc.errors()[0]
    field = ".".join(str(loc) for loc in first["loc"])
    return f"Invalid arguments for {tool_name}: {field} - {first['msg']}"


def _parse_decision(tool_call) -> AgentDecision:
    args, error = _validate_tool_args(tool_call)
    if error is not None:
        return AgentDecision(decision="unable_to_decide", reasoning=error["error"])

    return AgentDecision(decision=args["decision"], reasoning=args["reasoning"])


def _execute_tool_call(tool_call) -> dict:
    """The allowlist boundary: the model only ever proposes a name +
    arguments here. TOOL_REGISTRY decides what's actually permitted to
    run, and _validate_tool_args catches bad args (structural or typed)
    before touching real code.
    """
    tool_fn = TOOL_REGISTRY.get(tool_call.function.name)
    if tool_fn is None:
        return {"error": f"Unknown tool: {tool_call.function.name}"}

    args, error = _validate_tool_args(tool_call)
    if error is not None:
        return error

    try:
        return tool_fn(**args)
    except TypeError as exc:
        # Defensive fallback only — Pydantic validation above should catch
        # anything that would land here first.
        return {"error": f"Invalid arguments for {tool_call.function.name}: {exc}"}
