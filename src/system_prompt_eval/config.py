"""Load local project configuration from the repo root."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# src/system_prompt_eval/config.py -> parents[2] == repository root
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def default_claude_model() -> str:
    """Model id from ``ANTHROPIC_MODEL`` or a current Sonnet default."""
    return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def default_judge_model() -> str:
    """Model for LLM-as-judge; ``ANTHROPIC_JUDGE_MODEL`` or same default as the agent."""
    return os.environ.get("ANTHROPIC_JUDGE_MODEL") or default_claude_model()


def load_project_env() -> None:
    """
    Load a ``.env`` file at the project root into the process environment.

    Variables already set in the environment are not overridden (shell export wins).
    """
    load_dotenv(PROJECT_ROOT / ".env")
