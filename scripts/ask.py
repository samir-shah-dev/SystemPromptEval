"""Ask the Wikipedia agent one question (CLI)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from system_prompt_eval.agent import run_agent  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one question through the Wikipedia agent.")
    parser.add_argument(
        "question",
        nargs="?",
        default=None,
        help="Question to ask (if omitted, read stdin)",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Anthropic model id (default: ANTHROPIC_MODEL env or claude-sonnet-4-6)",
    )
    args = parser.parse_args()
    q = args.question
    if q is None:
        q = sys.stdin.read().strip()
    if not q:
        parser.error("Provide a question as an argument or on stdin.")
    print(run_agent(q, model=args.model))


if __name__ == "__main__":
    main()
