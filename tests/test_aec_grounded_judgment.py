"""Synthetic field attribution and schema checks; no human ratings or live calls."""

from copy import deepcopy

import pytest

from aia_mp1.grounded_documentation import GroundedJudgment, candidate_catalog, validate_grounding


def case():
    return {
        "untrusted_item": {
            "question": "Synthetic question",
            "answer": "Use a bounded operation.",
            "equipment_problem": "Synthetic lock",
            "tools_required": ["Synthetic tool"],
            "steps": ["Close automatically"],
            "safety_info": "Use disposable inputs.",
            "tips": ["Check units.", "Check context."],
        },
        "untrusted_reference_context": {"task": {"brief": "Use a bounded operation with 5 units."}},
    }


def response():
    task = {
        "task_quote": "bounded operation",
        "candidate_ids": ["answer"],
        "status": "supported",
        "note": "Synthetic.",
    }
    return {
        "task_checks": [task],
        "bindings": [deepcopy(task)],
        "safety": {"candidate_ids": ["safety_info"], "status": "supported", "note": "Synthetic."},
        "tips": [
            {
                "tip_id": f"tips[{i}]",
                "candidate_ids": [f"tips[{i}]"],
                "status": "uncertain",
                "note": "Synthetic.",
            }
            for i in range(2)
        ],
        "documentation": [
            {
                "candidate_id": "answer",
                "passage_id": "P1.E1",
                "quote": "operation",
                "status": "supported",
                "note": "Synthetic.",
            }
        ],
        "ratings": {f"D{i}": {"decision": 1, "justification": "Synthetic."} for i in range(1, 7)},
    }


def pages():
    return [{"id": "P1", "excerpts": [{"id": "E1", "text": "A bounded operation."}]}]


def test_valid_attribution_does_not_override_model_binary_decisions():
    value = response()
    value["ratings"]["D1"]["decision"] = 0
    result = validate_grounding(GroundedJudgment.model_validate(value), case(), pages())
    assert result.D1.decision == 0
    assert candidate_catalog(case())["steps[0]"] == "Close automatically"


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda r: r["safety"].update(candidate_ids=["steps[0]"]), "safety_info"),
        (lambda r: r["safety"].update(candidate_ids=[]), "must locate"),
        (lambda r: r["tips"].pop(), "every original tip"),
        (lambda r: r["tips"].reverse(), "every original tip"),
        (lambda r: r["tips"][0].update(candidate_ids=["answer"]), "original tip"),
        (lambda r: r["task_checks"][0].update(task_quote="Invented obligation"), "exact original"),
        (lambda r: r["bindings"][0].update(candidate_ids=["answer[999]"]), "does not resolve"),
        (lambda r: r["documentation"][0].update(passage_id="P1.E2"), "was not shown"),
        (lambda r: r["documentation"][0].update(quote="invented quote"), "not in the cited"),
        (
            lambda r: r["documentation"][0].update(passage_id=None, quote=None),
            "not evidence of absence",
        ),
    ],
)
def test_invalid_grounding_is_rejected_without_fabricated_scores(mutation, match):
    value = response()
    mutation(value)
    with pytest.raises(ValueError, match=match):
        validate_grounding(GroundedJudgment.model_validate(value), case(), pages())


def test_unmatched_documentation_and_missing_candidate_are_explicit_uncertainty():
    value = response()
    value["documentation"][0].update(passage_id=None, quote=None, status="uncertain")
    value["safety"].update(candidate_ids=[], status="missing")
    assert (
        validate_grounding(GroundedJudgment.model_validate(value), case(), [])
        == GroundedJudgment.model_validate(value).ratings
    )


def test_optional_quote_does_not_force_verbatim_transcription():
    value = response()
    value["documentation"][0]["quote"] = None
    validate_grounding(GroundedJudgment.model_validate(value), case(), pages())
