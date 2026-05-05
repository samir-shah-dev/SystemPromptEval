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
        },
        {
            "id": "b",
            "tags": ["physics"],
            "skipped": False,
            "passed": False,
            "gold_f1": None,
            "gold_pass": True,
            "grounding_score": 0.25,
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

    prec = by_tag["precision"]
    assert prec["n"] == 1
    assert prec["pass_rate"] == 1.0
    assert prec["avg_grounding"] == 1.0

    ut = by_tag["(untagged)"]
    assert ut["n"] == 1
    assert ut["avg_gold_f1"] == 0.5
    assert ut["avg_grounding"] is None


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
