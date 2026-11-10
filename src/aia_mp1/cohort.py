"""Immutable 50-item populations selected from validated collection evidence."""

from pathlib import Path

from .assessment import exclusive, read_json, save_new
from .collection import load_collection, summarize
from .tracing import digest, now, run_directory


def cohort_directory(root: Path, cohort_id: str) -> Path:
    if (root / "cohorts").is_symlink():
        raise ValueError("symlink cohort root is not supported")
    return run_directory(root / "cohorts", cohort_id)


def freeze_cohort(root: Path, collection_id: str, cohort_id: str) -> dict:
    parent, collection = load_collection(root, collection_id)
    target = cohort_directory(root, cohort_id)
    with exclusive(parent):
        if (parent / "frozen.json").exists():
            raise ValueError("collection already frozen; inspect existing cohort")
        summary = summarize(root, collection)
        if summary["status"] != "ready":
            raise ValueError("collection is not ready: " + ", ".join(summary["reasons"]))
        manifest = {
            "schema_version": "1",
            "cohort_id": cohort_id,
            "created_at": now(),
            "collection_id": collection_id,
            "collection_sha256": collection["sha256"],
            "identity": collection["identity"],
            "summary": summary,
        }
        manifest["sha256"] = digest(manifest)
        target.mkdir(parents=True, exist_ok=False)
        save_new(target / "manifest.json", manifest)
        save_new(parent / "frozen.json", {"cohort_id": cohort_id, "sha256": manifest["sha256"]})
        return manifest


def load_cohort(root: Path, cohort_id: str) -> dict:
    directory = cohort_directory(root, cohort_id)
    manifest = read_json(directory / "manifest.json")
    if manifest["cohort_id"] != cohort_id or manifest["sha256"] != digest(
        {k: v for k, v in manifest.items() if k != "sha256"}
    ):
        raise ValueError("cohort identity changed")
    parent, collection = load_collection(root, manifest["collection_id"])
    if collection["sha256"] != manifest["collection_sha256"]:
        raise ValueError("cohort source collection changed")
    if read_json(parent / "frozen.json") != {"cohort_id": cohort_id, "sha256": manifest["sha256"]}:
        raise ValueError("cohort freeze receipt differs")
    if manifest["identity"] != collection["identity"] or manifest["summary"] != summarize(
        root, collection
    ):
        raise ValueError("cohort source evidence changed")
    return manifest
