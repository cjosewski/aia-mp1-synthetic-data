"""Replay a completed local AEC judge and export its baseline evidence and charts."""

import argparse
import json

from prepare_aec_api_evaluation import REVISIONS, ROOT, SOURCES, prepare
from run_aec_api_evaluation import replay

from aia_mp1.analysis import category_distribution, file_hash, quality, segments, snapshot_sources
from aia_mp1.analysis_export import export_verified
from aia_mp1.assessment import load_assessment, read_json, read_text
from aia_mp1.calibration import agreement
from aia_mp1.cohort import load_cohort
from aia_mp1.evaluation_schemas import Judgment
from aia_mp1.human_reference import load_reference
from aia_mp1.judge import JudgeConfig
from aia_mp1.qualification import validate_qualification
from aia_mp1.tracing import digest, read_records


def baseline_report(root, revision):
    root = root.resolve()
    packet, inputs = prepare(root, revision)
    directory = root / f"api-correctness-judge-{revision}"
    manifest = read_json(directory / "manifest.json")
    if manifest["status"] != "complete" or (directory / ".writer.lock").exists():
        raise ValueError("A complete, closed judge run is required")
    saved = read_json(directory / "report.json")
    identity = manifest["identity"]
    parent, assessment, records, _ = load_assessment(root, inputs["source_assessment"])
    reference = load_reference(parent, assessment, records)
    config = JudgeConfig.model_validate(read_json(root / "judge-preparation-v1/judge.json"))
    qualification = validate_qualification(config, assessment)
    if (
        digest(saved) != manifest["report_sha256"]
        or saved["artifacts_sha256"] != manifest["artifacts_sha256"]
        or saved["identity"] != identity
        or identity["packet_sha256"] != digest(inputs)
        or identity["runner_sha256"]
        != digest(read_text(directory / "code/run_aec_api_evaluation.py"))
        or identity["qualification_sha256"] != qualification["sha256"]
        or identity["human_reference_sha256"] != reference["sha256"]
    ):
        raise ValueError("Saved judge report or provenance differs")
    starts, judgments, unknown = replay(directory, read_records(packet / "requests.jsonl"), config)
    labels = reference["labels"]
    summary = agreement(records, assessment["selected_ids"], labels, judgments)
    ready = (
        len(judgments) == len(records) == 50
        and len(labels) == 20
        and not unknown
        and summary["coverage_complete"]
        and all(
            row["compared"] == 20 and row["matching"] >= 16
            for row in summary["dimensions"].values()
        )
    )
    if (
        summary != saved["summary"]
        or unknown != saved["unknown_outcomes"]
        or ready != saved["meets_per_dimension_gate"]
    ):
        raise ValueError("Calibration does not reproduce from the frozen inputs")
    cohort = load_cohort(root, assessment["cohort_id"])
    collection = cohort["summary"]
    hashes = snapshot_sources(root, parent, cohort, None)
    paths = [
        packet / name for name in ("manifest.json", "prompt.md", "rubric.json", "requests.jsonl")
    ] + [
        directory / name
        for name in (
            "manifest.json",
            "attempts.jsonl",
            "report.json",
            "code/run_aec_api_evaluation.py",
            "code/prepare_aec_api_evaluation.py",
        )
    ]
    for source in SOURCES:
        paths.extend(
            root / "assessments" / source / name
            for name in (
                "manifest.json",
                "data.jsonl",
                "rubric.json",
                "human-labels.jsonl",
                "labels-checkpoint.json",
                "human-reference.json",
                "human-reference-withdrawal.json",
            )
        )
    qualification_dir = root / "judge-preparation-v1"
    paths.append(qualification_dir / "selection.json")
    paths.extend(qualification_dir / row["path"] for row in qualification["receipt"]["evidence"])
    hashes.update({path.relative_to(root).as_posix(): file_hash(path) for path in paths})
    selected = [r for r in records if r["item_id"] in labels]
    human = {key: value["decisions"] for key, value in labels.items()}
    judge = {key: Judgment.model_validate(value).decisions() for key, value in judgments.items()}
    baseline = {
        "assessment_id": assessment["assessment_id"],
        "cohort_id": assessment["cohort_id"],
        "cohort_sha256": cohort["sha256"],
        "judge_run_id": directory.name,
        "judge_report_sha256": manifest["report_sha256"],
        "human_reference_sha256": reference["sha256"],
        "rubric": read_json(packet / "rubric.json"),
        "generation": {
            k: collection[k]
            for k in (
                "planned_slots",
                "started_attempts",
                "initial_attempt_valid_count",
                "initial_attempt_schema_pass_rate",
                "batches",
            )
        },
        "category_distribution": category_distribution(collection),
        "judge_quality": quality(records, judge),
        "judge_segments": segments(records, judge),
        "human_quality": quality(selected, human),
        "human_segments": segments(selected, human),
        "judge_starts": sum(starts.values()),
        "calibration": {"status": "ready" if ready else "pending", "summary": summary},
        "input_hashes": hashes,
    }
    report = {
        "schema_version": "1",
        "report_id": f"aec-api-baseline-{revision}",
        "status": "pending",
        "baseline": baseline,
        "corrected": None,
        "comparison": None,
        "scope": "AEC baseline under version-specific API correctness D3. Corrected cohort unmeasured.",
    }
    report["sha256"] = digest(report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", choices=REVISIONS, required=True)
    args = parser.parse_args()
    receipt = export_verified(
        ROOT,
        f"aec-api-baseline-{args.revision}-package",
        lambda: baseline_report(ROOT, args.revision),
    )
    print(
        json.dumps(
            {"sealed_files": len(receipt["files"]), "report_sha256": receipt["report_sha256"]}
        )
    )
