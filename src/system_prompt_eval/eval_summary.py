"""Aggregate eval results by case tags for reporting."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def aggregate_by_tag(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Group scored (non-skipped) rows by tag.

    Cases with no tags are counted under ``"(untagged)"``.

    Each summary dict: ``tag``, ``n``, ``pass_rate``, ``accuracy``, ``avg_gold_f1``,
    ``avg_grounding``.

    - ``pass_rate``: fraction with ``passed`` True (composite checklist + gold gate).
    - ``accuracy``: fraction with ``gold_pass`` True among rows that have ``gold_f1``
      set (reference-answer subset); ``None`` if that subset is empty.
    - ``avg_gold_f1``: mean ``gold_f1`` over rows with ``gold_f1`` not ``None``;
      ``None`` if empty.
    - ``avg_grounding``: mean ``grounding_score`` over rows where it is not ``None``
      (cases with ``gold_doc_titles``); ``None`` if none.
    """
    tag_to_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        tags = row.get("tags")
        if not isinstance(tags, list) or not tags:
            tag_list = ["(untagged)"]
        else:
            tag_list = list(
                dict.fromkeys(str(t).strip() for t in tags if str(t).strip()),
            )
            if not tag_list:
                tag_list = ["(untagged)"]
        for t in tag_list:
            tag_to_rows[t].append(row)

    out: list[dict[str, Any]] = []
    for tag in sorted(tag_to_rows.keys(), key=lambda s: (s == "(untagged)", s.lower())):
        bucket = tag_to_rows[tag]
        scored = [r for r in bucket if r.get("skipped") is not True]
        n = len(scored)
        if n == 0:
            continue
        passed_n = sum(1 for r in scored if r.get("passed") is True)
        pass_rate = passed_n / n

        with_gold = [r for r in scored if r.get("gold_f1") is not None]
        if with_gold:
            gold_ok = sum(1 for r in with_gold if r.get("gold_pass") is True)
            accuracy = gold_ok / len(with_gold)
            avg_f1 = sum(float(r["gold_f1"]) for r in with_gold) / len(with_gold)
        else:
            accuracy = None
            avg_f1 = None

        with_ground = [r for r in scored if r.get("grounding_score") is not None]
        if with_ground:
            avg_gr = sum(float(r["grounding_score"]) for r in with_ground) / len(with_ground)
        else:
            avg_gr = None

        safe_tag = tag.replace("|", "\\|") if "|" in tag else tag
        out.append(
            {
                "tag": safe_tag,
                "n": n,
                "pass_rate": pass_rate,
                "accuracy": accuracy,
                "avg_gold_f1": avg_f1,
                "avg_grounding": avg_gr,
            }
        )
    return out


def tag_summary_markdown(rows: list[dict[str, Any]]) -> str:
    """Markdown table + footnotes explaining metrics."""
    stats = aggregate_by_tag(rows)
    lines: list[str] = [
        "## Summary by tag",
        "",
        "| Tag | N | Pass rate | Accuracy† | Avg gold F1‡ | Avg grounding§ |",
        "|-----|--:|----------:|----------:|-------------:|---------------:|",
    ]
    if not stats:
        lines.extend(["", "_No scored rows or no tags._"])
        return "\n".join(lines)

    for s in stats:
        pr = f"{100.0 * s['pass_rate']:.1f}%"
        acc = "—" if s["accuracy"] is None else f"{100.0 * s['accuracy']:.1f}%"
        f1 = "—" if s["avg_gold_f1"] is None else f"{s['avg_gold_f1']:.3f}"
        gr = "—" if s["avg_grounding"] is None else f"{s['avg_grounding']:.3f}"
        lines.append(f"| {s['tag']} | {s['n']} | {pr} | {acc} | {f1} | {gr} |")

    lines.extend(
        [
            "",
            "† **Accuracy**: among cases in this tag that have a **`gold_answer`** (so `gold_f1` "
            "was computed), the fraction where **`gold_pass`** is true (token-F1 / EM-style gate only). "
            "Cases without gold are omitted from this column.",
            "",
            "‡ **Avg gold F1**: mean token-overlap F1 vs **`gold_answer`** over the same gold subset; "
            "“—” when no gold-backed cases exist for the tag.",
            "",
            "**Pass rate**: fraction of scored cases (including those without gold) for which the "
            "**composite** check passed (`must_contain`, `must_not_contain`, and `gold_pass` when applicable).",
            "",
            "§ **Avg grounding**: mean **`grounding_score`** over cases in this tag that define "
            "**`gold_doc_titles`** (benchmark article titles). Each per-case score is the fraction of "
            "those titles that appear as substrings in the model answer (lexical overlap, not semantic "
            "entailment). “—” when no cases in the tag carry title lists.",
        ]
    )
    return "\n".join(lines)
