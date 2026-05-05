"""Heuristic scoring for eval cases (string checks + token F1 vs gold answer)."""

from __future__ import annotations

import re
import string
from collections import Counter
from typing import Any

from system_prompt_eval.eval_cases import EvalCase


def normalize_answer(text: str) -> str:
    """Lowercase, strip punctuation around tokens, collapse whitespace (lightweight QA norm)."""
    text = text.lower()
    text = re.sub(rf"[{re.escape(string.punctuation)}]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def token_f1(prediction: str, ground_truth: str) -> float:
    """SQuAD-style token overlap F1 on normalized token sequences."""
    pred_tokens = normalize_answer(prediction).split()
    gold_tokens = normalize_answer(ground_truth).split()
    if not gold_tokens:
        return 1.0 if not pred_tokens else 0.0
    if not pred_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(pred_tokens)
    recall = num_same / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def evaluate_case(
    case: EvalCase,
    answer: str,
    *,
    error: str | None = None,
    min_gold_f1: float = 0.5,
) -> dict[str, Any]:
    """
    Score one model answer against ``case``.

    - ``must_contain``: each phrase must appear as substring (case-insensitive).
    - ``must_not_contain``: none may appear (case-insensitive).
    - ``gold_answer``: pass if normalized exact match OR token F1 >= ``min_gold_f1``.
    - ``gold_doc_titles``: diagnostic only (fraction of titles appearing as substrings).
    """
    a_lower = answer.lower()
    out: dict[str, Any] = {
        "id": case.id,
        "passed": False,
        "skipped": False,
        "error": error,
        "must_contain_ok": True,
        "must_not_contain_ok": True,
        "gold_f1": None,
        "gold_pass": True,
        "titles_hit_frac": None,
    }

    if error:
        out["passed"] = False
        return out

    has_constraints = bool(
        case.must_contain or case.must_not_contain or case.gold_answer,
    )
    if not has_constraints:
        out["skipped"] = True
        out["passed"] = None
        if case.gold_doc_titles:
            hits = sum(1 for t in case.gold_doc_titles if t.lower() in a_lower)
            out["titles_hit_frac"] = round(hits / len(case.gold_doc_titles), 4)
        return out

    if case.must_contain:
        out["must_contain_ok"] = all(s.lower() in a_lower for s in case.must_contain)

    if case.must_not_contain:
        out["must_not_contain_ok"] = not any(s.lower() in a_lower for s in case.must_not_contain)

    if case.gold_answer:
        f1 = token_f1(answer, case.gold_answer)
        ng = normalize_answer(case.gold_answer)
        np_ = normalize_answer(answer)
        # Short gold strings often appear verbatim inside a longer free-form answer.
        # Require length >= 4 to avoid spurious hits (e.g. "no" inside "nothing").
        substring_pass = bool(ng) and len(ng) >= 4 and ng in np_
        out["gold_f1"] = round(f1, 4)
        out["gold_pass"] = (np_ == ng) or f1 >= min_gold_f1 or substring_pass
    else:
        out["gold_f1"] = None
        out["gold_pass"] = True

    if case.gold_doc_titles:
        hits = sum(1 for t in case.gold_doc_titles if t.lower() in a_lower)
        out["titles_hit_frac"] = round(hits / len(case.gold_doc_titles), 4)

    out["passed"] = (
        out["must_contain_ok"] and out["must_not_contain_ok"] and out["gold_pass"]
    )
    return out
