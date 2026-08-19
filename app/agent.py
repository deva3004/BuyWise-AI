# app/agent.py
#
# Manual tool-calling loop, no framework. This is deliberately the
# unabstracted version of what LangGraph would later wrap: send messages +
# tool definitions -> if the model asks for a tool call, run it ourselves
# and feed the result back -> repeat until the model calls submit_decision.

import json
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from groq import Groq

from app.tools import TOOL_DEFINITIONS, TOOL_REGISTRY

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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


def run_agent(user_message: str) -> AgentDecision:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    tools = TOOL_DEFINITIONS + [DECISION_TOOL_DEFINITION]

    for _ in range(MAX_TOOL_ITERATIONS):
        response = _client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return AgentDecision(
                decision="unable_to_decide",
                reasoning=message.content
                or "Model returned no tool calls and no decision.",
            )

        messages.append(message)

        for tool_call in message.tool_calls:
            if tool_call.function.name == "submit_decision":
                return _parse_decision(tool_call)

            result = _execute_tool_call(tool_call)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return AgentDecision(
        decision="unable_to_decide",
        reasoning="Reached the tool-call limit without a final decision.",
    )


def _parse_decision(tool_call) -> AgentDecision:
    try:
        args = json.loads(tool_call.function.arguments)
        return AgentDecision(decision=args["decision"], reasoning=args["reasoning"])
    except (json.JSONDecodeError, KeyError) as exc:
        return AgentDecision(
            decision="unable_to_decide",
            reasoning=f"Model's submit_decision call was malformed: {exc}",
        )


def _execute_tool_call(tool_call) -> dict:
    """The allowlist boundary: the model only ever proposes a name +
    arguments here. TOOL_REGISTRY decides what's actually permitted to
    run, and bad/missing args are caught before touching real code.
    """
    tool_fn = TOOL_REGISTRY.get(tool_call.function.name)
    if tool_fn is None:
        return {"error": f"Unknown tool: {tool_call.function.name}"}

    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return {"error": "Tool arguments were not valid JSON"}

    try:
        return tool_fn(**args)
    except TypeError as exc:
        return {"error": f"Invalid arguments for {tool_call.function.name}: {exc}"}
