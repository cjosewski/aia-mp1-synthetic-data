"""Synthetic acceptance amendment boundaries and historical evidence replay."""

import pytest
from test_evaluation import FakeJudge, label_all
from test_evaluation import assessed_queue as _assessed_queue
from test_evaluation import queue as _queue

from aia_mp1.acceptance import OWNER_POLICY, acceptance_result
from aia_mp1.analysis import load_analysis, write_analysis
from aia_mp1.analysis_export import chart_tables
from aia_mp1.calibration import agreement, calibration_report
from aia_mp1.cli import main
from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.human_reference import freeze_reference
from aia_mp1.judge import judge_run
from aia_mp1.labels import record_label


@pytest.fixture
def assessed_queue(tmp_path):
    return _assessed_queue.__wrapped__(tmp_path)


@pytest.fixture
def queue(tmp_path):
    return _queue.__wrapped__(tmp_path)


@pytest.mark.parametrize("matches,passed", [(83, False), (84, True), (87, True)])
def test_overall_exact_boundary_can_pass_with_failing_dimensions(matches, passed):
    records = [{"item_id": str(i)} for i in range(20)]
    selected = [r["item_id"] for r in records]
    labels = {i: {"decisions": dict.fromkeys(DIMENSIONS, 1)} for i in selected}
    judges = {
        item: {
            dimension: {"decision": int(index * 6 + d < matches), "justification": "Synthetic"}
            for d, dimension in enumerate(DIMENSIONS)
        }
        for index, item in enumerate(selected)
    }
    result = acceptance_result(agreement(records, selected, labels, judges), OWNER_POLICY)
    assert (result["matching"], result["compared"]) == (matches, 120)
    assert result["threshold_met"] is passed
    assert not result["original_per_dimension_80_met"]


def test_empty_or_unknown_policy_cannot_pass():
    summary = agreement([{"item_id": "x"}], ["x"], {}, {})
    assert acceptance_result(summary, OWNER_POLICY)["agreement"] is None
    assert not acceptance_result(summary, OWNER_POLICY)["threshold_met"]
    with pytest.raises(ValueError, match="unknown acceptance"):
        acceptance_result(summary, "arbitrary-policy")


def test_owner_receipt_and_cli_preserve_course_results_and_analysis_replay(assessed_queue):
    root, manifest, config = assessed_queue
    matches = [10, 17, 13, 18, 17, 12]
    for index, item in enumerate(manifest["selected_ids"]):
        record_label(
            root,
            "diagnostic",
            item,
            {d: int(index < n) for d, n in zip(DIMENSIONS, matches, strict=True)},
            "Synthetic reviewer",
            review_stage="blind",
        )
    freeze_reference(root, "diagnostic", "Synthetic reviewer", declare_blind=True)
    judge_run(root, "diagnostic", "judged", config, FakeJudge())
    original = calibration_report(root, "diagnostic", "judged", "course")
    original_path = root / "assessments/diagnostic/calibration/course/report.json"
    original_bytes = original_path.read_bytes()
    legacy_analysis = write_analysis(root, "legacy", "diagnostic", baseline_judge="judged")
    assert original["status"] == "pending"
    assert "acceptance" not in original
    assert (
        main(
            [
                "calibrate",
                "--artifact-root",
                str(root),
                "--assessment-id",
                "diagnostic",
                "--judge-run-id",
                "judged",
                "--report-id",
                "owner",
            ]
        )
        == 0
    )
    owner = calibration_report(
        root, "diagnostic", "judged", "preview", write=False, acceptance_policy=OWNER_POLICY
    )
    assert owner["status"] == "ready"
    assert owner["acceptance"]["matching"] == 87
    assert owner["acceptance"]["agreement"] == 0.725
    assert len(owner["summary"]["disagreements"]) == 33
    assert owner["summary"] == original["summary"]
    assert original_path.read_bytes() == original_bytes
    amended = write_analysis(
        root, "amended", "diagnostic", baseline_judge="judged", acceptance_policy=OWNER_POLICY
    )
    assert load_analysis(root, "legacy") == legacy_analysis
    assert load_analysis(root, "amended") == amended
    table = chart_tables(amended)["agreement"]
    assert table[0]["threshold_role"] == "original_course_reference"
    assert table[0]["overall_agreement"] == 0.725
    assert table[0]["overall_required"] == 0.7


def test_owner_policy_still_requires_complete_population(assessed_queue):
    root, manifest, config = assessed_queue
    label_all(root, manifest)
    with pytest.raises(KeyboardInterrupt):
        judge_run(root, "diagnostic", "interrupted", config, FakeJudge(interrupt=25))
    report = calibration_report(
        root, "diagnostic", "interrupted", "owner", acceptance_policy=OWNER_POLICY
    )
    assert report["acceptance"]["threshold_met"]
    assert report["status"] == "pending"
    assert "incomplete_human_or_judge_coverage" in report["readiness_reasons"]
    assert "judge_requests_with_unknown_outcome" in report["readiness_reasons"]


def test_owner_policy_never_promotes_diagnostic(queue):
    root, manifest, config = queue
    label_all(root, manifest)
    judge_run(root, "diagnostic", "judged", config, FakeJudge())
    report = calibration_report(
        root, "diagnostic", "judged", "owner", acceptance_policy=OWNER_POLICY
    )
    assert report["acceptance"]["threshold_met"]
    assert report["status"] == "pending"
    assert "diagnostic_assessment" in report["readiness_reasons"]
