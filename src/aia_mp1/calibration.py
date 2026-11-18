"""Exact agreement with explicit coverage and immutable calibration receipts."""

from pathlib import Path

from .acceptance import COURSE_POLICY, acceptance_result
from .assessment import exclusive, load_assessment, read_text, save_new
from .evaluation_schemas import DIMENSIONS, Judgment
from .generate import implementation_identity
from .judge import judge_directory, validate_judge
from .labels import load_labels
from .schemas import CATEGORIES
from .tracing import digest, now, run_directory


def agreement(records: list[dict], selected_ids: list[str], labels: dict, judgments: dict) -> dict:
    population_ids = {r["item_id"] for r in records}
    if (
        len(population_ids) != len(records)
        or len(set(selected_ids)) != len(selected_ids)
        or not set(selected_ids) <= population_ids
        or not set(labels) <= set(selected_ids)
        or not set(judgments) <= population_ids
    ):
        raise ValueError("agreement inputs have foreign or duplicate identities")
    dimensions, disagreements = {}, []
    for dimension in DIMENSIONS:
        confusion = {
            "human_0_judge_0": 0,
            "human_0_judge_1": 0,
            "human_1_judge_0": 0,
            "human_1_judge_1": 0,
        }
        for item_id in selected_ids:
            if item_id not in labels or item_id not in judgments:
                continue
            human = labels[item_id]["decisions"][dimension]
            judge = judgments[item_id][dimension]["decision"]
            if (
                type(human) is not int
                or type(judge) is not int
                or human not in (0, 1)
                or judge not in (0, 1)
            ):
                raise ValueError("agreement requires strict binary decisions")
            confusion[f"human_{human}_judge_{judge}"] += 1
            if human != judge:
                disagreements.append(
                    {
                        "item_id": item_id,
                        "dimension": dimension,
                        "human": human,
                        "judge": judge,
                        "judge_justification": judgments[item_id][dimension]["justification"],
                    }
                )
        compared = sum(confusion.values())
        matching = confusion["human_0_judge_0"] + confusion["human_1_judge_1"]
        dimensions[dimension] = {
            "matching": matching,
            "compared": compared,
            "missing": len(selected_ids) - compared,
            "agreement": matching / compared if compared else None,
            "threshold_met": compared > 0 and matching * 5 >= compared * 4,
            "confusion": confusion,
        }
    return {
        "selected": len(selected_ids),
        "human_completed": len(labels),
        "population": len(records),
        "judge_completed": len(judgments),
        "coverage_complete": len(labels) == len(selected_ids) and len(judgments) == len(records),
        "dimensions": dimensions,
        "disagreements": disagreements,
    }


def calibration_report(
    root: Path,
    assessment_id: str,
    judge_run_id: str,
    report_id: str,
    *,
    write: bool = True,
    acceptance_policy: str = COURSE_POLICY,
) -> dict:
    """Revalidate and compute calibration; previews do not create a report directory."""
    parent, assessment, records, rubric = load_assessment(root, assessment_id)
    judge_dir = judge_directory(parent, judge_run_id)
    report_root = parent / "calibration"
    if report_root.is_symlink():
        raise ValueError("symlink report directory is not supported")
    target = run_directory(report_root, report_id)
    with exclusive(parent), exclusive(judge_dir):
        labels = load_labels(parent, assessment, records)
        current_labels = labels
        reference = None
        if assessment["assessment_eligible"]:
            from .human_reference import load_reference

            reference = load_reference(parent, assessment, records, for_scoring=True)
            labels = reference["labels"]
        judge_manifest, events, attempts, results = validate_judge(
            judge_dir, assessment, records, rubric
        )
        judgments = {
            key: Judgment.model_validate(value["judgment"]).model_dump(mode="json")
            for key, value in results.items()
        }
        summary = agreement(records, assessment["selected_ids"], labels, judgments)
        acceptance = acceptance_result(summary, acceptance_policy)
        category_counts = {c: sum(r["category"] == c for r in records) for c in CATEGORIES}
        settings = judge_manifest["identity"]["settings"]
        generator_models = {r["model"] for r in records} | {assessment["generator_model"]}
        reported_models = {result["response_model"] for result in results.values()}
        model_eligible = (
            bool(settings.get("stronger_model_basis"))
            and settings["model"] not in generator_models
            and not bool(reported_models & generator_models)
            and None not in reported_models
            and len(reported_models) == 1
        )
        reasons = []
        if reference and any(
            current_labels[k]["label_id"] != labels[k]["label_id"] for k in labels
        ):
            reasons.append("human_reference_amended_after_freeze")
        if not assessment["assessment_eligible"]:
            reasons.append("diagnostic_assessment")
        if (
            len(records) < 50
            or len(set(category_counts.values())) != 1
            or not all(category_counts.values())
        ):
            reasons.append("assessed_population_not_ready")
        if len(labels) < 20:
            reasons.append("fewer_than_20_complete_human_labels")
        if not summary["coverage_complete"]:
            reasons.append("incomplete_human_or_judge_coverage")
        if not acceptance["threshold_met"]:
            reasons.append(
                "per_dimension_agreement_not_met"
                if acceptance_policy == COURSE_POLICY
                else "overall_agreement_not_met"
            )
        if not model_eligible:
            reasons.append("stronger_judge_selection_not_established")
        if judge_manifest["status"] != "complete":
            reasons.append("judge_run_not_complete")
        completed_requests = {a["attempt_id"] for a in attempts}
        if any(e["attempt_id"] not in completed_requests for e in events):
            reasons.append("judge_requests_with_unknown_outcome")
        segments = {}
        for category in CATEGORIES:
            segment = [r for r in records if r["category"] == category]
            ids = {r["item_id"] for r in segment}
            segments[category] = agreement(
                segment,
                [i for i in assessment["selected_ids"] if i in ids],
                {i: v for i, v in labels.items() if i in ids},
                {i: v for i, v in judgments.items() if i in ids},
            )
        report = {
            "schema_version": "1",
            "report_id": report_id,
            "created_at": now(),
            "assessment_id": assessment_id,
            "judge_run_id": judge_run_id,
            "status": "ready" if not reasons else "pending",
            "readiness_reasons": reasons,
            "scope": "calibration on the selected items, not independent generalization",
            "assessment_eligible": assessment["assessment_eligible"],
            "assessment_sha256": assessment["manifest_sha256"],
            "human_ledger_sha256": digest(read_text(parent / "human-labels.jsonl")),
            "effective_label_ids": {key: value["label_id"] for key, value in labels.items()},
            "judge_manifest_sha256": digest(read_text(judge_dir / "manifest.json")),
            "judge_artifacts_sha256": judge_manifest["artifacts_sha256"],
            "frozen_judge": judge_manifest["identity"],
            "reported_models": sorted(m for m in reported_models if m is not None),
            "summary": summary,
            "categories": segments,
            "category_counts": category_counts,
            "implementation": implementation_identity(),
            "agreement_basis": "frozen_blind_reference"
            if reference
            else "diagnostic_effective_labels",
            "human_reference_sha256": reference["sha256"] if reference else None,
            "adjudication_summary": agreement(
                records, assessment["selected_ids"], current_labels, judgments
            )
            if reference
            else None,
        }
        # Preserve the exact legacy report shape for replay of sealed course reports.
        if acceptance_policy != COURSE_POLICY:
            report["acceptance"] = acceptance
        if write:
            target.mkdir(parents=True, exist_ok=False)
            save_new(target / "report.json", report)
        return report
