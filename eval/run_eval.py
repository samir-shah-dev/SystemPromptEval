"""Load eval cases, run the agent, score answers (CLI)."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

# Repo root on path when running `python eval/run_eval.py` without install
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from system_prompt_eval.agent import run_agent  # noqa: E402
from system_prompt_eval.eval_cases import load_cases  # noqa: E402
from system_prompt_eval.eval_summary import tag_summary_markdown  # noqa: E402
from system_prompt_eval.scoring import evaluate_case  # noqa: E402


def _maybe_truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    return text[:limit] + "…[truncated]"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Wikipedia agent eval suite.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).parent / "cases.yaml",
        help="Eval cases: .yaml / .yml (list), or .jsonl / .json (HotpotQA, KILT, or custom rows)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only load cases; do not call the API",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run at most this many cases (order preserved)",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Anthropic model id (default: ANTHROPIC_MODEL env or project default)",
    )
    parser.add_argument(
        "--min-gold-f1",
        type=float,
        default=0.5,
        help="Pass gold_answer check if token F1 >= this (or exact match after normalize)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="After the run, write all per-case results as a JSON array to this path",
    )
    parser.add_argument(
        "--jsonl-out",
        type=Path,
        default=None,
        help="Write one JSON object per line after each case (good for 100+; survives partial runs)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Terse terminal log (no full answer dump); use with --json-out or --jsonl-out",
    )
    parser.add_argument(
        "--truncate-answer",
        type=int,
        default=4000,
        help="Max characters of model answer in JSON output (0 = no limit)",
    )
    parser.add_argument(
        "--max-preview-chars",
        type=int,
        default=0,
        help="Trim answer text in the terminal log (0 = print full answer; use e.g. 500 for short logs)",
    )
    parser.add_argument(
        "--tag-summary-md",
        type=Path,
        default=None,
        help="Also write tag-grouped Markdown summary (pass rate, gold accuracy, avg F1, avg grounding) to this path",
    )
    args = parser.parse_args()

    def _export_row(r: dict[str, object]) -> dict[str, object]:
        d = dict(r)
        if isinstance(d.get("answer"), str):
            d["answer"] = _maybe_truncate(d["answer"], args.truncate_answer)
        return d

    cases = load_cases(args.cases)
    print(f"Loaded {len(cases)} cases from {args.cases}")
    if args.dry_run:
        return

    if args.limit is not None:
        cases = cases[: max(0, args.limit)]

    jsonl_fp = None
    if args.jsonl_out:
        args.jsonl_out.parent.mkdir(parents=True, exist_ok=True)
        jsonl_fp = args.jsonl_out.open("w", encoding="utf-8")

    results: list[dict[str, object]] = []
    try:
        for i, case in enumerate(cases, start=1):
            print(f"[{i}/{len(cases)}] {case.id} …", flush=True)
            answer = ""
            err: str | None = None
            try:
                answer = run_agent(case.question, model=args.model)
            except Exception:
                err = traceback.format_exc(limit=3)

            score = evaluate_case(case, answer, error=err, min_gold_f1=args.min_gold_f1)
            row: dict[str, object] = {
                "id": case.id,
                "question": case.question,
                "answer": answer,
                "tags": case.tags,
                "gold_doc_titles": case.gold_doc_titles,
                **score,
            }
            results.append(row)

            if jsonl_fp is not None:
                jsonl_fp.write(json.dumps(_export_row(row), ensure_ascii=False) + "\n")
                jsonl_fp.flush()

            if score.get("skipped"):
                status = "SKIP"
            elif err:
                status = "ERROR"
            elif score.get("passed"):
                status = "PASS"
            else:
                status = "FAIL"

            if args.quiet:
                peek = _maybe_truncate(answer.replace("\n", " "), 100)
                tail = f"  {peek!r}" if peek else ""
                print(f"    -> {status}{tail}", flush=True)
                if err:
                    print(_maybe_truncate(err, 1200), flush=True)
            else:
                print(f"    -> {status}", flush=True)
                if err:
                    print(err, flush=True)
                else:
                    body = (
                        answer
                        if args.max_preview_chars <= 0
                        else _maybe_truncate(answer, args.max_preview_chars)
                    )
                    print("    --- answer ---", flush=True)
                    if not body:
                        print("    (empty)", flush=True)
                    else:
                        for line in body.splitlines():
                            print(f"    {line}", flush=True)
                    print("    --- end answer ---", flush=True)
    finally:
        if jsonl_fp is not None:
            jsonl_fp.close()
            print(f"Wrote {args.jsonl_out} ({len(results)} lines)", flush=True)

    skipped = [r for r in results if r.get("skipped") is True]
    scored = [r for r in results if r.get("skipped") is not True]
    passed = [r for r in scored if r.get("passed") is True]
    print()
    print(f"Cases run: {len(results)}  (skipped, no scoring constraints: {len(skipped)})")
    if scored:
        pct = 100.0 * len(passed) / len(scored)
        print(f"Pass rate (constrained cases): {len(passed)}/{len(scored)} ({pct:.1f}%)")

    tag_md = tag_summary_markdown([dict(r) for r in results])
    print()
    print(tag_md)
    if args.tag_summary_md:
        args.tag_summary_md.parent.mkdir(parents=True, exist_ok=True)
        args.tag_summary_md.write_text(tag_md + "\n", encoding="utf-8")
        print(f"\nWrote tag summary {args.tag_summary_md}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        export = [_export_row(r) for r in results]
        args.json_out.write_text(json.dumps(export, indent=2, ensure_ascii=False) + "\n")
        print(f"Wrote {args.json_out}")


if __name__ == "__main__":
    main()
