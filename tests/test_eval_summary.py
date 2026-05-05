import pytest

from system_prompt_eval.eval_summary import aggregate_by_tag, tag_summary_markdown


def test_aggregate_by_tag_pass_and_gold():
    rows = [
        {
            "id": "a",
            "tags": ["physics", "precision"],
            "skipped": False,
            "passed": True,
            "gold_f1": 1.0,
            "gold_pass": True,
            "grounding_score": 1.0,
            "judge_score": 0.9,
            "judge_correct": True,
        },
        {
            "id": "b",
            "tags": ["physics"],
            "skipped": False,
            "passed": False,
            "gold_f1": None,
            "gold_pass": True,
            "grounding_score": 0.25,
            "judge_score": 0.5,
            "judge_correct": False,
        },
        {
            "id": "c",
            "tags": [],
            "skipped": False,
            "passed": True,
            "gold_f1": 0.5,
            "gold_pass": True,
            "grounding_score": None,
        },
    ]
    stats = aggregate_by_tag(rows)
    by_tag = {s["tag"]: s for s in stats}

    phys = by_tag["physics"]
    assert phys["n"] == 2
    assert phys["pass_rate"] == 0.5
    assert phys["accuracy"] == 1.0  # one gold row, gold_pass True
    assert phys["avg_gold_f1"] == 1.0
    assert phys["avg_grounding"] == pytest.approx(0.625)
    assert phys["avg_judge_score"] == pytest.approx(0.7)
    assert phys["judge_accuracy"] == pytest.approx(0.5)

    prec = by_tag["precision"]
    assert prec["n"] == 1
    assert prec["pass_rate"] == 1.0
    assert prec["avg_grounding"] == 1.0
    assert prec["avg_judge_score"] == pytest.approx(0.9)
    assert prec["judge_accuracy"] == 1.0

    ut = by_tag["(untagged)"]
    assert ut["n"] == 1
    assert ut["avg_gold_f1"] == 0.5
    assert ut["avg_grounding"] is None
    assert ut["avg_judge_score"] is None
    assert ut["judge_accuracy"] is None


def test_tag_summary_markdown_contains_headers():
    rows = [
        {
            "tags": ["x"],
            "skipped": False,
            "passed": True,
            "gold_f1": None,
            "gold_pass": True,
        },
    ]
    md = tag_summary_markdown(rows)
    assert "Summary by tag" in md
    assert "| x |" in md
    assert "Pass rate" in md
    assert "Avg grounding" in md
    assert "Avg judge" in md
    assert "Judge acc" in md
