"""LLM-as-judge scoring via Anthropic Messages API (no tools)."""

from __future__ import annotations

import json
import re
from typing import Any

from anthropic import Anthropic

from system_prompt_eval.config import default_judge_model, load_project_env
from system_prompt_eval.eval_cases import EvalCase

load_project_env()

JUDGE_SYSTEM_PROMPT = """You grade answers to factual questions. You receive the question, an optional reference answer (gold), optional constraint hints, and the model's answer.

Rules:
- If a reference answer is provided, treat it as authoritative for factual claims unless it is clearly wrong or incomplete; the model may elaborate if still accurate.
- If no reference is provided, judge correctness from general knowledge.
- Penalize contradictions, serious factual errors, hedging that avoids answering when a direct answer was expected, and empty or nonsensical replies.
- Output ONLY valid JSON, no markdown fences, no extra text.

Schema:
{"score": <float 0.0-1.0>, "correct": <boolean>, "reason": <single concise sentence>}

Where score is overall answer quality for the question asked (1.0 = fully satisfies the question factually)."""


def _truncate(s: str, limit: int) -> str:
    if limit <= 0 or len(s) <= limit:
        return s
    return s[:limit] + "\n…[truncated for judge]"


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("no JSON object in judge response")
    return json.loads(m.group())


def judge_score_case(
    case: EvalCase,
    answer: str,
    *,
    client: Anthropic | None = None,
    model: str | None = None,
    error: str | None = None,
    max_answer_chars: int = 16_000,
) -> dict[str, Any]:
    """
    Call Anthropic once to score ``answer`` for ``case``.

    Returns keys: ``judge_score`` (0–1 or ``None``), ``judge_correct``, ``judge_reason``,
    ``judge_error`` (API/parse failure message when applicable).
    """
    base: dict[str, Any] = {
        "judge_score": None,
        "judge_correct": None,
        "judge_reason": None,
        "judge_error": None,
    }
    if error:
        base["judge_error"] = "skipped_judge: agent_error"
        return base

    client = client or Anthropic()
    resolved_model = model or default_judge_model()

    gold = case.gold_answer or ""
    gold_line = gold if gold.strip() else "(none provided — judge without gold)"

    must_c = ", ".join(case.must_contain) if case.must_contain else "(none)"
    must_nc = ", ".join(case.must_not_contain) if case.must_not_contain else "(none)"

    user_body = (
        f"case_id: {case.id}\n\n"
        f"Question:\n{case.question}\n\n"
        f"Reference answer (gold):\n{gold_line}\n\n"
        f"Hints — strings the automated checker required (must_contain): {must_c}\n"
        f"Hints — forbidden phrases (must_not_contain): {must_nc}\n\n"
        f"Model answer:\n{_truncate(answer, max_answer_chars)}"
    )

    try:
        msg = client.messages.create(
            model=resolved_model,
            max_tokens=1024,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_body}],
        )
        parts = [b for b in msg.content if b.type == "text"]
        raw = "".join(b.text for b in parts).strip()
        parsed = _extract_json_object(raw)
        score = parsed.get("score")
        correct = parsed.get("correct")
        reason = parsed.get("reason")

        out_score: float | None = None
        if isinstance(score, (int, float)):
            out_score = float(score)
            out_score = max(0.0, min(1.0, out_score))
        elif isinstance(score, str):
            try:
                out_score = max(0.0, min(1.0, float(score)))
            except ValueError:
                pass

        out_correct: bool | None = None
        if isinstance(correct, bool):
            out_correct = correct

        out_reason = reason.strip() if isinstance(reason, str) and reason.strip() else None

        base["judge_score"] = round(out_score, 4) if out_score is not None else None
        base["judge_correct"] = out_correct
        base["judge_reason"] = out_reason
        if base["judge_score"] is None:
            base["judge_error"] = "judge_parse: missing or invalid score field"
        return base
    except Exception as exc:  # noqa: BLE001
        base["judge_error"] = f"judge_api: {exc}"
        return base
