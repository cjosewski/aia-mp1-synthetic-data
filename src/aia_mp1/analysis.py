"""Reproducible cohort metrics; missing judgments never become measured passes."""

import hashlib
from fractions import Fraction
from pathlib import Path

from .acceptance import COURSE_POLICY, acceptance_result
from .assessment import exclusive, load_assessment, read_json, save_new
from .calibration import calibration_report
from .cohort import load_cohort
from .evaluation_schemas import DIMENSIONS, Decisions, Judgment
from .generate import implementation_identity
from .human_reference import load_reference
from .judge import judge_directory, validate_judge
from .labels import load_labels
from .schemas import CATEGORIES
from .tracing import digest, now, run_directory


def quality(records: list[dict], decisions: dict) -> dict:
    """Rates use observed items; coverage and full-population eligibility are separate."""
    ids = {r["item_id"] for r in records}
    if len(ids) != len(records) or not set(decisions) <= ids:
        raise ValueError("quality inputs have foreign or duplicate identities")
    for record in records:
        if record["category"] not in CATEGORIES:
            raise ValueError("unknown quality category")
    values = [Decisions.model_validate(value).model_dump() for value in decisions.values()]
    count = len(values)

    def metric(passed):
        return {
            "pass": passed,
            "fail": count - passed,
            "observed": count,
            "population": len(records),
            "missing": len(records) - count,
            "pass_rate": passed / count if count else None,
            "coverage_complete": count == len(records) and count > 0,
        }

    return {
        "dimensions": {d: metric(sum(v[d] for v in values)) for d in DIMENSIONS},
        "overall": metric(sum(all(v.values()) for v in values)),
    }


def segments(records: list[dict], decisions: dict) -> dict:
    result = {}
    for category in CATEGORIES:
        subset = [r for r in records if r["category"] == category]
        ids = {r["item_id"] for r in subset}
        result[category] = quality(subset, {k: v for k, v in decisions.items() if k in ids})
    return result


def worst_segment(metrics: dict) -> dict | None:
    """Highest failure fraction, then larger N, then declared category/dimension order."""
    candidates = []
    for ci, category in enumerate(CATEGORIES):
        for di, dimension in enumerate(DIMENSIONS):
            row = metrics[category]["dimensions"][dimension]
            if not row["coverage_complete"]:
                return None
            candidates.append(
                (
                    Fraction(row["fail"], row["observed"]),
                    row["observed"],
                    -ci,
                    -di,
                    category,
                    dimension,
                    row,
                )
            )
    _, _, _, _, category, dimension, row = max(candidates)
    return {"category": category, "dimension": dimension, **row}


def file_hash(path: Path) -> str:
    if path.is_symlink():
        raise ValueError("symlink analysis evidence is not supported")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output_directory(root: Path, report_id: str) -> Path:
    repository = Path(__file__).resolve().parents[2]
    if root.resolve().is_relative_to(repository):
        raise ValueError("analysis evidence must stay outside the repository")
    if (root / "analysis").is_symlink():
        raise ValueError("symlink analysis root is not supported")
    return run_directory(root / "analysis", report_id)


def _sources(root: Path, parent: Path, cohort: dict, judge_dir: Path | None) -> dict:
    paths = [
        parent / name
        for name in (
            "manifest.json",
            "data.jsonl",
            "rubric.json",
            "human-labels.jsonl",
            "labels-checkpoint.json",
            "human-reference.json",
        )
        if (parent / name).exists()
    ]
    paths += [root / "cohorts" / cohort["cohort_id"] / "manifest.json"]
    paths += [
        root / "collections" / cohort["collection_id"] / name
        for name in ("manifest.json", "frozen.json")
    ]
    paths += [
        root / b["run_id"] / name for b in cohort["summary"]["batches"] for name in b["hashes"]
    ]
    if judge_dir:
        paths += [
            judge_dir / name
            for name in ("manifest.json", "events.jsonl", "attempts.jsonl", "prompt.md")
        ]
    return {p.relative_to(root).as_posix(): file_hash(p) for p in sorted(set(paths))}


def cohort_snapshot(
    root: Path,
    assessment_id: str,
    judge_run_id: str | None = None,
    *,
    acceptance_policy: str = COURSE_POLICY,
) -> dict:
    root = root.resolve()
    parent, assessment, records, rubric = load_assessment(root, assessment_id)
    if assessment.get("source_type") != "cohort" or not assessment["assessment_eligible"]:
        raise ValueError("analysis requires an assessed cohort; diagnostics stay separate")
    cohort = load_cohort(root, assessment["cohort_id"])
    judge_dir = judge_directory(parent, judge_run_id) if judge_run_id else None
    calibration = None
    if judge_run_id:
        calibration = calibration_report(
            root,
            assessment_id,
            judge_run_id,
            "preview",
            write=False,
            acceptance_policy=acceptance_policy,
        )
        # The report time is not evidence and must not change a reproducible snapshot.
        for key in ("created_at", "report_id", "implementation"):
            calibration.pop(key)
    with exclusive(parent):
        before = _sources(root, parent, cohort, judge_dir)
        current_labels = load_labels(parent, assessment, records)
        reference = (
            load_reference(parent, assessment, records, for_scoring=True)
            if (parent / "human-reference.json").exists()
            else None
        )
        labels = reference["labels"] if reference else current_labels
        judgments, judge_identity = {}, None
        if judge_dir:
            with exclusive(judge_dir):
                manifest, _, _, results = validate_judge(judge_dir, assessment, records, rubric)
                judge_identity = manifest["identity"]
                judgments = {
                    k: Judgment.model_validate(v["judgment"]).decisions()
                    for k, v in results.items()
                }
            if calibration["judge_manifest_sha256"] != digest(
                (judge_dir / "manifest.json").read_text(encoding="utf-8")
            ) or calibration["human_ledger_sha256"] != digest(
                (parent / "human-labels.jsonl").read_text(encoding="utf-8")
            ):
                raise ValueError("calibration inputs changed during analysis")
        human = {k: v["decisions"] for k, v in labels.items()}
        selected = [r for r in records if r["item_id"] in assessment["selected_ids"]]
        summary = cohort["summary"]
        distributions = {
            c: {
                "schema_valid_candidates": sum(d["category"] == c for d in summary["decisions"]),
                "after_deduplication": sum(
                    d["category"] == c and d["duplicate_of"] is None for d in summary["decisions"]
                ),
                "retained": summary["counts"][c],
                "target": 10,
            }
            for c in CATEGORIES
        }
        for stage in ("schema_valid_candidates", "after_deduplication", "retained"):
            total = sum(row[stage] for row in distributions.values())
            for row in distributions.values():
                row[f"{stage}_fraction"] = row[stage] / total if total else None
        after = _sources(root, parent, cohort, judge_dir)
        if before != after:
            raise ValueError("analysis inputs changed during reading")
    return {
        "schema_version": "1",
        "assessment_id": assessment_id,
        "judge_run_id": judge_run_id,
        "purpose": assessment["purpose"],
        "cohort_id": cohort["cohort_id"],
        "cohort_sha256": cohort["sha256"],
        "population_ids": assessment["population_ids"],
        "selected_ids": assessment["selected_ids"],
        "selection": assessment["selection"],
        "rubric": rubric,
        "rubric_sha256": assessment["rubric_sha256"],
        "reference_pack_sha256": assessment["reference_pack_sha256"],
        "collection_identity": cohort["identity"],
        "judge_identity": judge_identity,
        "input_hashes": before,
        "calibration": calibration,
        "human_basis": "frozen_blind_reference" if reference else "unfrozen_effective_labels",
        "human_reference_sha256": reference["sha256"] if reference else None,
        "human_reference_amended": bool(reference)
        and any(current_labels[k]["label_id"] != value["label_id"] for k, value in labels.items()),
        "human_quality": quality(selected, human),
        "human_segments": segments(selected, human),
        "judge_quality": quality(records, judgments),
        "judge_segments": segments(records, judgments),
        "category_distribution": distributions,
        "generation": {
            k: summary[k]
            for k in (
                "planned_slots",
                "started_attempts",
                "initial_attempt_valid_count",
                "initial_attempt_schema_pass_rate",
                "batches",
            )
        },
    }


def _fraction(row: dict, field: str) -> Fraction | None:
    return Fraction(row[field], row["observed"]) if row["observed"] else None


def compare(baseline: dict, corrected: dict, correction: str) -> dict:
    """Compare independent cohorts under one frozen judge; never imply item pairing."""
    if not correction.strip():
        raise ValueError("describe the declared generator prompt correction")
    reasons = []
    if baseline["purpose"] != "baseline" or corrected["purpose"] != "corrected":
        raise ValueError("comparison needs baseline and corrected purposes in that order")
    if set(baseline["population_ids"]) & set(corrected["population_ids"]):
        raise ValueError("baseline and corrected populations must be distinct")
    for key in ("rubric_sha256", "reference_pack_sha256", "selection"):
        if baseline[key] != corrected[key]:
            reasons.append(f"different_{key}")
    # Paths, endpoint/authentication and phase labels are not sampling parameters.
    runtime = (
        "model",
        "model_identity",
        "model_sha256",
        "temperature",
        "mode",
        "max_tokens",
        "max_attempts",
        "timeout_seconds",
        "reasoning_effort",
    )
    for role, key in (("generator", "collection_identity"), ("judge", "judge_identity")):
        left, right = baseline[key], corrected[key]
        if left is None or right is None:
            reasons.append(f"missing_{role}_identity")
            continue
        if any(left["settings"].get(k) != right["settings"].get(k) for k in runtime):
            reasons.append(f"different_{role}_settings")
        if role == "generator":
            for field in ("policy", "gate_rules_sha256", "sources"):
                if left[field] != right[field]:
                    reasons.append(f"different_{field}")
            if left["prompt"] == right["prompt"]:
                reasons.append("generator_prompt_not_changed")
        else:
            for field in ("prompt_sha256", "qualification", "implementation"):
                if left.get(field) != right.get(field):
                    reasons.append(f"different_judge_{field}")
    rubric = baseline["rubric"]

    def policy_id(snapshot):
        return (
            (snapshot.get("calibration") or {})
            .get("acceptance", {})
            .get("policy", {})
            .get("id", COURSE_POLICY)
        )

    if policy_id(baseline) != policy_id(corrected):
        reasons.append("different_acceptance_policy")
    checks = {}
    for phase, snapshot in (("baseline", baseline), ("corrected", corrected)):
        cal = snapshot["calibration"]
        checks[f"{phase}_calibration_ready"] = bool(cal and cal["status"] == "ready")
        checks[f"{phase}_population_complete"] = (
            snapshot["judge_quality"]["overall"]["coverage_complete"]
            and len(snapshot["population_ids"]) >= 50
        )
        gen = snapshot["generation"]
        checks[f"{phase}_initial_schema_validity"] = bool(gen["planned_slots"]) and (
            Fraction(gen["initial_attempt_valid_count"], gen["planned_slots"])
            >= Fraction(str(rubric["structural_validity_minimum"]))
        )
    b = baseline["judge_quality"]["overall"]
    c = corrected["judge_quality"]["overall"]
    bf, cf = _fraction(b, "fail"), _fraction(c, "fail")
    complete = b["coverage_complete"] and c["coverage_complete"]
    reduction = (bf - cf) / bf if complete and bf else None
    checks["baseline_failure_minimum"] = bool(
        b["coverage_complete"]
        and bf is not None
        and bf >= Fraction(str(rubric["baseline_overall_failure_minimum"]))
    )
    checks["corrected_overall_pass"] = bool(
        c["coverage_complete"]
        and _fraction(c, "pass") >= Fraction(str(rubric["overall_pass"]["pass_rate_minimum"]))
    )
    for d in rubric["dimensions"]:
        row = corrected["judge_quality"]["dimensions"][d["id"]]
        checks[f"corrected_{d['id']}_pass"] = bool(
            row["coverage_complete"]
            and _fraction(row, "pass") >= Fraction(str(d["pass_rate_minimum"]))
        )
    target = Fraction(str(rubric["relative_failure_reduction"]["conservative_target"]["value"]))
    checks["relative_failure_reduction_strict"] = reduction is not None and reduction > target
    return {
        "status": "ready" if all(checks.values()) and not reasons else "pending",
        "scope": "measured criteria only; instructor disposition, demo and coaching are separate",
        "correction": correction,
        "comparability_reasons": reasons,
        "checks": checks,
        "relative_failure_reduction": float(reduction) if reduction is not None else None,
        "reduction_fraction": str(reduction) if reduction is not None else None,
        "reduction_at_least_80_percent": reduction is not None and reduction >= target,
        "worst_baseline_segment": worst_segment(baseline["judge_segments"]),
        "pairing": "independent cohort aggregates; no item-level pairing",
    }


def write_analysis(
    root: Path,
    report_id: str,
    baseline_id: str,
    *,
    baseline_judge: str | None = None,
    corrected_id: str | None = None,
    corrected_judge: str | None = None,
    correction: str = "",
    acceptance_policy: str = COURSE_POLICY,
) -> dict:
    target = output_directory(root, report_id)
    if target.exists():
        raise FileExistsError(f"analysis already exists: {report_id}")
    if corrected_judge and not corrected_id:
        raise ValueError("corrected judge requires corrected assessment")
    # Validate even if no judge has yet completed.
    acceptance_result({"dimensions": {}}, acceptance_policy)
    baseline = cohort_snapshot(
        root, baseline_id, baseline_judge, acceptance_policy=acceptance_policy
    )
    if baseline["purpose"] != "baseline":
        raise ValueError("baseline assessment required")
    corrected = (
        cohort_snapshot(root, corrected_id, corrected_judge, acceptance_policy=acceptance_policy)
        if corrected_id
        else None
    )
    comparison = compare(baseline, corrected, correction) if corrected else None
    report = {
        "schema_version": "1",
        "report_id": report_id,
        "created_at": now(),
        "status": comparison["status"] if comparison else "pending",
        "baseline": baseline,
        "corrected": corrected,
        "comparison": comparison,
        "implementation": implementation_identity(),
        "scope": "local evidence; human sample statistics are not 50-item judge measurements",
    }
    if acceptance_policy != COURSE_POLICY:
        report["acceptance_policy"] = acceptance_policy
    report["sha256"] = digest(report)
    target.mkdir(parents=True, exist_ok=False)
    save_new(target / "report.json", report)
    return report


def load_analysis(root: Path, report_id: str) -> dict:
    report = read_json(output_directory(root, report_id) / "report.json")
    if report["sha256"] != digest({k: v for k, v in report.items() if k != "sha256"}):
        raise ValueError("analysis report content changed")
    for phase in ("baseline", "corrected"):
        snapshot = report[phase]
        if snapshot and snapshot != cohort_snapshot(
            root,
            snapshot["assessment_id"],
            snapshot["judge_run_id"],
            acceptance_policy=report.get("acceptance_policy", COURSE_POLICY),
        ):
            raise ValueError("analysis source evidence changed; create a new report")
    expected = (
        compare(report["baseline"], report["corrected"], report["comparison"]["correction"])
        if report["corrected"]
        else None
    )
    if expected != report["comparison"] or report["status"] != (
        expected["status"] if expected else "pending"
    ):
        raise ValueError("analysis comparison differs from recomputed metrics")
    return report
