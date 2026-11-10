"""Append-only run evidence and explicit, replaceable run checkpoints."""

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: str | dict) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def run_directory(root: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", run_id):
        raise ValueError("run ID must be 1–64 letters, digits, underscores or hyphens")
    root = root.resolve()
    target = root / run_id
    if target.resolve().parent != root or target.is_symlink():
        raise ValueError("run directory must stay within the artifact root")
    return target


def append_record(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid JSONL record at {path.name}:{number}; preserve and inspect it"
            ) from exc
        if not isinstance(record, dict):
            raise ValueError(f"expected JSON object at {path.name}:{number}")
        records.append(record)
    return records


def write_checkpoint(path: Path, record: dict) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as tmp:
        tmp.write(json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        tmp.flush()
        os.fsync(tmp.fileno())
        temporary = tmp.name
    os.replace(temporary, path)


def artifact_hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.glob("*.jsonl"))
    }
