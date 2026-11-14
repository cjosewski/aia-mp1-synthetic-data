"""Synthetic-only metric boundaries, frozen evidence replay and export failures."""

import copy
import json

import pytest
from assessed_fixtures import GoodClient, fixture_config, qualified_judge
from test_evaluation import FakeJudge, label_all
from test_evaluation import assessed_queue as _assessed_queue

from aia_mp1.analysis import (
    cohort_snapshot,
    compare,
    load_analysis,
    quality,
    segments,
    worst_segment,
    write_analysis,
)
from aia_mp1.analysis_cli import main
from aia_mp1.analysis_export import chart_tables, export_local, render_charts
from aia_mp1.assessment import create_cohort_assessment, load_assessment
from aia_mp1.cohort import freeze_cohort
from aia_mp1.collection import collect
from aia_mp1.evaluation_schemas import DIMENSIONS, Judgment
from aia_mp1.human_reference import freeze_reference
from aia_mp1.judge import judge_run
from aia_mp1.labels import record_label
from aia_mp1.model_client import AttemptResult
from aia_mp1.schemas import CATEGORIES


@pytest.fixture
def assessed_queue(tmp_path):
    return _assessed_queue.__wrapped__(tmp_path)


def samples(count=100, failed=20, prefix="synthetic"):
    records = [{"item_id": f"{prefix}-{i}", "category": CATEGORIES[i % 5]} for i in range(count)]
    decisions = {
        r["item_id"]: dict.fromkeys(DIMENSIONS, int(i >= failed)) for i, r in enumerate(records)
    }
    return records, decisions


def test_missing_and_strict_binary_denominators():
    records, decisions = samples(50, 10)
    observed = dict(list(decisions.items())[:20])
    metric = quality(records, observed)
    assert metric["overall"] == {
        "pass": 10,
        "fail": 10,
        "observed": 20,
        "population": 50,
        "missing": 30,
        "pass_rate": 0.5,
        "coverage_complete": False,
    }
    assert quality(records, {})["overall"]["pass_rate"] is None
    assert worst_segment(segments(records, observed)) is None
    for invalid in (True, "1", 1.0, 2, None):
        with pytest.raises(ValueError):
            quality(records, {records[0]["item_id"]: dict.fromkeys(DIMENSIONS, invalid)})
    with pytest.raises(ValueError, match="foreign"):
        quality(records, {"foreign": dict.fromkeys(DIMENSIONS, 1)})
    with pytest.raises(ValueError, match="duplicate"):
        quality(records + records[:1], decisions)


def test_worst_segment_is_exact_and_deterministic():
    records, decisions = samples()
    worst = worst_segment(segments(records, decisions))
    assert (worst["category"], worst["dimension"], worst["fail"], worst["observed"]) == (
        CATEGORIES[0],
        "D1",
        4,
        20,
    )
    decisions[records[22]["item_id"]]["D3"] = 0
    assert worst_segment(segments(records, decisions))["dimension"] == "D3"
    assert worst_segment(segments(records, decisions))["category"] == CATEGORIES[2]


@pytest.fixture
def snapshots(assessed_queue):
    root, manifest, config = assessed_queue
    label_all(root, manifest)
    judge_run(root, "diagnostic", "judged", config, FakeJudge())
    baseline = cohort_snapshot(root, "diagnostic", "judged")
    corrected = copy.deepcopy(baseline)
    corrected["purpose"] = "corrected"
    corrected["collection_identity"]["prompt"] += "\nSynthetic declared correction."
    for snapshot, phase, failed in ((baseline, "baseline", 20), (corrected, "corrected", 3)):
        records, decisions = samples(failed=failed, prefix=phase)
        snapshot["population_ids"] = [r["item_id"] for r in records]
        snapshot["judge_quality"] = quality(records, decisions)
        snapshot["judge_segments"] = segments(records, decisions)
    return baseline, corrected


def test_exact_reduction_and_zero_baseline(snapshots):
    baseline, corrected = snapshots
    result = compare(baseline, corrected, "Synthetic correction")
    assert result["status"] == "ready" and result["reduction_fraction"] == "17/20"
    records, decisions = samples(failed=4, prefix="corrected")
    corrected["judge_quality"] = quality(records, decisions)
    result = compare(baseline, corrected, "Synthetic correction")
    assert result["status"] == "pending" and result["reduction_fraction"] == "4/5"
    assert result["reduction_at_least_80_percent"] is True
    assert result["checks"]["relative_failure_reduction_strict"] is False
    records, decisions = samples(failed=0)
    baseline["judge_quality"] = quality(records, decisions)
    assert compare(baseline, corrected, "Synthetic")["relative_failure_reduction"] is None


@pytest.mark.parametrize(
    "change,reason",
    [
        ("rubric", "different_rubric_sha256"),
        ("model", "different_judge_settings"),
        ("gate", "different_gate_rules_sha256"),
        ("prompt", "generator_prompt_not_changed"),
        ("policy", "different_policy"),
        ("selection", "different_selection"),
    ],
)
def test_comparability_rejects_changed_controls(snapshots, change, reason):
    baseline, corrected = snapshots
    if change == "rubric":
        corrected["rubric_sha256"] = "changed"
    elif change == "model":
        corrected["judge_identity"]["settings"]["model"] = "another-model"
    elif change == "gate":
        corrected["collection_identity"]["gate_rules_sha256"] = "changed"
    elif change == "prompt":
        corrected["collection_identity"]["prompt"] = baseline["collection_identity"]["prompt"]
    elif change == "policy":
        corrected["collection_identity"]["policy"]["max_attempts"] = 5
    else:
        corrected["selection"]["seed"] = "different"
    result = compare(baseline, corrected, "Synthetic")
    assert result["status"] == "pending" and reason in result["comparability_reasons"]


def test_human_only_snapshot_is_not_judge_measurement(assessed_queue):
    root, manifest, _ = assessed_queue
    label_all(root, manifest)
    report = write_analysis(root, "baseline-review", "diagnostic")
    assert report["status"] == "pending"
    assert report["baseline"]["human_quality"]["overall"]["observed"] == 20
    assert report["baseline"]["judge_quality"]["overall"]["missing"] == 50
    assert load_analysis(root, "baseline-review") == report
    assert not (root / "assessments/diagnostic/calibration").exists()
    with pytest.raises(FileExistsError):
        write_analysis(root, "baseline-review", "diagnostic")
    tables = chart_tables(report)
    assert all(r["pass_rate"] is None for r in tables["dimensions"])
    assert sum(r["retained"] or 0 for r in tables["categories"]) == 50
    receipt = export_local(root, "baseline-review", "local-export", charts=False)
    assert receipt["completion"] == "pending"
    assert "baseline.jsonl" in receipt["files"]
    assert any("attempts.jsonl" in name for name in receipt["files"])
    assert not any("corrected.jsonl" in name for name in receipt["files"])


def test_replay_detects_later_human_amendment(assessed_queue):
    root, manifest, _ = assessed_queue
    label_all(root, manifest)
    report = write_analysis(root, "before-amendment", "diagnostic")
    snapshot = report["baseline"]
    ref = json.loads((root / "assessments/diagnostic/human-reference.json").read_text())
    first = manifest["selected_ids"][0]
    record_label(
        root,
        "diagnostic",
        first,
        dict.fromkeys(DIMENSIONS, 0),
        "Synthetic reviewer",
        supersedes=ref["labels"][first]["label_id"],
    )
    with pytest.raises(ValueError, match="source evidence changed"):
        load_analysis(root, "before-amendment")
    amended = cohort_snapshot(root, "diagnostic")
    assert amended["human_quality"] == snapshot["human_quality"]


def test_assessed_preview_and_tampered_report(assessed_queue):
    root, manifest, config = assessed_queue
    label_all(root, manifest)
    judge_run(root, "diagnostic", "judged", config, FakeJudge())
    report = write_analysis(root, "judged-review", "diagnostic", baseline_judge="judged")
    assert report["baseline"]["calibration"]["status"] == "ready"
    assert load_analysis(root, "judged-review") == report
    assert not (root / "assessments/diagnostic/calibration").exists()
    path = root / "analysis/judged-review/report.json"
    report["status"] = "ready"
    path.write_text(json.dumps(report))
    assert main(["verify", "--artifact-root", str(root), "--report-id", "judged-review"]) == 2


def test_five_charts_export_missing_cells(assessed_queue, tmp_path):
    pytest.importorskip("matplotlib")
    pytest.importorskip("seaborn")
    root, manifest, _ = assessed_queue
    label_all(root, manifest)
    report = write_analysis(root, "chart-source", "diagnostic")
    receipt = render_charts(report, tmp_path / "charts")
    assert len([name for name in receipt["files"] if name.endswith(".png")]) == 5
    assert len([name for name in receipt["files"] if name.endswith(".svg")]) == 5
    assert len([name for name in receipt["files"] if name.endswith(".csv")]) == 5
    assert all(path.stat().st_size > 0 for path in (tmp_path / "charts").iterdir())
    with pytest.raises(FileExistsError):
        render_charts(report, tmp_path / "charts")


def test_full_verified_comparison_and_reasoning_change(tmp_path):
    """Two synthetic cohorts exercise the real collection/reference/judge joins."""
    from pathlib import Path

    config = fixture_config(tmp_path)
    root = Path(config.artifact_root)
    judge_config = qualified_judge(tmp_path, config)
    rubric = Path(__file__).resolve().parents[1] / "config/rubric.json"

    class SyntheticJudgments:
        def __init__(self, failed):
            self.failed, self.index = failed, 0

        def generate(self, messages):
            values = {
                d: {"decision": 1, "justification": "Synthetic test only."} for d in DIMENSIONS
            }
            values["D1"]["decision"] = int(self.index >= self.failed)
            self.index += 1
            item = Judgment.model_validate(values)
            return AttemptResult(item, item.model_dump(), None, None, judge_config.model)

    for phase, failed in (("baseline", 10), ("corrected", 1)):
        selected_config = config
        if phase == "corrected":
            prompt = tmp_path / "corrected.md"
            prompt.write_text(Path(config.prompt_path).read_text() + "\nSynthetic correction.")
            selected_config = config.model_copy(
                update={"purpose": phase, "prompt_path": str(prompt)}
            )
        collect(selected_config, phase, GoodClient())
        freeze_cohort(root, phase, phase)
        manifest = create_cohort_assessment(root, phase, phase, rubric)
        _, _, records, _ = load_assessment(root, phase)
        for i, record in enumerate(records):
            if record["item_id"] in manifest["selected_ids"]:
                record_label(
                    root,
                    phase,
                    record["item_id"],
                    dict.fromkeys(DIMENSIONS, 1) | {"D1": int(i >= failed)},
                    "Synthetic reviewer",
                    notes="Synthetic integration fixture",
                    review_stage="blind",
                )
        freeze_reference(root, phase, "Synthetic reviewer", declare_blind=True)
        judge_run(root, phase, "judged", judge_config, SyntheticJudgments(failed))
    report = write_analysis(
        root,
        "complete",
        "baseline",
        baseline_judge="judged",
        corrected_id="corrected",
        corrected_judge="judged",
        correction="Synthetic prompt change",
    )
    assert report["status"] == "ready"
    assert report["comparison"]["reduction_fraction"] == "9/10"
    assert report["corrected"]["judge_quality"]["overall"]["pass"] == 49
    assert load_analysis(root, "complete") == report
    changed = copy.deepcopy(report["corrected"])
    changed["judge_identity"]["settings"]["reasoning_effort"] = "high"
    assert (
        "different_judge_settings"
        in compare(report["baseline"], changed, "Synthetic")["comparability_reasons"]
    )
