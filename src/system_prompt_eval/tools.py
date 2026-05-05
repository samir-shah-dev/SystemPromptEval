"""Anthropic tool definitions and runtime handlers for the agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# Anthropic API expects a list of tool specs (name, description, input_schema).
SEARCH_WIKIPEDIA_TOOL: dict[str, Any] = {
    "name": "search_wikipedia",
    "description": (
        "Search English Wikipedia (en.wikipedia.org). Returns ranked titles, search snippets, and "
        "short lead-section extracts for the top hits when available. "
        "Call with focused keywords or natural-language queries; if results are empty or off-topic, "
        "reformulate and try again. Use multiple calls for multi-hop questions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (keywords or natural language).",
            },
        },
        "required": ["query"],
    },
}

TOOLS: list[dict[str, Any]] = [SEARCH_WIKIPEDIA_TOOL]

ToolHandler = Callable[[dict[str, Any]], str]


def default_tool_router(handlers: dict[str, ToolHandler]) -> ToolHandler:
    """Return a dispatcher that routes by tool name."""

    def route(tool_use: dict[str, Any]) -> str:
        name = tool_use.get("name", "")
        handler = handlers.get(name)
        if handler is None:
            return f"Unknown tool: {name}"
        return handler(tool_use)

    return route
