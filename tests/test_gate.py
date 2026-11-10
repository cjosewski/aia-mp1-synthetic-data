"""Gate behavior on explicitly synthetic items; no model quality is asserted."""

import pytest

from aia_mp1.gate import evaluate_gate
from aia_mp1.schemas import CATEGORIES, GeneratedItem


def record(index, category=None, **item_changes):
    return GeneratedItem.model_validate(
        {
            "run_id": "synthetic-run",
            "trace_id": f"trace-{index}",
            "item_id": f"item-{index}",
            "attempt_id": f"attempt-{index}",
            "category": category or CATEGORIES[index % 5],
            "prompt_variant": "fixture",
            "prompt_hash": "a" * 64,
            "model": "synthetic-fixture",
            "source_refs": [],
            "item": {
                "question": f"How do I validate the standalone synthetic case {index}?",
                "answer": "Read the test values, compare units, and inspect the output before retaining the result.",
                "equipment_problem": f"Synthetic validation case {index}",
                "tools_required": ["Python standard library"],
                "steps": [
                    "Read the fixture values.",
                    "Check the input unit labels.",
                    "Compare with the expected reference.",
                ],
                "safety_info": "Incorrect units can invalidate calculations; verify the dimensions against a known reference before using the output.",
                "tips": [
                    "Compare ratios as well as differences to reveal a hidden scale factor in the fixture."
                ],
                **item_changes,
            },
        }
    )


def test_balanced_fifty_passes_only_implemented_gate():
    records = [record(index) for index in range(50)]
    before = [entry.model_dump() for entry in records]
    result = evaluate_gate(records, expected_count=50)
    assert result["status"] == "passed"
    assert result["counts"]["accepted"] == 50
    assert result["distribution"]["counts"] == dict.fromkeys(CATEGORIES, 10)
    assert result["minimum_assessed_size_met"] is True
    assert result["quality_status"] == "pending"
    assert result["course_acceptance"] == "not_evaluated"
    assert result["schema_pass_rate"] is None
    assert [entry.model_dump() for entry in records] == before
    for item in result["items"]:
        assert all(
            item["checks"][dimension]["status"] == "pending"
            for dimension in ("D1", "D3", "D4", "D5")
        )


def test_five_item_smoke_is_not_an_assessed_run():
    result = evaluate_gate([record(index) for index in range(5)], expected_count=5)
    assert result["status"] == "passed"
    assert result["minimum_assessed_size_met"] is False
    assert result["course_acceptance"] == "not_evaluated"


def test_normalized_duplicate_is_rejected_and_category_deficit_remains_visible():
    records = [record(index) for index in range(5)]
    records[1] = record(1, question="  HOW do I validate the standalone synthetic CASE 0!!! ")
    result = evaluate_gate(records, expected_count=5)
    assert result["status"] == "failed"
    assert result["counts"] == {
        "input": 5,
        "after_dedup": 4,
        "accepted": 4,
        "duplicates": 1,
        "heuristic_rejected": 0,
        "missing": 1,
        "excess": 0,
    }
    assert "duplicate_question" in result["items"][1]["reasons"]
    assert result["distribution"]["before"]["aec_automation"] == 1
    assert result["distribution"]["counts"]["aec_automation"] == 0
    assert "item-1" not in result["accepted_item_ids"]


def test_missing_category_fails_even_when_total_count_matches():
    result = evaluate_gate(
        [record(index, category="gis_scripting") for index in range(5)], expected_count=5
    )
    assert result["counts"]["accepted"] == 5
    assert result["status"] == "failed"
    assert result["distribution"]["passed"] is False
    assert result["distribution"]["counts"]["simulation"] == 0


@pytest.mark.parametrize(
    "changes,dimension",
    [
        ({"safety_info": "Be careful and use caution when working through this example."}, "D2"),
        ({"tips": ["Follow the instructions."]}, "D6"),
        ({"tips": ["1. Compare with the expected reference."]}, "D6"),
    ],
)
def test_heuristic_failures_are_explained(changes, dimension):
    result = evaluate_gate([record(0, **changes)], expected_count=5)
    assert result["items"][0]["accepted"] is False
    assert dimension in result["items"][0]["reasons"]
    assert result["items"][0]["checks"][dimension]["kind"] == "heuristic"
    assert result["counts"]["heuristic_rejected"] == 1


def test_duplicate_and_heuristic_rejection_counts_do_not_double_count():
    result = evaluate_gate(
        [
            record(0),
            record(1, question=record(0).item.question, safety_info="Stay safe."),
        ],
        expected_count=5,
    )
    assert result["counts"]["duplicates"] == 1
    assert result["counts"]["heuristic_rejected"] == 0
    assert result["counts"]["after_dedup"] == 1
    assert result["counts"]["accepted"] == 1
    assert result["items"][1]["reasons"] == ["duplicate_question", "D2"]


def test_empty_batch_reports_missing_slots_without_dividing_by_zero():
    result = evaluate_gate([], expected_count=50)
    assert result["status"] == "failed"
    assert result["counts"]["missing"] == 50
    assert result["accepted_item_ids"] == []
    assert result["distribution"]["counts"] == dict.fromkeys(CATEGORIES, 0)


@pytest.mark.parametrize("count", [0, -5, 1, 7, 5.0, True])
def test_invalid_planned_batch_size_is_rejected(count):
    with pytest.raises(ValueError, match="positive multiple of five"):
        evaluate_gate([], expected_count=count)


def test_mixed_runs_and_duplicate_identity_are_rejected():
    other_run = record(1).model_copy(update={"run_id": "other-run"})
    with pytest.raises(ValueError, match="one run"):
        evaluate_gate([record(0), other_run], expected_count=5)
    with pytest.raises(ValueError, match="duplicate item_id"):
        evaluate_gate([record(0), record(0)], expected_count=5)


def test_unvalidated_input_cannot_be_misreported_as_schema_valid():
    with pytest.raises(TypeError, match="validated GeneratedItem"):
        evaluate_gate([record(0).model_dump()], expected_count=5)
