"""A developer fixture cannot satisfy a missing task or tip with a plausible citation."""

from pathlib import Path

import pytest
from test_compact_evidence import sample as sample
from test_passage_evidence import case as case

from aia_mp1.aec_development import (
    DevelopmentJudgment,
    TaskChecklist,
    checked_judgment,
    checked_reference,
    reference_catalog,
)
from aia_mp1.aec_scoped_judge import ScopedJudgment, project


def test_one_dimension_quote_must_come_from_its_candidate_field(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "tools"))
    from screen_aec_dimensions import QuotedDecision, verify_quote

    item = {"tips": ["Check units before comparing.", "Keep the copy."], "steps": ["Save it."]}
    row = QuotedDecision(field="tips", quote="Check units", decision=1, justification="Synthetic")
    verify_quote(row, item, "D6")
    for changed in [
        {"field": "steps", "quote": "Save it."},
        {"field": "tips", "quote": "Check the units"},
        {"field": "tips", "quote": "comparing. Keep"},
    ]:
        with pytest.raises(ValueError, match="required candidate field"):
            verify_quote(row.model_copy(update=changed), item, "D6")


def test_reference_requires_a_bound_source():
    catalog = reference_catalog(
        {
            "task": {"brief": "Inspect the synthetic input. Report its units."},
            "sources": [
                {
                    "id": "synthetic",
                    "version": "1",
                    "text": "Only the second line applies.\nUnits are metres.",
                }
            ],
        }
    )
    check = {
        "task_passage": "B2",
        "expected_evidence": "Explains the unit.",
        "basis": "source",
        "source_passages": ["synthetic.2"],
    }
    plan = TaskChecklist(checks=[check])
    assert (
        checked_reference(plan, catalog)[0]["sources"]["synthetic.2"]["text"] == "Units are metres."
    )
    with pytest.raises(ValueError, match="does not resolve"):
        checked_reference(
            TaskChecklist(checks=[check | {"source_passages": ["synthetic.3"]}]), catalog
        )


def test_missing_tip_and_unsupported_coverage_cannot_project_to_six_scores(case):
    content, rubric, ratings = case
    tip_ids = [key for key in content["passage_index"] if key.startswith("C.tips.")]
    tips = [
        {
            "tip_id": k,
            "status": "adds_value",
            "dependency_ids": ["C.answer"],
            "reason": "Synthetic detail.",
        }
        for k in tip_ids
    ]
    coverage = {
        "check_id": "T1",
        "status": "established",
        "candidate_ids": ["C.steps.0"],
        "reason": "Synthetic step.",
    }

    def validate(rows, findings):
        response = DevelopmentJudgment(coverage=rows, tips=findings, ratings=ratings)
        return checked_judgment(response, content, rubric, [{"id": "T1"}])

    assert validate([coverage], tips).D1.decision == 1
    with pytest.raises(ValueError, match="every candidate tip"):
        validate([coverage], tips[1:])
    with pytest.raises(ValueError, match="candidate evidence"):
        validate([coverage | {"candidate_ids": []}], tips)
    with pytest.raises(ValueError, match="dependency"):
        validate([coverage], [tips[0] | {"dependency_ids": [tip_ids[0]]}, *tips[1:]])


def test_scoped_ratings_preserve_model_decisions_and_require_candidate_ids(case):
    content, rubric, _ = case
    tips = [
        {"tip_id": k, "status": "repeats", "dependency_ids": ["C.steps.0"], "reason": "Synthetic."}
        for k in content["passage_index"]
        if k.startswith("C.tips.")
    ]
    ratings = {
        f"D{i}": {"decision": i % 2, "justification": "Synthetic.", "candidate_ids": ["C.answer"]}
        for i in range(1, 7)
    }
    row = {
        "check_id": "T1",
        "status": "established",
        "candidate_ids": ["C.steps.0"],
        "reason": "Synthetic.",
    }
    parsed = ScopedJudgment(coverage=[row], tips=tips, ratings=ratings)
    assert project(parsed, content, rubric, [{"id": "T1"}]).decisions() == {
        key: value["decision"] for key, value in ratings.items()
    }
    parsed.ratings.D1.candidate_ids = ["invented"]
    with pytest.raises(ValueError, match="unknown passage"):
        project(parsed, content, rubric, [{"id": "T1"}])
