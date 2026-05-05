"""Single-turn or multi-turn agent loop with Anthropic tool_use."""

from __future__ import annotations

from typing import Any

from anthropic import Anthropic

from system_prompt_eval.config import default_claude_model, load_project_env
from system_prompt_eval.prompts import SYSTEM_PROMPT
from system_prompt_eval.tools import TOOLS, default_tool_router
from system_prompt_eval.wikipedia import search_wikipedia

load_project_env()


def _search_tool_handler(tool_use: dict[str, Any]) -> str:
    args = tool_use.get("input") or {}
    q = args.get("query", "")
    if not isinstance(q, str) or not q.strip():
        return "Error: missing or empty query."
    try:
        return search_wikipedia(q.strip())
    except Exception as exc:  # noqa: BLE001 — return error text to the model
        return f"search_wikipedia failed: {exc}"


def run_agent(
    user_message: str,
    *,
    client: Anthropic | None = None,
    model: str | None = None,
    max_tool_rounds: int = 8,
) -> str:
    """
    Run until the model returns text (no further tool_use) or max_tool_rounds.

    TODO: wire full message history + tool_result blocks.
    """
    client = client or Anthropic()
    resolved_model = model or default_claude_model()
    router = default_tool_router({"search_wikipedia": _search_tool_handler})

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
    for _ in range(max_tool_rounds):
        msg = client.messages.create(
            model=resolved_model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        if msg.stop_reason == "end_turn":
            parts = [b for b in msg.content if b.type == "text"]
            return "".join(b.text for b in parts)

        if msg.stop_reason != "tool_use":
            parts = [b for b in msg.content if b.type == "text"]
            return "".join(b.text for b in parts) or f"Stopped: {msg.stop_reason}"

        tool_results: list[dict[str, Any]] = []
        for block in msg.content:
            if block.type != "tool_use":
                continue
            result_text = router({"name": block.name, "input": block.input})
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": [{"type": "text", "text": result_text}],
                }
            )

        # Pass assistant blocks through as returned by the API (see anthropic-sdk examples/tools.py).
        messages.append({"role": "assistant", "content": msg.content})
        messages.append({"role": "user", "content": tool_results})

    return "Error: exceeded max_tool_rounds without a final answer."
