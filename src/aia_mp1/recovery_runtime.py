"""Retained experimental observations, never API documentation or human labels."""

import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt

from .evidence_judge import StrictModel
from .factcheck import SHA, source_file
from .schemas import NonBlank
from .tracing import digest

CaseID = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]*$")]


class RuntimeArtifact(StrictModel):
    path: NonBlank
    sha256: SHA


class RuntimeEvidence(StrictModel):
    record_id: Annotated[str, Field(pattern=r"^P[0-9]{4}$")]
    author: NonBlank
    origin: Literal["assistant_authored", "owner_authored"]
    created_at: NonBlank
    scope: NonBlank
    limitations: NonBlank
    provenance_limitations: NonBlank
    scheduled_cases: Annotated[list[CaseID], Field(min_length=1)]
    protocol: RuntimeArtifact
    script: RuntimeArtifact
    dependency_lock: RuntimeArtifact
    identities: Annotated[list[RuntimeArtifact], Field(min_length=1)]
    raw_result: RuntimeArtifact
    permission: RuntimeArtifact


class ProcessCapture(StrictModel):
    case: CaseID
    returncode: StrictInt | None
    stdout: str | None
    stderr: str | None
    timeout: StrictBool


def artifact_text(artifact: RuntimeArtifact, root: Path) -> str:
    data = source_file(root, artifact.path).read_bytes()
    if hashlib.sha256(data).hexdigest() != artifact.sha256:
        raise ValueError("runtime artifact bytes changed")
    return data.decode("utf-8")


def runtime_context(records: list[RuntimeEvidence], root: Path) -> tuple[dict, list[dict]]:
    """Verify bytes/accounting and expose all cases; applicability needs a separate audit."""
    if [r.record_id for r in records] != [f"P{i:04d}" for i in range(1, len(records) + 1)]:
        raise ValueError("runtime record IDs must be ordered and unique")
    catalog = {}
    views = []
    for record in records:
        if len(set(record.scheduled_cases)) != len(record.scheduled_cases):
            raise ValueError("duplicate scheduled runtime case")
        artifacts = {
            name: {
                **getattr(record, name).model_dump(),
                "text": artifact_text(getattr(record, name), root),
            }
            for name in ("protocol", "script", "dependency_lock", "raw_result", "permission")
        }
        identities = [{**a.model_dump(), "text": artifact_text(a, root)} for a in record.identities]
        paths = [a["path"] for a in artifacts.values()] + [a["path"] for a in identities]
        if len(set(paths)) != len(paths):
            raise ValueError("runtime artifact roles must use distinct files")
        permission = json.loads(artifacts["permission"]["text"])
        if (
            not isinstance(permission, dict)
            or permission.get("origin") != "standalone_personal_research"
            or not {"judge_context", "local_evidence"} <= set(permission.get("allowed_uses", []))
        ):
            raise ValueError("runtime reuse permission is missing")
        result = json.loads(artifacts["raw_result"]["text"])
        if not isinstance(result, dict) or not isinstance(result.get("cases"), list):
            raise ValueError("runtime result must retain process captures")
        captures = [ProcessCapture.model_validate(c) for c in result["cases"]]
        if [c.case for c in captures] != record.scheduled_cases:
            raise ValueError("runtime captures must account for the whole ordered schedule")
        if any(
            not c.timeout and c.returncode is not None and (c.stdout is None or c.stderr is None)
            for c in captures
        ):
            raise ValueError("completed process captures require both retained streams")
        record_unresolved = any(c.timeout or c.returncode is None for c in captures)
        version = digest(record.model_dump(mode="json"))
        passages = []
        # Preserve the original decoded stream exactly, without an authored summary.
        # Keep every case visible even when a check cites just one counterexample.
        for capture in captures:
            for stream in ("stdout", "stderr"):
                text = getattr(capture, stream)
                if text is None or not text.strip():
                    continue
                passage_id = f"P.{record.record_id}.{capture.case}.{stream}"
                catalog[passage_id] = {
                    "text": text,
                    "authority": "runtime_observation",
                    "version": version,
                    "record_id": record.record_id,
                    "unresolved": record_unresolved,
                }
                passages.append({"passage_id": passage_id, "text": text, "version": version})
        views.append(
            {
                **record.model_dump(mode="json"),
                "version": version,
                "artifacts": artifacts,
                "identity_artifacts": identities,
                "captures": [c.model_dump(mode="json") for c in captures],
                "passages": passages,
            }
        )
    return catalog, views
