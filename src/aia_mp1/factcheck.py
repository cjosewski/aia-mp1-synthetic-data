"""V8 development contracts. Valid references establish traceability, not truth."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator

from .evaluation_schemas import DIMENSIONS, Judgment
from .evidence_judge import StrictModel, completion_json
from .passage_evidence import PassageID, PassageJudgment, passage_catalog
from .schemas import NonBlank
from .tracing import digest

SHA = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Dimension = Literal["D1", "D2", "D3", "D4", "D5", "D6"]
Stage = Literal["control", "facts", "score"]


class Extraction(StrictModel):
    original_path: NonBlank
    original_sha256: SHA
    extractor_path: NonBlank
    extractor_sha256: SHA
    receipt_path: NonBlank
    receipt_sha256: SHA


class Excerpt(StrictModel):
    source_id: NonBlank
    version: NonBlank
    artifact_path: NonBlank
    artifact_sha256: SHA
    byte_start: Annotated[int, Field(ge=0)]
    byte_end: Annotated[int, Field(gt=0)]
    text: str
    text_sha256: SHA
    retrieved_at: NonBlank
    license: NonBlank
    permission_path: NonBlank
    permission_sha256: SHA
    allowed_uses: list[NonBlank]
    extraction: Extraction | None = None

    @field_validator("text")
    @classmethod
    def exact_nonblank(cls, value):
        if not value.strip():
            raise ValueError("excerpt text must be nonblank")
        return value


def source_file(root: Path, name: str) -> Path:
    """Only relative, nonsymlink paths within the declared source snapshot."""
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
        raise ValueError("source path must be relative to the snapshot")
    root = root.resolve()
    path = root / relative
    if not path.resolve().is_relative_to(root) or any(
        p.is_symlink() for p in (path, *path.parents) if p != root and p.is_relative_to(root)
    ):
        raise ValueError("source path escapes the snapshot or is a symlink")
    return path


def check_excerpt(excerpt: Excerpt, root: Path | None = None) -> None:
    if (
        excerpt.byte_end <= excerpt.byte_start
        or excerpt.byte_end - excerpt.byte_start != len(excerpt.text.encode("utf-8"))
        or digest(excerpt.text) != excerpt.text_sha256
        or not {"judge_context", "local_evidence"} <= set(excerpt.allowed_uses)
        or len(set(excerpt.allowed_uses)) != len(excerpt.allowed_uses)
    ):
        raise ValueError("excerpt hash, extent or declared permissions differ")
    if root is not None:
        artifact = source_file(root, excerpt.artifact_path).read_bytes()
        permission = source_file(root, excerpt.permission_path).read_bytes()
        if (
            hashlib.sha256(artifact).hexdigest() != excerpt.artifact_sha256
            or artifact[excerpt.byte_start : excerpt.byte_end] != excerpt.text.encode("utf-8")
            or hashlib.sha256(permission).hexdigest() != excerpt.permission_sha256
        ):
            raise ValueError("source artifact, exact excerpt or permission receipt changed")
        if excerpt.extraction is not None:
            extraction = excerpt.extraction
            for name, expected in (
                (extraction.original_path, extraction.original_sha256),
                (extraction.extractor_path, extraction.extractor_sha256),
                (extraction.receipt_path, extraction.receipt_sha256),
            ):
                if hashlib.sha256(source_file(root, name).read_bytes()).hexdigest() != expected:
                    raise ValueError("original/extractor/receipt hash changed")
            receipt = json.loads(source_file(root, extraction.receipt_path).read_text("utf-8"))
            if (
                not isinstance(receipt, dict)
                or any(
                    receipt.get(key) != expected
                    for key, expected in {
                        "original_sha256": extraction.original_sha256,
                        "extractor_sha256": extraction.extractor_sha256,
                        "output_sha256": excerpt.artifact_sha256,
                    }.items()
                )
                or not receipt.get("extractor_version")
            ):
                raise ValueError("extraction receipt does not bind the original and output")


def _context(content: dict) -> None:
    """Reject metadata channels outside the existing source/task contract."""
    context = content["untrusted_reference_context"]
    if (
        not isinstance(context, dict)
        or not {"task", "sources"} <= set(context)
        or set(context) - {"task", "sources", "pack_sha256", "source_pack_sha256", "task_origin"}
    ):
        raise ValueError("unexpected reference context fields")
    task = context["task"]
    if not isinstance(task, dict) or set(task) - {"id", "brief", "category", "source_refs"}:
        raise ValueError("unexpected task fields")
    if not isinstance(context["sources"], list):
        raise ValueError("sources must be a list")
    for source in context["sources"]:
        if not isinstance(source, dict) or set(source) - {
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
            raise ValueError("unexpected authored-source fields")
        if "content_sha256" in source and source["content_sha256"] != digest(source["text"]):
            raise ValueError("authored-source text hash changed")
    # Metadata is retained verbatim, but may not introduce nested arbitrary objects.
    for record in (context, task, *context["sources"]):
        for key, value in record.items():
            if record is context and key in {"task", "sources"}:
                continue
            if not isinstance(value, str) and not (
                key in {"source_refs", "allowed_uses"}
                and isinstance(value, list)
                and all(isinstance(v, str) for v in value)
            ):
                raise ValueError("reference metadata must use the frozen text/list contract")


def fact_input(base: dict, rubric: dict, excerpts: list[dict]) -> dict:
    _context(base)
    catalog = passage_catalog(base, rubric)
    for identifier, entry in catalog.items():
        entry["authority"] = (
            "candidate"
            if identifier.startswith("C.")
            else "task"
            if identifier == "R.task"
            else "authored_summary"
            if identifier.startswith("R.source.")
            else "rubric"
        )
    for index, record in enumerate(excerpts):
        excerpt = Excerpt.model_validate(record)
        check_excerpt(excerpt)
        catalog[f"R.fact.{index}"] = {
            "path": f"/primary_excerpts/{index}/text",
            "text": excerpt.text,
            "authority": "primary_excerpt",
        }
    return deepcopy(
        {
            **base,
            "primary_excerpts": excerpts,
            "passage_index": {key: value["path"] for key, value in catalog.items()},
            "passage_catalog": catalog,
        }
    )


def validate_input(content: dict, rubric: dict, source_root: Path | None = None) -> dict:
    if set(content) != {
        "untrusted_item",
        "untrusted_reference_context",
        "primary_excerpts",
        "passage_index",
        "passage_catalog",
    } or not isinstance(content["primary_excerpts"], list):
        raise ValueError("unexpected V8 input fields")
    base = {key: content[key] for key in ("untrusted_item", "untrusted_reference_context")}
    rebuilt = fact_input(base, rubric, content["primary_excerpts"])
    if content != rebuilt:
        raise ValueError("typed catalog differs from original text and authority")
    for excerpt in content["primary_excerpts"]:
        check_excerpt(Excerpt.model_validate(excerpt), source_root)
    return rebuilt["passage_catalog"]


class Finding(StrictModel):
    candidate_ids: Annotated[list[PassageID], Field(min_length=1)]
    claim: NonBlank
    kind: Literal[
        "task_alignment",
        "api_contract",
        "procedure",
        "hazard_precaution",
        "professional_scope",
        "tip",
    ]
    task_refs: list[PassageID]
    source_refs: list[PassageID]
    status: Literal["supported", "contradicted", "insufficient"]
    explanation: NonBlank


class NonClaim(StrictModel):
    candidate_id: PassageID
    reason: NonBlank


class FactReport(StrictModel):
    findings: list[Finding]
    non_claims: list[NonClaim]


class Disposition(StrictModel):
    finding_id: Annotated[str, Field(pattern=r"^F[0-9]{4,}$")]
    position: Literal["accepted", "disputed", "needs_evidence"]
    dimensions: list[Dimension]
    reference_ids: list[PassageID]
    explanation: NonBlank


class ScoreReport(StrictModel):
    status: Literal["ready", "unresolved"]
    judgment: PassageJudgment | None
    dispositions: list[Disposition]
    unresolved_reasons: list[NonBlank]


def unique(values: list, allowed: set, name: str) -> None:
    if len(set(values)) != len(values) or not set(values) <= allowed:
        raise ValueError(f"duplicate or foreign {name}")


def validate_facts(report: FactReport, catalog: dict) -> None:
    roles = {
        role: {key for key, entry in catalog.items() if entry["authority"] == role}
        for role in ("candidate", "task", "primary_excerpt", "authored_summary")
    }
    covered = set()
    for finding in report.findings:
        unique(finding.candidate_ids, roles["candidate"], "candidate references")
        unique(finding.task_refs, roles["task"], "task references")
        unique(
            finding.source_refs,
            roles["primary_excerpt"] | roles["authored_summary"],
            "source references",
        )
        if finding.status != "insufficient":
            if not finding.task_refs and not finding.source_refs:
                raise ValueError("a factual conclusion requires evidence")
            if (
                finding.kind == "api_contract"
                and not set(finding.source_refs) & roles["primary_excerpt"]
            ):
                raise ValueError("API conclusions require a primary excerpt")
        covered.update(finding.candidate_ids)
    neutral = [entry.candidate_id for entry in report.non_claims]
    unique(neutral, roles["candidate"], "non-claim references")
    if covered & set(neutral) or covered | set(neutral) != roles["candidate"]:
        raise ValueError("candidate coverage is incomplete or overlaps non-claims")


def project_passages(report: PassageJudgment, catalog: dict) -> Judgment:
    """V7 output semantics against an independently validated V8 catalog."""
    for dimension in DIMENSIONS:
        row = getattr(report, dimension)
        unique([row.requirement, *row.evidence, *row.counter], set(catalog), "passage IDs")
        if not row.requirement.startswith("R.") or (
            row.requirement.startswith("R.D") and not row.requirement.startswith(f"R.{dimension}.")
        ):
            raise ValueError("requirement must use task/source or its own rubric anchor")
        if any(catalog[key]["authority"] != "candidate" for key in row.evidence + row.counter):
            raise ValueError("evidence and counter must cite candidate passages")
    return Judgment.model_validate(
        {
            d: {
                "decision": getattr(report, d).decision,
                "justification": getattr(report, d).justification,
            }
            for d in DIMENSIONS
        }
    )


class Memo(StrictModel):
    input_sha256: SHA
    rubric_sha256: SHA
    prompt_sha256: SHA
    runtime_sha256: SHA
    attempt_id: NonBlank
    raw_sha256: SHA
    report: FactReport
    findings: dict[str, Finding]


def make_memo(
    raw: dict, content: dict, rubric: dict, prompt: str, runtime: dict, attempt_id: str
) -> Memo:
    report = FactReport.model_validate(completion_json(raw))
    validate_facts(report, validate_input(content, rubric))
    return Memo(
        input_sha256=digest(content),
        rubric_sha256=digest(rubric),
        prompt_sha256=digest(prompt),
        runtime_sha256=digest(runtime),
        attempt_id=attempt_id,
        raw_sha256=digest(raw),
        report=report,
        findings={f"F{i:04d}": finding for i, finding in enumerate(report.findings, 1)},
    )


def validate_memo(
    memo: Memo, content: dict, rubric: dict, prompt: str, runtime: dict, attempt_id: str, raw: dict
) -> None:
    if memo != make_memo(raw, content, rubric, prompt, runtime, attempt_id):
        raise ValueError("memo differs from its accepted predecessor, raw response or input")


def project_score(report: ScoreReport, memo: Memo, catalog: dict) -> Judgment | None:
    """Caller must first verify memo lineage against its accepted ledger attempt."""
    ids = [row.finding_id for row in report.dispositions]
    unique(ids, set(memo.findings), "finding dispositions")
    if set(ids) != set(memo.findings):
        raise ValueError("every finding must receive a disposition")
    material_unknown = False
    references = {key for key in catalog if key.startswith("R.")}
    for row in report.dispositions:
        unique(row.dimensions, set(DIMENSIONS), "dimensions")
        unique(row.reference_ids, references, "reference IDs")
        if row.position == "disputed" and not any(
            catalog[key]["authority"] in {"task", "primary_excerpt", "authored_summary"}
            for key in row.reference_ids
        ):
            raise ValueError("disputed findings require task/source evidence")
        finding = memo.findings[row.finding_id]
        if (
            row.position == "disputed"
            and finding.kind == "api_contract"
            and not any(catalog[key]["authority"] == "primary_excerpt" for key in row.reference_ids)
        ):
            raise ValueError("disputed API findings require primary evidence")
        if row.dimensions and (
            row.position == "needs_evidence"
            or (row.position == "accepted" and finding.status == "insufficient")
        ):
            material_unknown = True
    if report.status == "unresolved":
        if report.judgment is not None or not report.unresolved_reasons:
            raise ValueError("unresolved requires reasons and prohibits binary projection")
        return None
    if report.judgment is None or report.unresolved_reasons or material_unknown:
        raise ValueError("ready output cannot conceal material uncertainty")
    return project_passages(report.judgment, catalog)


def resolve_report(report: PassageJudgment, catalog: dict) -> dict:
    project_passages(report, catalog)
    return {
        d: {
            field: [
                {"id": key, **catalog[key]}
                for key in (
                    [getattr(report, d).requirement]
                    if field == "requirement"
                    else getattr(getattr(report, d), field)
                )
            ]
            for field in ("requirement", "evidence", "counter")
        }
        for d in DIMENSIONS
    }
