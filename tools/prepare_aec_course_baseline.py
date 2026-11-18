"""Replay original generation evidence with the course gate in a fresh evidence root."""

from pathlib import Path
from shutil import copyfile

from aia_mp1.assessment import create_cohort_assessment, read_json, read_text
from aia_mp1.cli import gate_run
from aia_mp1.cohort import freeze_cohort
from aia_mp1.collection import checkpoint, rule_identity
from aia_mp1.schemas import DOMAIN
from aia_mp1.tracing import digest, now


def verify_manifest(path):
    data = read_json(path)
    if data["sha256"] != digest({k: v for k, v in data.items() if k != "sha256"}):
        raise ValueError(f"Changed source manifest: {path}")
    return data


def main():
    if DOMAIN != "aec-course":
        raise ValueError("Set AIA_MP1_DOMAIN=aec-course")
    source = Path("../artifacts/evidence/P1-03")
    dest = source / "aec-course"
    collection_id = "baseline-001"
    source_collection = verify_manifest(source / "collections" / collection_id / "manifest.json")
    cohort = verify_manifest(source / "cohorts/baseline-cohort-001/manifest.json")
    if cohort["collection_sha256"] != source_collection["sha256"]:
        raise ValueError("Source cohort and collection differ")
    dest.mkdir(exist_ok=False)
    batches = cohort["summary"]["batches"]
    if [b["run_id"] for b in batches] != source_collection["batches"]:
        raise ValueError("Source batch list differs")
    for batch in batches:
        run = batch["run_id"]
        (dest / run).mkdir()
        for name in ("manifest.json", "data.jsonl", "events.jsonl", "attempts.jsonl", "prompt.md"):
            original = source / run / name
            copied = dest / run / name
            copyfile(original, copied)
            if digest(read_text(copied)) != batch["hashes"][name]:
                raise ValueError(f"Frozen input differs: {run}/{name}")
        gate_run(dest, run)
    directory = dest / "collections" / collection_id
    directory.mkdir(parents=True)
    checkpoint(
        directory,
        {
            "schema_version": "1",
            "collection_id": collection_id,
            "created_at": now(),
            "identity": source_collection["identity"] | {"gate_rules_sha256": rule_identity()},
            "batches": source_collection["batches"],
            "baseline_replay": {
                "source_collection_sha256": source_collection["sha256"],
                "source_cohort_sha256": cohort["sha256"],
                "excluded_item_ids": [r["item_id"] for r in cohort["summary"]["members"]],
            },
        },
    )
    result = freeze_cohort(dest, collection_id, "aec-course-baseline")
    assessment = create_cohort_assessment(
        dest,
        result["cohort_id"],
        "aec-course-baseline-review",
        Path("config/aec-course/rubric.json"),
    )
    print(result["summary"]["counts"], "review items:", len(assessment["selected_ids"]))


if __name__ == "__main__":
    main()
