"""Compare two frozen v2 blind human references from one review session; never judges."""

from pathlib import Path

from .assessment import assessment_directory, exclusive, save_new
from .assessment_v2 import SCHEMA_VERSION, load_assessment_v2
from .cohort import load_cohort
from .compare_human import compute_comparison
from .generate import implementation_identity
from .reference_v2 import load_reference_v2
from .review_packet_v2 import packet_label_records
from .rubric_v2 import boundary_triggered
from .tracing import digest, now, run_directory

REPOSITORY = Path(__file__).resolve().parents[2]
PATH_SETTINGS = {"artifact_root", "prompt_path", "reference_pack_path", "sources_path"}
IDENTITY_DIGESTS = ("prompt", "sources", "policy", "implementation")


def comparison_path(root: Path, comparison_id: str) -> Path:
    if root.resolve().is_relative_to(REPOSITORY):
        raise ValueError("comparison evidence must stay outside the repository")
    if (root / "analysis").is_symlink():
        raise ValueError("symlink analysis root is not supported")
    return run_directory(root / "analysis", comparison_id).with_name(f"{comparison_id}.json")


def identity_fields(cohort: dict) -> dict:
    """The generator identity that must match unless a difference is declared."""
    identity = cohort["identity"]
    fields = {
        # List- and dict-valued settings are compared by digest, never dropped.
        f"settings.{key}": digest(value) if isinstance(value, (dict, list)) else value
        for key, value in identity["settings"].items()
        if key != "purpose" and key not in PATH_SETTINGS and not key.endswith("_path")
    }
    fields |= {key: digest(identity[key]) for key in IDENTITY_DIGESTS}
    fields["gate_rules_sha256"] = identity["gate_rules_sha256"]
    return fields


def _boundary(manifest: dict, records: list[dict], rubric: dict) -> dict:
    """Owner F3: with no triggered brief the dimension is reported as not exercised."""
    by_id = {record["item_id"]: record for record in records}
    triggered = sum(
        boundary_triggered(rubric, by_id[item_id]["reference_context"]["task"]["id"])
        for item_id in manifest["selected_ids"]
    )
    return {
        "exercised": triggered > 0,
        "triggered_items": triggered,
        "reporting": rubric["professional_boundary_triggers"]["reporting"],
    }


def _arm(manifest: dict, records: list[dict], reference: dict) -> dict:
    by_id = {record["item_id"]: record for record in records}
    return {
        "assessment_id": manifest["assessment_id"],
        "selected_ids": manifest["selected_ids"],
        "labels": {item_id: label["decisions"] for item_id, label in reference["labels"].items()},
        "categories": {item_id: by_id[item_id]["category"] for item_id in manifest["selected_ids"]},
    }


def compare_assessments(
    root: Path,
    baseline_id: str,
    corrected_id: str,
    declared_differences: dict,
    comparison_id: str,
) -> dict:
    target = comparison_path(root, comparison_id)
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"comparison {comparison_id} already exists; choose a new ID")
    if not isinstance(declared_differences, dict) or not all(
        type(field) is str and type(reason) is str and reason.strip()
        for field, reason in declared_differences.items()
    ):
        raise ValueError("declared differences map each field to a non-empty reason")
    if baseline_id == corrected_id:
        raise ValueError("compare two different assessments")
    first, second = sorted(assessment_directory(root, a) for a in (baseline_id, corrected_id))
    with exclusive(first), exclusive(second):
        arms = {}
        for role, assessment_id in (("baseline", baseline_id), ("corrected", corrected_id)):
            directory, manifest, records, rubric = load_assessment_v2(root, assessment_id)
            if manifest["purpose"] != role:
                raise ValueError(f"assessment {assessment_id} is {manifest['purpose']}, not {role}")
            reference_path = directory / "human-reference.json"
            if not (reference_path.exists() or reference_path.is_symlink()):
                raise ValueError(f"assessment {assessment_id} has no frozen human reference")
            reference = load_reference_v2(directory, manifest, records, for_scoring=True)
            arms[role] = {
                "manifest": manifest,
                "records": records,
                "rubric": rubric,
                "reference": reference,
                "cohort": load_cohort(root, manifest["cohort_id"]),
            }
        baseline, corrected = arms["baseline"], arms["corrected"]
        if baseline["manifest"]["rubric_sha256"] != corrected["manifest"]["rubric_sha256"]:
            raise ValueError("both assessments must use the same rubric")
        if baseline["reference"]["reviewer"] != corrected["reference"]["reviewer"]:
            raise ValueError("both references must come from the same reviewer")
        packets = {
            label.get("packet_id")
            for arm in arms.values()
            for label in arm["reference"]["labels"].values()
        }
        if len(packets) != 1 or None in packets:
            raise ValueError("every label in both references must come from one masked packet")
        (packet_id,) = packets
        imports = {}
        for arm in arms.values():
            imports |= packet_label_records(
                root, arm["manifest"]["assessment_id"], arm["reference"]["labels"]
            )
        record = imports[packet_id]
        boundary = {
            role: _boundary(arm["manifest"], arm["records"], arm["rubric"])
            for role, arm in arms.items()
        }
        before, after = identity_fields(baseline["cohort"]), identity_fields(corrected["cohort"])
        observed = {
            field: {"baseline": before.get(field), "corrected": after.get(field)}
            for field in sorted(set(before) | set(after))
            if before.get(field) != after.get(field)
        }
        if undeclared := sorted(set(observed) - set(declared_differences)):
            raise ValueError("undeclared generator differences: " + ", ".join(undeclared))
        if spurious := sorted(set(declared_differences) - set(observed)):
            raise ValueError("declared differences that do not differ: " + ", ".join(spurious))
        result = compute_comparison(
            _arm(baseline["manifest"], baseline["records"], baseline["reference"]),
            _arm(corrected["manifest"], corrected["records"], corrected["reference"]),
            baseline["rubric"],
            course_checks={
                role: {
                    "retained_items": len(arm["cohort"]["summary"]["members"]),
                    "initial_attempt_schema_pass_rate": arm["cohort"]["summary"][
                        "initial_attempt_schema_pass_rate"
                    ],
                }
                for role, arm in arms.items()
            },
        )
        document = {
            "schema_version": SCHEMA_VERSION,
            "comparison_id": comparison_id,
            "created_at": now(),
            "rubric_version": baseline["manifest"]["rubric_version"],
            "rubric_sha256": baseline["manifest"]["rubric_sha256"],
            "packet_id": packet_id,
            "reviewer": baseline["reference"]["reviewer"],
            "review": {
                "packet_id": packet_id,
                "import_sha256": record["sha256"],
                "answers_sha256": record["answers_sha256"],
                "declarations_as_supplied": record["declarations_as_supplied"],
            },
            "arms": {
                role: {
                    "assessment_id": arm["manifest"]["assessment_id"],
                    "assessment_sha256": arm["manifest"]["manifest_sha256"],
                    "cohort_id": arm["manifest"]["cohort_id"],
                    "cohort_sha256": arm["manifest"]["cohort_sha256"],
                    "human_reference_sha256": arm["reference"]["sha256"],
                    "professional_boundary": boundary[role],
                }
                for role, arm in arms.items()
            },
            # Reported as measured only when exercised; its check stays in the decision.
            "professional_boundary": {
                "exercised": any(row["exercised"] for row in boundary.values()),
                "triggered_items": sum(row["triggered_items"] for row in boundary.values()),
                "reporting": baseline["rubric"]["professional_boundary_triggers"]["reporting"],
            },
            "declared_differences": {
                field: observed[field] | {"reason": declared_differences[field]}
                for field in observed
            },
            "implementation": implementation_identity(),
            "comparison": result,
        }
        document["sha256"] = digest(document)
        target.parent.mkdir(parents=True, exist_ok=True)
        with exclusive(target.parent):
            save_new(target, document)
        return document
