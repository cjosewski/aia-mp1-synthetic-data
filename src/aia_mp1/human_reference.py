"""Freeze blind labels before model feedback; adjudication never replaces them."""

from pathlib import Path

from .assessment import exclusive, load_assessment, read_json, read_text, save_new
from .labels import load_labels
from .tracing import digest, now, read_records


def freeze_reference(root: Path, assessment_id: str, reviewer: str, *, declare_blind: bool) -> dict:
    directory, assessment, records, _ = load_assessment(root, assessment_id)
    if not declare_blind or not reviewer.strip():
        raise ValueError("reviewer must explicitly declare no judge output was consulted")
    if not assessment["assessment_eligible"] or assessment.get("source_type") != "cohort":
        raise ValueError("blind reference requires an assessed cohort")
    with exclusive(directory):
        if (directory / "judges").exists() and any((directory / "judges").iterdir()):
            raise ValueError("cannot freeze blind labels after judge evidence exists")
        labels = load_labels(directory, assessment, records)
        if set(labels) != set(assessment["selected_ids"]) or len(labels) < 20:
            raise ValueError("complete all 20 selected human reviews before freezing")
        if any(
            label.get("review_stage") != "blind" or label.get("consulted_report_ids")
            for label in labels.values()
        ):
            raise ValueError("reference requires explicitly blind reviews")
        if any(label["reviewer"] != reviewer for label in labels.values()):
            raise ValueError("reference declaration must match the human reviewer")
        text = read_text(directory / "human-labels.jsonl")
        reference = {
            "schema_version": "1",
            "assessment_sha256": assessment["manifest_sha256"],
            "created_at": now(),
            "reviewer": reviewer,
            "declared_blind": True,
            "ledger_prefix_sha256": digest(text),
            "ledger_prefix_lines": len(text.splitlines()),
            "labels": labels,
            "selected_ids": assessment["selected_ids"],
            "rubric_sha256": assessment["rubric_sha256"],
            "reference_pack_sha256": assessment["reference_pack_sha256"],
        }
        reference["sha256"] = digest(reference)
        save_new(directory / "human-reference.json", reference)
        return reference


def load_reference(directory: Path, assessment: dict, records: list[dict]) -> dict:
    reference = read_json(directory / "human-reference.json")
    load_labels(directory, assessment, records)
    text = read_text(directory / "human-labels.jsonl")
    lines = text.splitlines(keepends=True)
    n = reference["ledger_prefix_lines"]
    if type(n) is not int or not 20 <= n <= len(lines):
        raise ValueError("invalid frozen human ledger prefix")
    prefix_labels = {}
    for envelope in read_records(directory / "human-labels.jsonl")[:n]:
        label = envelope["label"]
        prefix_labels[label["item_id"]] = label
    if (
        reference["sha256"] != digest({k: v for k, v in reference.items() if k != "sha256"})
        or reference["assessment_sha256"] != assessment["manifest_sha256"]
        or reference["selected_ids"] != assessment["selected_ids"]
        or reference["rubric_sha256"] != assessment["rubric_sha256"]
        or reference["reference_pack_sha256"] != assessment["reference_pack_sha256"]
        or reference["declared_blind"] is not True
        or reference["ledger_prefix_sha256"] != digest("".join(lines[:n]))
        or reference["labels"] != prefix_labels
        or set(prefix_labels) != set(assessment["selected_ids"])
        or any(
            label.get("review_stage") != "blind"
            or label.get("consulted_report_ids")
            or label["reviewer"] != reference["reviewer"]
            for label in prefix_labels.values()
        )
    ):
        raise ValueError("frozen human reference differs from its independent ledger prefix")
    return reference
