"""Authentic human input, explicit amendments and resumable review queues."""

import json
import uuid
from datetime import datetime
from pathlib import Path

from .assessment import exclusive, item_identity, load_assessment, read_json, read_text
from .evaluation_schemas import DIMENSIONS, Decisions, HumanLabel
from .tracing import append_record, digest, now, read_records, write_checkpoint


def load_labels(directory: Path, manifest: dict, records: list[dict]) -> dict[str, dict]:
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
    by_id = {r["item_id"]: r for r in records}
    effective, ids = {}, set()
    previous_hash = None
    for envelope in ledger:
        if set(envelope) != {"label", "previous_sha256", "sha256"}:
            raise ValueError("invalid human-label ledger envelope")
        unsigned = {k: v for k, v in envelope.items() if k != "sha256"}
        if envelope["sha256"] != digest(unsigned) or envelope["previous_sha256"] != previous_hash:
            raise ValueError("human-label chain changed")
        label = HumanLabel.model_validate(envelope["label"]).model_dump(mode="json")
        item_id = label["item_id"]
        if item_id not in manifest["selected_ids"] or label["label_id"] in ids:
            raise ValueError("foreign or duplicate human label")
        timestamp = datetime.fromisoformat(label["timestamp"])
        if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
            raise ValueError("human-label timestamp must be UTC")
        if any(label[k] != v for k, v in item_identity(manifest, by_id[item_id]).items()):
            raise ValueError("human label has mismatched item or rubric identity")
        expected = effective[item_id]["label_id"] if item_id in effective else None
        if label["supersedes_label_id"] != expected:
            raise ValueError("amendment must supersede the current label explicitly")
        effective[item_id] = label
        ids.add(label["label_id"])
        previous_hash = envelope["sha256"]
    return effective


def record_label(
    root: Path,
    assessment_id: str,
    item_id: str,
    decisions: dict,
    reviewer: str,
    *,
    notes: str = "",
    supersedes: str | None = None,
) -> dict:
    directory, manifest, records, _ = load_assessment(root, assessment_id)
    with exclusive(directory):
        effective = load_labels(directory, manifest, records)
        if item_id not in manifest["selected_ids"]:
            raise ValueError("item is not in the frozen human-review selection")
        expected = effective[item_id]["label_id"] if item_id in effective else None
        if supersedes != expected:
            raise ValueError("use the current label ID for an explicit amendment")
        record = next(r for r in records if r["item_id"] == item_id)
        label = HumanLabel(
            **item_identity(manifest, record),
            label_id=str(uuid.uuid4()),
            reviewer=reviewer,
            timestamp=now(),
            decisions=Decisions.model_validate(decisions),
            notes=notes,
            supersedes_label_id=supersedes,
        ).model_dump(mode="json")
        path = directory / "human-labels.jsonl"
        ledger = read_records(path)
        envelope = {"label": label, "previous_sha256": ledger[-1]["sha256"] if ledger else None}
        envelope["sha256"] = digest(envelope)
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


def label_status(root: Path, assessment_id: str) -> dict:
    directory, manifest, records, _ = load_assessment(root, assessment_id)
    with exclusive(directory):
        effective = load_labels(directory, manifest, records)
        pending = [i for i in manifest["selected_ids"] if i not in effective]
        return {
            "assessment_id": assessment_id,
            "purpose": manifest["purpose"],
            "assessment_eligible": manifest["assessment_eligible"],
            "selected": len(manifest["selected_ids"]),
            "completed": len(effective),
            "pending_item_ids": pending,
            "effective_label_ids": {k: v["label_id"] for k, v in effective.items()},
            "status": "complete" if not pending else "incomplete",
        }


def interactive_label(
    root: Path, assessment_id: str, reviewer: str, *, input_fn=input, output=print
) -> dict:
    _, manifest, records, rubric = load_assessment(root, assessment_id)
    pending = label_status(root, assessment_id)["pending_item_ids"]
    by_id = {r["item_id"]: r for r in records}
    output("Human review: 0=fail, 1=pass, s=skip item, q=quit. No model scores are shown.")
    for item_id in pending:
        output(json.dumps({"item_id": item_id, "item": by_id[item_id]["item"]}, indent=2))
        decisions, skip = {}, False
        for dimension in rubric["dimensions"]:
            output(
                json.dumps({k: dimension[k] for k in ("id", "name", "pass_anchor", "fail_anchor")})
            )
            while True:
                try:
                    answer = input_fn(f"{dimension['id']} [0/1/s/q]: ").strip().lower()
                except EOFError:
                    return label_status(root, assessment_id)
                if answer == "q":
                    return label_status(root, assessment_id)
                if answer == "s":
                    skip = True
                    break
                if answer in {"0", "1"}:
                    decisions[dimension["id"]] = int(answer)
                    break
                output("Enter 0, 1, s or q.")
            if skip:
                break
        if not skip:
            try:
                notes = input_fn("Notes/reference versions (optional): ")
            except EOFError:
                return label_status(root, assessment_id)
            if set(decisions) == set(DIMENSIONS):
                record_label(root, assessment_id, item_id, decisions, reviewer, notes=notes)
                output(f"Saved {item_id}")
    return label_status(root, assessment_id)
