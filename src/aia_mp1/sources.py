"""Permission-checked, content-addressed reference packs for assessed requests."""

import json
from pathlib import Path

from .schemas import CATEGORIES
from .tracing import digest


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"reference pack requires {name}")
    return value


def validate_pack(pack: dict) -> dict:
    """Validate a self-contained snapshot; permission is an attributed decision."""
    if pack.get("schema_version") != "1":
        raise ValueError("unsupported reference pack version")
    if set(pack) != {
        "schema_version",
        "pack_id",
        "version",
        "approved_by",
        "approved_at",
        "approval_basis",
        "permission_status",
        "sources",
        "tasks",
    }:
        raise ValueError("unexpected reference pack fields")
    for key in ("pack_id", "version", "approved_by", "approved_at", "approval_basis"):
        _text(pack.get(key), key)
    if pack.get("permission_status") != "approved_for_assessed_generation":
        raise ValueError("reference pack is not cleared for assessed generation")
    sources = pack.get("sources")
    tasks = pack.get("tasks")
    if not isinstance(sources, list) or not sources or not isinstance(tasks, list):
        raise ValueError("reference pack requires sources and tasks")
    by_id = {}
    for source in sources:
        if set(source) != {
            "id",
            "url",
            "version",
            "retrieved_at",
            "license",
            "license_evidence",
            "attribution",
            "installation",
            "text",
            "content_sha256",
            "allowed_uses",
            "export_permission",
        }:
            raise ValueError("unexpected reference source fields")
        for key in (
            "id",
            "url",
            "version",
            "retrieved_at",
            "license",
            "license_evidence",
            "attribution",
            "installation",
            "text",
            "content_sha256",
        ):
            _text(source.get(key), key)
        if source["id"] in by_id:
            raise ValueError("duplicate reference source")
        if source["content_sha256"] != digest(source["text"]):
            raise ValueError("reference content hash differs")
        if not {"assessed_generation", "human_review", "judge_context", "local_evidence"} <= set(
            source.get("allowed_uses", [])
        ):
            raise ValueError("reference uses are not cleared")
        if source.get("export_permission") not in {"permitted", "local_only"}:
            raise ValueError("reference export permission must be explicit")
        by_id[source["id"]] = source
    seen, briefs = set(), set()
    counts = dict.fromkeys(CATEGORIES, 0)
    for task in tasks:
        if set(task) != {"id", "brief", "category", "source_refs"}:
            raise ValueError("unexpected reference task fields; scores do not belong in context")
        task_id = _text(task.get("id"), "task id")
        brief = _text(task.get("brief"), "task brief")
        if task_id in seen or brief.strip().casefold() in briefs:
            raise ValueError("duplicate task identity or brief")
        seen.add(task_id)
        briefs.add(brief.strip().casefold())
        if task.get("category") not in CATEGORIES:
            raise ValueError("unknown reference task category")
        refs = task.get("source_refs")
        if not isinstance(refs, list) or not refs or len(set(refs)) != len(refs):
            raise ValueError("task requires unique source references")
        if not set(refs) <= set(by_id):
            raise ValueError("task references an unknown source")
        counts[task["category"]] += 1
    if any(count < 10 for count in counts.values()):
        raise ValueError("reference pack needs ten distinct tasks per category")
    return pack


def load_pack(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError("symlink reference pack is not supported")
    pack = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(pack, dict):
        raise ValueError("reference pack must be an object")
    return validate_pack(pack)


def context_for(pack: dict, category: str, ordinal: int) -> dict:
    tasks = [t for t in pack["tasks"] if t["category"] == category]
    task = tasks[ordinal % len(tasks)]
    sources = {s["id"]: s for s in pack["sources"]}
    return {
        "pack_sha256": digest(pack),
        "task": task,
        "sources": [sources[ref] for ref in task["source_refs"]],
    }
