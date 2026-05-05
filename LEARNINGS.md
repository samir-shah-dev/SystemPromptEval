# Learnings: Wikipedia-grounded agent & eval (collaborative build narrative)

This document is for your **written and video** deliverables. It has two layers: (1) **how I steered the work** by prompting an AI coding assistant from a blank folder, and (2) **what we built** and what that taught us technically.

---

## Checkpoint — 2026-05-03

**Status:** Working end-to-end agent (`run_agent` + `search_wikipedia` via MediaWiki), eval CLI (`run_eval.py`) with YAML/JSONL cases, **rule-based scoring** in `scoring.py`, results export (`--json-out` / `--jsonl-out`), stress cases in `eval/cases.yaml`, and this narrative doc through Part F.

**Superseded by later work (see Journal):** prompt was expanded **2026-05-04**; iterate prompts against the same case file and compare JSONL runs.

**Use this checkpoint** as a cut for your video (“here’s everything that existed when we froze the engineering story”) or as chapter 1 before later journal entries.

---

## Checkpoint — 2026-05-03 (v0.2.0)

**Status:** Eval cases in YAML include **`gold_answer`** and **`gold_doc_titles`** for stress and hard rows; **`eval_cases.py`** loads **`gold_answer`** correctly (it previously only mapped Hotpot-style **`answer`**, so **`gold_f1`** was always unset for YAML runs). **`eval_summary.py`** drives a Markdown **tag summary** (`--tag-summary-md`): pass rate, **Accuracy**, **Avg gold F1**, and **Avg grounding** (title substring overlap in the model answer). **`scoring.py`** exposes **`grounding_score`** from **`gold_doc_titles`**. Repository snapshot tagged **`v0.2.0`**.

---

## How this doc is maintained (journal convention)

- New **dated sections** go under **Journal** at the bottom (newest first or oldest first—pick one and stay consistent; we use **newest at top** below).
- After substantive milestones, add a new **Checkpoint — YYYY-MM-DD** block *above* the Journal (or refresh this section) so the final **video script** can be assembled from checkpoints + journal bullets.
- The AI assistant should **append** journal notes when you ask for updates (“keep learnings current”) so the file stays a single timeline.

---

## Journal (newest first)

### 2026-05-04 — Rich system prompt + Wikipedia lead extracts

- Replaced the stub **`SYSTEM_PROMPT`** with explicit guidance: when to call **`search_wikipedia`**, query reformulation and **multi-call multi-hop**, how to use snippets vs synthesized answers with light attribution, and honesty when retrieval is empty or weak.
- Expanded the **`search_wikipedia`** tool **description** in `tools.py` to mention lead extracts and multiple calls.
- Upgraded **`wikipedia.py`**: after **`list=search`**, fetch **`prop=extracts`** (intro, plain text, truncated) for the top hits so tool output carries **lead paragraphs**, not only snippets— improves grounding for the eval suite.

### 2026-05-03 — Gold-backed metrics, YAML loader fix, tag summary

- **`eval_cases.py`:** **`_gold_answer_from_row`** now honors our YAML field **`gold_answer`** (Hotpot rows still use **`answer`**). Without this, **`gold_f1`** stayed **`null`** for every YAML case, so the tag table showed **—** for **Accuracy** and **Avg gold F1** even when cases defined gold text.
- **`eval_summary.py`** + **`run_eval.py --tag-summary-md`:** per-tag **pass rate**, **Accuracy** (share of **`gold_pass`** among rows with computed **`gold_f1`**), **Avg gold F1**, and **Avg grounding** (mean **`grounding_score`** from **`gold_doc_titles`** substring hits).
- **`eval/cases.yaml`:** reference **`gold_answer`** and **`gold_doc_titles`** added across smoke, stress, and hard cases so aggregates are meaningful.
- **`scoring.py`:** **`grounding_score`** / **`titles_hit_frac`** derived from **`gold_doc_titles`**.
- Release snapshot: git tag **`v0.2.0`**.

### 2026-05-03 — Scoring methodology documented; checkpoint formalized

- Captured **what our automatic grading is called** (see **Part G**) so the write-up can use standard terminology: heuristic / constraint checks + lexical F1, not LLM-as-judge.
- Established **checkpoint + journal** structure for ongoing updates toward a **video script**.

---

## Part A — How we worked together (prompting and iteration)

### A.1 Starting from the assignment

I pasted the take-home brief (design **system prompt + tool**, wire **Wikipedia**, build **eval suite**) and asked **what to do first**. The assistant recommended a **spike** first: prove Wikipedia retrieval works in code before locking the tool contract—then formalize the prompt and tool schema, then automate grading.

**Learning:** “Spike” meant a **short feasibility experiment** (e.g. Python calling the MediaWiki API), not “try it in Claude chat.” That reduced rework.

### A.2 Clarifying terms before coding

I asked what **“spike”** meant and whether I should use Claude web vs Python. That clarified we should use **real code** in the repo so imports, keys, and error paths behave like production.

### A.3 Scaffolding the repo and understanding it

I asked to **create the project** and discuss **structure**. We added a `src/system_prompt_eval/` package (`prompts`, `tools`, `wikipedia`, `agent`), `eval/` for cases and CLI, `tests/`, and `pyproject.toml`. Then I asked for a **slow file-by-file explanation** and **which file to run first**—that produced the mental model: implement **`wikipedia.py`** first for real data; **`eval/run_eval.py`** only loads YAML until wired; **`scripts/ask.py`** for one-off questions once `run_agent` works.

**Iteration:** Concepts before automation—I understood entrypoints before pouring cases into a harness.

### A.4 Deep dives when confused

I requested **`run_eval.py` line-by-line** (imports first) and later asked **why YAML**. Those pauses turned into durable notes: `yaml.safe_load` + human-readable case lists + comments; `argparse` + `Path` + `sys.path` so the eval script runs without a global `pip install` in some workflows.

### A.5 Small quality-of-life requests

- **`ask.py`** so I could run a single question from the terminal.  
- **`.env` support** for `ANTHROPIC_API_KEY` (and later `ANTHROPIC_MODEL`) so keys are not only shell exports. I also asked about **quotes in `.env`**—we confirmed plain `KEY=value` is standard.  
- When the **venv was missing**, the fix was to **create `.venv` in the project** and `pip install -e .`—not an AI-only step; the assistant could scaffold commands but the environment is local.

### A.6 Debugging “it doesn’t run”

When **`ask.py` threw many errors**, we iterated until it worked:

| Symptom | What we changed |
|--------|------------------|
| Wrong / deprecated **model id** | Default to a **current** Claude API model; optional **`ANTHROPIC_MODEL`** in `.env`. |
| **400 / invalid Messages payload** after tool use | Match Anthropic’s pattern: pass **`msg.content`** back for the assistant turn; send **`tool_result`** `content` as **text blocks**, not a lone raw string. |
| Tool code crashing | **`try/except`** in the tool handler returns an **error string** to the model instead of killing the whole script. |

After it ran, I asked **what exactly was fixed**—good practice for documentation (snapshot for reviewers).

### A.7 Evaluation strategy questions

I shifted toward **evaluating the system prompt** and asked whether **public datasets** exist (HotpotQA, KILT, etc.). We aligned on: **no dataset is “system prompt eval only,”** but benchmarks supply **questions + optional gold**; we normalize rows into **`EvalCase`**.

I asked whether we had **multi-hop support**. Answer for this codebase: **multi-turn tool loops** yes (model may call the tool many times); **no bespoke Python multi-hop planner**.

When I said **“go ahead,”** we wired **`run_agent`** into **`run_eval.py`**, added **`scoring.py`**, and flags for **JSON / JSONL**, **quiet** logging, and **full-answer** printing so I could see failures.

### A.8 Making the suite stress the system

The suite **passed 100%** on early cases, so I asked to **add cases that fail**—we added “hard” rows (exact numerics, long lists, strict substrings, `must_not_contain`). That exposed a key lesson: **string match ≠ semantic correctness** (e.g. speed of light: model wrote `299,792,458` but the check required `299792458` → **`must_contain_ok: false`**).

### A.9 Wikipedia “unavailable” in answers

I asked **why the model said Wikipedia was unavailable** even though the API key worked. Root cause: **`search_wikipedia` was still a stub** (`NotImplementedError`); the agent fed the model an error string, which the model paraphrased politely. We **implemented** the English Wikipedia **search API** with `httpx` and a proper **User-Agent**.

### A.10 Tests and visibility

I asked where **live test output** went and why **pytest showed no text** on pass. We learned: **pytest captures stdout**; use **`pytest -s`**, and a smoke test can **`print`** the tool output for inspection. The result is **not** written to `results/` unless the eval harness or a script does so.

### A.11 Artifacts for the submission

I asked for a **learnings document** (this file), then asked to **redo** it to include **how I prompted and how we iterated**—hence **Part A** and the timeline style above.

### A.12 Checkpoint, journal habit, and naming the scoring approach

I asked to **mark a checkpoint** in this doc, keep **journal-style updates** as we go (for a future **video script**), and to explain **how scoring works** and what it is called—leading to **Part G** and the dated **Journal** section above.

---

## Part B — What the assignment is asking for (technical)

Three pillars:

1. **Design** — A **system prompt** (when/how to use Wikipedia) and a **tool definition** (the structured `name` / `description` / `input_schema` passed to `messages.create(..., tools=...)`). The tool definition lives in `src/system_prompt_eval/tools.py`; the system prompt in `src/system_prompt_eval/prompts.py` (still the main place to **iterate** for behavior).
2. **Integration** — Real Wikipedia: `src/system_prompt_eval/wikipedia.py` calls the **MediaWiki** `action=query&list=search` API and returns titles + cleaned snippets.
3. **Evaluation** — `eval/cases.yaml` (and optional JSONL), `eval_cases.py` for loading, `scoring.py` for checks, `eval/run_eval.py` to run the agent and aggregate **pass / fail**.

---

## Part C — Repository map (what we built)

| Piece | Role |
|--------|------|
| `prompts.py` | `SYSTEM_PROMPT` |
| `tools.py` | Tool specs for the Anthropic API |
| `wikipedia.py` | `search_wikipedia(query)` implementation |
| `agent.py` | Tool loop: `tool_use` → execute → `tool_result` → repeat |
| `config.py` | Load `.env`; default model helper |
| `eval_cases.py` | YAML / JSONL → `EvalCase` |
| `scoring.py` | `must_contain`, `must_not_contain`, `gold_answer` heuristics, `gold_doc_titles` grounding |
| `eval_summary.py` | Aggregate by tag → Markdown table (`tag_summary_markdown`) |
| `eval/run_eval.py` | Batch eval CLI (`--json-out`, `--jsonl-out`, `--quiet`, `--tag-summary-md`, …) |
| `scripts/ask.py` | Single-question CLI |

---

## Part D — Pitfalls we discovered (short list)

- **Tool message shapes** must match what the Anthropic SDK expects after tool calls.  
- **Model IDs** must match what your API account supports.  
- **Substring grading** is strict: formatted numbers can fail “exact digit string” checks.  
- **Live Wikipedia** vs benchmark snapshots: articles change; gold provenance can drift.  
- **Scale:** use **`--jsonl-out`** for long runs; **`--quiet`** for terminals; **`--truncate-answer`** only affects file export if set.

---

## Part E — Suggested storyline for your video

1. **Assignment** → three deliverables (prompt+tool, integration, eval).  
2. **Process** → spike retrieval, scaffold repo, ask “dumb” questions on purpose (YAML, line-by-line), fix runtime errors methodically.  
3. **Artifact** → tool definition in code vs prose in system prompt.  
4. **Evaluation** → start easy, add stress cases, watch pass rate move; interpret failures (metric vs model).  
5. **Integration reality** → stub vs real API; User-Agent; costs/latency on big suites.  
6. **How you used AI** → steering with explicit questions, requesting explanations, then requesting features (`ask.py`, `.env`, JSONL), and validating outputs yourself (pytest `-s`, reading `results/*.jsonl`).

---

## Part F — Files worth showing on screen

- `tools.py` / `prompts.py` — design.  
- `wikipedia.py` — integration.  
- `agent.py` — orchestration.  
- `eval/cases.yaml` — cases + difficulty ramp.  
- `results/*.jsonl` — per-case `passed`, `must_contain_ok`, answers, errors.

---

## Part G — How answers are scored (and what to call this technique)

Implementation: `src/system_prompt_eval/scoring.py` (`evaluate_case`).

### G.1 High-level name (for your report or video)

This is **automated, rule-based (heuristic) evaluation** of model outputs. It is **not**:

- **LLM-as-judge** (no second model rates the answer),
- **Human preference** or rubric studies,
- **Semantic similarity** (no embeddings; we do not measure cosine similarity of meanings),
- **Standard BLEU/ROUGE** (we did not use those).

It **is** a mix of:

1. **Constraint satisfaction / checklist scoring** — each `must_contain` string must appear somewhere in the answer (case-insensitive **substring** match); each `must_not_contain` string must **not** appear. Think **binary constraints** glued with AND.
2. **Lexical overlap vs a reference** — when `gold_answer` is set, we use **normalized text + token overlap**, in the same family as **reading-comprehension benchmarks**:
   - **Light normalization** (lowercase, strip punctuation to spaces, collapse whitespace) then **exact match** on the normalized string (“EM-style” exactness).
   - **Token-level F1** between prediction and `gold_answer` using bag-of-token overlap (implementation matches the spirit of **SQuAD / extractive QA F1**, often called **token F1** in papers).
   - A **relaxed substring** rule: if the normalized gold string is **long enough** (≥ 4 characters) and appears as a **substring** of the normalized prediction, we treat that as pass (helps short factual phrases embedded in a longer answer).

**Optional diagnostic (does not decide pass/fail by default):** `gold_doc_titles` → fraction of titles that appear as substrings in the answer (“soft retrieval overlap” proxy).

### G.2 When a case passes

For a **non-skipped** case: **`passed`** is true only if **`must_contain_ok` AND `must_not_contain_ok` AND `gold_pass`** are all true. Tool/API errors mark the case failed regardless of text.

### G.3 Aggregate “score” you see in the CLI

**Pass rate** = (number of constrained cases with `passed == true`) / (number of cases that are not **skipped**). Skipped rows have no `must_contain` / `must_not_contain` / `gold_answer`, so they do not affect that ratio.

**Tag summary** (optional Markdown from `eval_summary.py`): for each tag, **Accuracy** and **Avg gold F1** use only rows where **`gold_f1`** was computed (YAML **`gold_answer`** must load into **`EvalCase`**). **Avg grounding** averages **`grounding_score`** over cases that define **`gold_doc_titles`**.

### G.4 Known limitations (honest for the video)

- **Substring constraints** can reject **correct** answers if formatting differs (e.g. required `299792458` vs answered `299,792,458`).
- **Token F1** rewards shared words, not truth—dangerous if the model is confidently wrong but lexical overlap is high; combine with careful gold phrasing or human spot checks for important demos.

---

*Use this as a draft for your narrative; cite datasets, API terms of use, and model providers per your course or employer requirements.*
