from system_prompt_eval.eval_cases import EvalCase
from system_prompt_eval.scoring import evaluate_case, token_f1


def test_token_f1_exact():
    assert token_f1("Paris", "paris") == 1.0


def test_must_contain_and_gold():
    case = EvalCase(
        id="t1",
        question="q",
        must_contain=["Paris"],
        gold_answer="Paris",
    )
    r = evaluate_case(case, "The capital is Paris.", error=None)
    assert r["passed"] is True
    assert r["must_contain_ok"] is True
    assert r["gold_pass"] is True


def test_must_not_contain():
    case = EvalCase(
        id="t2",
        question="q",
        must_not_contain=["WRONG"],
    )
    assert evaluate_case(case, "ok", error=None)["passed"] is True
    assert evaluate_case(case, "this is WRONG", error=None)["passed"] is False


def test_skipped_when_no_constraints():
    case = EvalCase(id="t3", question="q", tags=["x"])
    r = evaluate_case(case, "anything", error=None)
    assert r["skipped"] is True
    assert r["passed"] is None


def test_error_fails():
    case = EvalCase(id="t4", question="q", must_contain=["a"])
    r = evaluate_case(case, "", error="boom")
    assert r["passed"] is False
    assert "boom" in r["error"]
    assert r["grounding_score"] is None


def test_grounding_score_from_gold_doc_titles():
    case = EvalCase(
        id="t5",
        question="q",
        must_contain=["France"],
        gold_doc_titles=["Paris", "London"],
    )
    r = evaluate_case(case, "Paris is in France.", error=None)
    assert r["grounding_score"] == 0.5
    assert r["titles_hit_frac"] == r["grounding_score"]
