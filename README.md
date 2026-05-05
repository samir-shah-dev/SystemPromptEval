# SystemPromptEval

Wikipedia-grounded agent (system prompt + `search_wikipedia` tool) and an eval suite.

## Setup

```bash
cd /Users/samirshah/code/personal-ai/SystemPromptEval
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=...
```

## Layout

See package `src/system_prompt_eval/` and `eval/` for structure.
