"""Load eval cases from YAML or JSONL (including HotpotQA- and KILT-shaped rows)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def _stable_id(question: str, explicit: str) -> str:
    if explicit.strip():
        return explicit.strip()
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest()[:12]
    return f"auto_{digest}"


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return []


def _gold_answer_from_row(row: dict[str, Any]) -> str | None:
    a = row.get("answer")
    if isinstance(a, str) and a.strip():
        return a.strip()
    if isinstance(a, list) and a:
        parts = [str(x).strip() for x in a if str(x).strip()]
        if parts:
            return " | ".join(parts)
    out = row.get("output")
    if isinstance(out, list) and out:
        first = out[0]
        if isinstance(first, dict) and isinstance(first.get("answer"), str):
            return first["answer"].strip()
        if isinstance(first, str) and first.strip():
            return first.strip()
    if isinstance(out, str) and out.strip():
        return out.strip()
    return None


def _gold_titles_hotpot(row: dict[str, Any]) -> list[str]:
    sf = row.get("supporting_facts")
    if not isinstance(sf, list):
        return []
    titles: list[str] = []
    for item in sf:
        if isinstance(item, (list, tuple)) and item and isinstance(item[0], str):
            t = item[0].strip()
            if t and t not in titles:
                titles.append(t)
    return titles


def _normalize_row(row: dict[str, Any]) -> EvalCase:
    """Map a dict from YAML, HotpotQA JSON, KILT JSONL, or a thin custom JSONL row."""
    question = row.get("question") if isinstance(row.get("question"), str) else None
    if not question and isinstance(row.get("input"), str):
        question = row["input"]
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"Case missing non-empty 'question' or 'input': keys={list(row)!r}")

    case_id = row.get("id") if isinstance(row.get("id"), str) else None
    if not case_id and isinstance(row.get("_id"), str):
        case_id = row["_id"]
    case_id = _stable_id(question.strip(), case_id or "")

    tags = _coerce_str_list(row.get("tags"))
    if not tags and isinstance(row.get("type"), str):
        tags = [row["type"]]
    if isinstance(row.get("meta"), dict):
        task = row["meta"].get("task") or row["meta"].get("dataset")
        if isinstance(task, str) and task and task not in tags:
            tags = [task, *tags]

    must_contain = _coerce_str_list(row.get("must_contain"))
    must_not_contain = _coerce_str_list(row.get("must_not_contain"))
    gold = _gold_answer_from_row(row)
    titles = _gold_titles_hotpot(row)
    if isinstance(row.get("gold_doc_titles"), list):
        titles = [*titles, *_coerce_str_list(row["gold_doc_titles"])]

    return EvalCase(
        id=case_id,
        question=question.strip(),
        tags=tags,
        must_contain=must_contain,
        must_not_contain=must_not_contain,
        gold_answer=gold,
        gold_doc_titles=titles,
        raw=row,
    )


@dataclass
class EvalCase:
    """Normalized case for running the agent and scoring."""

    id: str
    question: str
    tags: list[str] = field(default_factory=list)
    must_contain: list[str] = field(default_factory=list)
    must_not_contain: list[str] = field(default_factory=list)
    gold_answer: str | None = None
    gold_doc_titles: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def load_cases(path: Path) -> list[EvalCase]:
    """
    Load cases from ``.yaml`` / ``.yml`` (list of objects) or ``.jsonl`` (one JSON object per line).

    Supported row shapes:

    - **Our YAML / JSONL**: ``id``, ``question``, optional ``tags``, ``must_contain``, ``gold_answer``.
    - **HotpotQA-style**: ``_id``, ``question``, ``answer``, optional ``supporting_facts``.
    - **KILT-style**: ``id``, ``input`` (question), ``output`` (list with ``answer`` strings).
    """
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        raw = yaml.safe_load(path.read_text())
        rows = raw if isinstance(raw, list) else []
        return [_normalize_row(r) for r in rows if isinstance(r, dict)]

    if suffix == ".jsonl":
        cases: list[EvalCase] = []
        for line_no, line in enumerate(path.read_text().splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object per line")
            cases.append(_normalize_row(row))
        return cases

    if suffix == ".json":
        raw = json.loads(path.read_text())
        rows = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
        return [_normalize_row(r) for r in rows if isinstance(r, dict)]

    raise ValueError(f"Unsupported cases file type: {path} (use .yaml, .yml, .jsonl, or .json)")
