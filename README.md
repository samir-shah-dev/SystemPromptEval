# SystemPromptEval

Wikipedia-grounded **Claude** agent: a **system prompt** plus the **`search_wikipedia`** tool (MediaWiki API). Includes an **eval harness** (`eval/cases.yaml`, JSONL loaders), **rule-based scoring** (`must_contain`, `gold_answer` token F1, optional **`gold_doc_titles` grounding**), optional **LLM-as-judge** (`--with-judge`), and Markdown **tag summaries**.

---

## Requirements

- **Python 3.11+**
- **Anthropic API key** ([Console](https://console.anthropic.com/))
- Outbound **HTTPS** to `api.anthropic.com` and `en.wikipedia.org` (when running the agent or network-marked tests)

---

## Setup

From the repository root, create a virtual environment and install the package (including dev dependencies for tests):

```bash
cd SystemPromptEval
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

After activation, the examples below use **`python`** (your venv’s interpreter).

---

## Configuration

Create a **`.env`** file in the project root (loaded automatically; optional but convenient):

```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
# Optional overrides:
# ANTHROPIC_MODEL=claude-sonnet-4-6
# ANTHROPIC_JUDGE_MODEL=claude-3-5-haiku-latest   # only used with --with-judge
```

| Variable | Purpose |
|----------|---------|
| **`ANTHROPIC_API_KEY`** | Required for any API call (agent, eval, judge). |
| **`ANTHROPIC_MODEL`** | Model ID for **`run_agent`** and **`run_eval`** (default in code: **`claude-sonnet-4-6`** if unset). |
| **`ANTHROPIC_JUDGE_MODEL`** | Model ID for **`--with-judge`** (defaults to **`ANTHROPIC_MODEL`** / Sonnet default if unset). |

You can instead `export` these in your shell; environment variables already set are not overwritten by `.env`.

---

## Run the agent (single question)

```bash
python scripts/ask.py "What is the capital of France?"
python scripts/ask.py -m claude-sonnet-4-6 "What is the chemical symbol for mercury?"
```

---

## Run the eval suite

The CLI loads cases from **`eval/cases.yaml`** by default (or pass **`--cases`** to a `.yaml` / `.jsonl` / `.json` file).

```bash
# Smoke check: load cases only (no API calls)
python eval/run_eval.py --dry-run

# Full suite — prints each answer and a Markdown tag summary (stdout)
python eval/run_eval.py

# Typical run: quiet, JSONL + tag summary on disk, full answers in JSONL
python eval/run_eval.py --quiet \
  --jsonl-out results/latest.jsonl \
  --tag-summary-md results/tag-summary.md \
  --truncate-answer 0

# First N cases only
python eval/run_eval.py --limit 3

# Optional LLM-as-judge (extra Anthropic call per non-skipped case)
python eval/run_eval.py --with-judge --quiet \
  --jsonl-out results/with-judge.jsonl \
  --tag-summary-md results/tag-summary.md \
  --truncate-answer 0
```

Useful flags (see **`python eval/run_eval.py --help`**):

| Flag | Meaning |
|------|---------|
| **`--cases`** | Path to cases file (YAML list or JSONL). |
| **`--dry-run`** | Load cases only. |
| **`--limit N`** | Run at most N cases. |
| **`-m` / `--model`** | Override agent model for this run. |
| **`--min-gold-f1`** | Threshold for **`gold_pass`** when **`gold_answer`** is set (default `0.5`). |
| **`--json-out`** | Write full results array as JSON. |
| **`--jsonl-out`** | Append one JSON object per line after each case. |
| **`--quiet`** | Short status lines (pair with JSON outputs to capture answers). |
| **`--truncate-answer`** | Max chars of answer in JSON export (`0` = no truncation). |
| **`--tag-summary-md`** | Write tag-grouped Markdown (pass rate, gold metrics, grounding; judge columns if **`--with-judge`**). |
| **`--with-judge`** | Run **`judge_score_case`** after each scored case (extra cost). |
| **`--judge-model`** | Judge model override for this run. |

The directory **`results/`** is gitignored; create it locally when writing outputs.

---

## Tests

```bash
pytest
```

By default, **`pytest`** excludes tests marked **`network`** (live Wikipedia). To run them:

```bash
pytest -m network
```

---

## Project layout (short)

| Path | Role |
|------|------|
| `src/system_prompt_eval/` | Agent (`agent.py`), prompts, tool spec, Wikipedia client, scoring, judge, eval loaders |
| `eval/run_eval.py` | Batch eval CLI |
| `eval/cases.yaml` | Default YAML eval cases |
| `scripts/ask.py` | Single-question CLI |
| `tests/` | Pytest suite |

More narrative context for write-ups is in **`LEARNINGS.md`**.

---

## Recommended run (reproduced results for this submission)

To regenerate the same style of **per-case results** and **tag-level summary** used in the write-up (full model answers, heuristic scores, and **LLM-as-judge** fields), run from the repository root with **`ANTHROPIC_API_KEY`** (and optional **`ANTHROPIC_MODEL`** / **`ANTHROPIC_JUDGE_MODEL`**) set:

```bash
python eval/run_eval.py --cases eval/cases.yaml --with-judge --quiet \
  --jsonl-out results/with-judge.jsonl --tag-summary-md results/tag-summary.md \
  --truncate-answer 0
```

This writes:

- **`results/with-judge.jsonl`** — one JSON object per line (`passed`, `gold_f1`, `grounding_score`, `judge_score`, …).
- **`results/tag-summary.md`** — Markdown table by tag (pass rate, gold metrics, grounding, judge aggregates).

**Cost note:** **`--with-judge`** calls Anthropic **twice per non-skipped case** (agent + judge). Omit **`--with-judge`** for a cheaper run that still fills heuristic columns and **`results/tag-summary.md`** (without judge columns).

Create **`results/`** locally if it does not exist; it remains **gitignored**.
