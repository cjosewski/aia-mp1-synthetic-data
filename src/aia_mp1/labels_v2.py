"""Authentic v2 human labels: the v1 ledger format with the eight rubric v2 dimensions."""

import json
import uuid
from datetime import datetime
from pathlib import Path

from .assessment import exclusive, read_json, read_text
from .assessment_v2 import item_identity_v2, load_assessment_v2
from .rubric_v2 import DecisionsV2, HumanLabelV2, boundary_triggered, load_rubric_v2
from .tracing import append_record, digest, now, read_records, run_directory, write_checkpoint

PACKET_MARKER = "review-packet.json"  # Written into each assessment that a review packet binds.


def refuse_unimported_packet(root: Path, assessment_id: str, directory: Path) -> None:
    """A bound arm takes no labels until its packet's import has finished.

    Otherwise the packet becomes unimportable and no new packet can be made for the arm.
    The packet import itself appends through append_label_v2 and is exempt.
    """
    marker = directory / PACKET_MARKER
    if not (marker.exists() or marker.is_symlink()):
        return
    packet_id = read_json(marker)["packet_id"]
    if not (run_directory(root / "packets", packet_id) / "import.json").exists():
        raise ValueError(
            f"assessment {assessment_id} belongs to review packet {packet_id}, whose import "
            "has not finished; import that packet's answers first, because a label recorded "
            "now would make the packet unimportable"
        )


def load_labels_v2(directory: Path, manifest: dict, records: list[dict]) -> dict[str, dict]:
    path = directory / "human-labels.jsonl"
    text = read_text(path)  # Missing evidence and symlinks are errors, not an empty review set.
    checkpoint = read_json(directory / "labels-checkpoint.json")
    ledger = read_records(path)
    if checkpoint != {
        "assessment_sha256": manifest["manifest_sha256"],
        "ledger_sha256": digest(text),
        "count": len(ledger),
    } or (text and not text.endswith("\n")):
        raise ValueError("human-label checkpoint/chain changed; preserve evidence for inspection")
    by_id = {record["item_id"]: record for record in records}
    effective, ids, previous_hash = {}, set(), None
    for envelope in ledger:
        if set(envelope) != {"label", "previous_sha256", "sha256"}:
            raise ValueError("invalid human-label ledger envelope")
        unsigned = {k: v for k, v in envelope.items() if k != "sha256"}
        if envelope["sha256"] != digest(unsigned) or envelope["previous_sha256"] != previous_hash:
            raise ValueError("human-label chain changed")
        label = HumanLabelV2.model_validate(envelope["label"]).model_dump(mode="json")
        item_id = label["item_id"]
        if item_id not in manifest["selected_ids"] or label["label_id"] in ids:
            raise ValueError("foreign or duplicate human label")
        timestamp = datetime.fromisoformat(label["timestamp"])
        if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
            raise ValueError("human-label timestamp must be UTC")
        if any(label[k] != v for k, v in item_identity_v2(manifest, by_id[item_id]).items()):
            raise ValueError("human label has mismatched item or rubric identity")
        expected = effective[item_id]["label_id"] if item_id in effective else None
        if label["supersedes_label_id"] != expected:
            raise ValueError("amendment must supersede the current label explicitly")
        effective[item_id] = label
        ids.add(label["label_id"])
        previous_hash = envelope["sha256"]
    return effective


def append_label_v2(
    directory: Path,
    manifest: dict,
    records: list[dict],
    item_id: str,
    decisions: dict,
    reviewer: str,
    *,
    notes: str = "",
    supersedes: str | None = None,
    review_stage: str | None = None,
    consulted_report_ids: list[str] | None = None,
    packet_id: str | None = None,
    review_id: str | None = None,
) -> dict:
    """Validate and append one label; the caller holds the directory's writer lock."""
    if (directory / "human-reference.json").exists():
        if review_stage == "blind":
            raise ValueError(
                "labels recorded after the reference freeze must disclose post-review context"
            )
        review_stage = "post_review"
    elif review_stage is None:
        review_stage = "unknown"
    effective = load_labels_v2(directory, manifest, records)
    if item_id not in manifest["selected_ids"]:
        raise ValueError("item is not in the frozen human-review selection")
    expected = effective[item_id]["label_id"] if item_id in effective else None
    if supersedes != expected:
        raise ValueError("use the current label ID for an explicit amendment")
    record = next(r for r in records if r["item_id"] == item_id)
    validated = DecisionsV2.model_validate(decisions)
    rubric = load_rubric_v2(read_text(directory / "rubric.json"))
    task_id = record["reference_context"]["task"]["id"]
    if validated.professional_boundary != 1 and not boundary_triggered(rubric, task_id):
        # label_rule: an automatic pass is recorded as 1, never as a failure.
        raise ValueError("professional_boundary is an automatic pass (1) for this brief (F3)")
    label = HumanLabelV2(
        **item_identity_v2(manifest, record),
        label_id=str(uuid.uuid4()),
        reviewer=reviewer,
        timestamp=now(),
        decisions=validated,
        notes=notes,
        supersedes_label_id=supersedes,
        review_stage=review_stage,
        consulted_report_ids=consulted_report_ids,
        packet_id=packet_id,
        review_id=review_id,
    ).model_dump(mode="json")
    path = directory / "human-labels.jsonl"
    ledger = read_records(path)
    envelope = {"label": label, "previous_sha256": ledger[-1]["sha256"] if ledger else None}
    envelope["sha256"] = digest(envelope)
    # Serialised exactly as append_record writes it; read_records splits on splitlines().
    line = json.dumps(envelope, ensure_ascii=False, allow_nan=False) + "\n"
    if len(line.splitlines()) != 1:
        raise ValueError(
            "label text contains a Unicode line separator (for example U+2028); remove it, "
            "because it would split the ledger line"
        )
    append_record(path, envelope)
    write_checkpoint(
        directory / "labels-checkpoint.json",
        {
            "assessment_sha256": manifest["manifest_sha256"],
            "ledger_sha256": digest(read_text(path)),
            "count": len(ledger) + 1,
        },
    )
    return label


def record_label_v2(
    root: Path,
    assessment_id: str,
    item_id: str,
    decisions: dict,
    reviewer: str,
    *,
    notes: str = "",
    supersedes: str | None = None,
    review_stage: str | None = None,
    consulted_report_ids: list[str] | None = None,
) -> dict:
    directory, manifest, records, _ = load_assessment_v2(root, assessment_id)
    with exclusive(directory):
        refuse_unimported_packet(root, assessment_id, directory)
        return append_label_v2(
            directory,
            manifest,
            records,
            item_id,
            decisions,
            reviewer,
            notes=notes,
            supersedes=supersedes,
            review_stage=review_stage,
            consulted_report_ids=consulted_report_ids,
        )


def label_status_v2(root: Path, assessment_id: str) -> dict:
    directory, manifest, records, _ = load_assessment_v2(root, assessment_id)
    with exclusive(directory):
        effective = load_labels_v2(directory, manifest, records)
        pending = [i for i in manifest["selected_ids"] if i not in effective]
        return {
            "assessment_id": assessment_id,
            "purpose": manifest["purpose"],
            "selected": len(manifest["selected_ids"]),
            "completed": len(effective),
            "pending_item_ids": pending,
            "effective_label_ids": {k: v["label_id"] for k, v in effective.items()},
            "status": "complete" if not pending else "incomplete",
            "reference_frozen": (directory / "human-reference.json").exists(),
        }


def interactive_label_v2(
    root: Path,
    assessment_id: str,
    reviewer: str,
    *,
    input_fn=input,
    output=print,
    review_stage: str | None = None,
) -> dict:
    """Show only the brief and the seven fields; EOF or q stops without saving the item."""
    directory, manifest, records, rubric = load_assessment_v2(root, assessment_id)
    refuse_unimported_packet(root, assessment_id, directory)  # Before any rating is typed.
    pending = set(label_status_v2(root, assessment_id)["pending_item_ids"])
    by_id = {record["item_id"]: record for record in records}
    # The selection is a per-category round robin, so its positions would reveal the category.
    # A seeded shuffle gives every session the same order and positions that carry nothing.
    order = sorted(
        manifest["selected_ids"],
        key=lambda item_id: digest(
            {
                "seed": manifest["selection"]["seed"],
                "assessment_id": assessment_id,
                "item_id": item_id,
                "order": "interactive-session-v1",
            }
        ),
    )
    output("Human review, aec-rubric-v2: 1 = pass, 0 = fail, q = stop. No model scores are shown.")
    for number, item_id in enumerate(order, 1):
        if item_id not in pending:
            continue
        record = by_id[item_id]
        task = record["reference_context"]["task"]
        triggered = boundary_triggered(rubric, task["id"])
        position = f"{number} of {len(order)}"
        output(f"Item {position}")
        output("Task brief:\n" + task["brief"])
        output("Seven fields:\n" + json.dumps(record["item"], ensure_ascii=False, indent=2))
        decisions = {}
        for dimension in rubric["dimensions"]:
            name = dimension["name"]
            if dimension["id"] == "professional_boundary" and not triggered:
                decisions[dimension["id"]] = 1
                output(
                    f"{name}: automatic pass (1) under F3; the brief does not say its results "
                    "feed a design or code-compliance decision."
                )
                continue
            output(
                f"{name}\n  Pass: {dimension['pass_anchor']}\n  Fail: {dimension['fail_anchor']}"
            )
            while True:
                try:
                    answer = input_fn(f"{name} [1/0/q]: ").strip().lower()
                except EOFError:
                    return label_status_v2(root, assessment_id)
                if answer == "q":
                    return label_status_v2(root, assessment_id)
                if answer in {"0", "1"}:
                    decisions[dimension["id"]] = int(answer)
                    break
                output("Enter 1, 0 or q.")
        output("Notes (several lines allowed; end with a line holding only '.'):")
        lines = []
        while True:
            try:
                line = input_fn("")
            except EOFError:
                return label_status_v2(root, assessment_id)
            if line.strip() == ".":
                break
            lines.append(line)
        record_label_v2(
            root,
            assessment_id,
            item_id,
            decisions,
            reviewer,
            notes="\n".join(lines),
            review_stage=review_stage,
        )
        output(f"Saved item {position}.")
    return label_status_v2(root, assessment_id)
