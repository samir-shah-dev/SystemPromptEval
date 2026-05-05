from types import SimpleNamespace
from unittest.mock import MagicMock

from system_prompt_eval.eval_cases import EvalCase
from system_prompt_eval.judge import judge_score_case


def test_judge_score_case_parses_json_response():
    fake_msg = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="text",
                text='{"score": 0.85, "correct": true, "reason": "Answer matches the facts."}',
            )
        ],
        stop_reason="end_turn",
    )
    client = MagicMock()
    client.messages.create.return_value = fake_msg

    case = EvalCase(id="t", question="What is 2+2?", gold_answer="4", must_contain=["4"])
    out = judge_score_case(case, "The answer is 4.", client=client, model="claude-test")

    assert out["judge_score"] == 0.85
    assert out["judge_correct"] is True
    assert out["judge_reason"] is not None and "facts" in out["judge_reason"]
    assert out["judge_error"] is None
    client.messages.create.assert_called_once()


def test_judge_score_case_skips_when_agent_errored():
    case = EvalCase(id="t", question="q", must_contain=["x"])
    out = judge_score_case(case, "", error="RuntimeError: boom", client=MagicMock())

    assert out["judge_score"] is None
    assert out["judge_error"] == "skipped_judge: agent_error"


def test_judge_score_case_clamps_score():
    fake_msg = SimpleNamespace(
        content=[SimpleNamespace(type="text", text='{"score": 2, "correct": true, "reason": "ok"}')],
        stop_reason="end_turn",
    )
    client = MagicMock()
    client.messages.create.return_value = fake_msg

    case = EvalCase(id="t", question="q?", must_contain=["a"])
    out = judge_score_case(case, "a", client=client, model="m")

    assert out["judge_score"] == 1.0


def test_judge_score_case_api_error_surfaces():
    client = MagicMock()
    client.messages.create.side_effect = OSError("network down")

    case = EvalCase(id="t", question="q?", must_contain=["a"])
    out = judge_score_case(case, "a", client=client, model="m")

    assert out["judge_score"] is None
    assert out["judge_error"] is not None
    assert "network down" in out["judge_error"]
