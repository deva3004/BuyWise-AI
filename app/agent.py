# app/agent.py
#
# Manual tool-calling loop, no framework. This is deliberately the
# unabstracted version of what LangGraph would later wrap: send messages +
# tool definitions -> if the model asks for a tool call, run it ourselves
# and feed the result back -> repeat until the model returns plain text.

import json
import os

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


def run_agent(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    for _ in range(MAX_TOOL_ITERATIONS):
        response = _client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content

        messages.append(message)

        for tool_call in message.tool_calls:
            result = _execute_tool_call(tool_call)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return "Reached the tool-call limit without a final answer."


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
