from pathlib import Path

import pytest

from system_prompt_eval.eval_cases import EvalCase, load_cases

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"


def test_load_yaml_cases():
    cases = load_cases(EVAL_DIR / "cases.yaml")
    assert len(cases) >= 1
    assert all(isinstance(c, EvalCase) for c in cases)
    fr = next(c for c in cases if c.id == "smoke_capital_france")
    assert "France" in fr.question
    assert "Paris" in fr.must_contain


def test_load_jsonl_hotpot_and_kilt_shapes():
    path = EVAL_DIR / "sample_hotpot_shape.jsonl"
    cases = load_cases(path)
    assert len(cases) == 2
    assert cases[0].id == "sample_hotpot_1"
    assert cases[0].gold_answer == "Paris"
    assert "France" in cases[0].gold_doc_titles
    assert cases[1].question == "Who wrote Hamlet?"
    assert cases[1].gold_answer == "William Shakespeare"
    assert "nq" in cases[1].tags


def test_jsonl_rejects_bad_line():
    bad = Path(__file__).parent / "_bad_cases.jsonl"
    bad.write_text('{"question": "ok", "id": "x"}\nnot-json\n')
    try:
        with pytest.raises(ValueError, match="invalid JSON"):
            load_cases(bad)
    finally:
        bad.unlink()
