"""Offline recovery prototype. Structural checks do not establish factual truth.

No model dispatch, human labels, canonical judgments or calibration projection.
Keep historical V8 validators unchanged so their saved evidence still replays.
"""

import argparse
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator

from .evidence_judge import StrictModel
from .factcheck import SHA, Dimension, unique, validate_input
from .schemas import NonBlank
from .tracing import digest

CheckID = Annotated[str, Field(pattern=r"^K[0-9]{4}$")]


class Span(StrictModel):
    passage_id: NonBlank
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(gt=0)]
    quote: str

    @field_validator("quote")
    @classmethod
    def preserve_quote(cls, value):
        if not value.strip():
            raise ValueError("quote must contain non-whitespace text")
        return value


class SourceBinding(StrictModel):
    passage_id: NonBlank
    version: NonBlank


class Check(StrictModel):
    check_id: CheckID
    kind: Literal["task_obligation", "technical_claim", "context"]
    subject: Span
    question: NonBlank
    dimensions: Annotated[list[Dimension], Field(min_length=1)]
    sources: list[SourceBinding]


class CheckPlan(StrictModel):
    protocol: Literal["recovery-offline-v1"]
    input_sha256: SHA
    rubric_sha256: SHA
    checks: Annotated[list[Check], Field(min_length=1)]


class Observation(StrictModel):
    check_id: CheckID
    status: Literal["supported", "contradicted", "insufficient"]
    citations: list[Span]
    explanation: NonBlank


class Observations(StrictModel):
    plan_sha256: SHA
    observations: list[Observation]


def check_span(span: Span, catalog: dict) -> None:
    """Offsets are Python Unicode character offsets, not source-file byte offsets."""
    if span.passage_id not in catalog:
        raise ValueError("unknown passage in span")
    text = catalog[span.passage_id]["text"]
    if span.end <= span.start or span.end > len(text) or text[span.start : span.end] != span.quote:
        raise ValueError("span does not reproduce exact original text")


def validate_plan(plan: CheckPlan, content: dict, rubric: dict, source_root: Path) -> dict:
    """Validate retained sources and a separately prepared, label-free checklist.

    Cover all non-whitespace characters in task and candidate passages exactly
    once. This prevents skipped passages, NOT bundled/omitted semantic claims.
    """
    catalog = validate_input(content, rubric, source_root)
    if plan.input_sha256 != digest(content) or plan.rubric_sha256 != digest(rubric):
        raise ValueError("plan input or rubric fingerprint changed")
    identifiers = [check.check_id for check in plan.checks]
    if identifiers != [f"K{i:04d}" for i in range(1, len(identifiers) + 1)]:
        raise ValueError("check IDs must be unique, ordered application IDs")
    covered = {
        key: set() for key, row in catalog.items() if row["authority"] in {"candidate", "task"}
    }
    context_ids = {"C.question", "C.equipment_problem"}
    for check in plan.checks:
        subject = check.subject
        check_span(subject, catalog)
        if subject.passage_id not in covered:
            raise ValueError("check subject must be task or candidate text")
        unique(check.dimensions, {f"D{i}" for i in range(1, 7)}, "dimensions")
        source_ids = [source.passage_id for source in check.sources]
        unique(source_ids, set(catalog), "bound sources")
        if subject.passage_id == "R.task":
            if check.kind != "task_obligation" or "D1" not in check.dimensions:
                raise ValueError("task obligations must include completeness")
        elif subject.passage_id in context_ids:
            if check.kind != "context" or "D5" not in check.dimensions:
                raise ValueError("question/problem context must include D5")
        else:
            required = {"D1", "D3"}
            if subject.passage_id.startswith("C.tips."):
                required.add("D6")
            if subject.passage_id == "C.safety_info":
                required.add("D2")
            if check.kind != "technical_claim" or not required <= set(check.dimensions):
                raise ValueError("technical text cannot bypass required dimension review")
        for source in check.sources:
            role = catalog[source.passage_id]["authority"]
            if role == "primary_excerpt":
                index = int(source.passage_id.removeprefix("R.fact."))
                if source.version != content["primary_excerpts"][index]["version"]:
                    raise ValueError("source version differs from retained excerpt")
            elif role == "task" and check.kind != "technical_claim":
                if source.version != "frozen-task":
                    raise ValueError("task binding must use frozen-task version")
            else:
                raise ValueError("bound evidence must have the required authority")
        positions = set(range(subject.start, subject.end))
        if covered[subject.passage_id] & positions:
            raise ValueError("overlapping checklist spans")
        covered[subject.passage_id].update(positions)
    for key, positions in covered.items():
        required = {i for i, char in enumerate(catalog[key]["text"]) if not char.isspace()}
        if not required <= positions:
            raise ValueError(f"uncovered task/candidate text: {key}")
    return catalog


def inspect_offline(
    plan: CheckPlan,
    content: dict,
    rubric: dict,
    source_root: Path,
    response: Observations | None = None,
) -> dict:
    catalog = validate_plan(plan, content, rubric, source_root)
    plan_hash = digest(plan.model_dump(mode="json"))
    gaps = [check.check_id for check in plan.checks if not check.sources]
    result = {
        "protocol": plan.protocol,
        "plan_sha256": plan_hash,
        "checks": len(plan.checks),
        "source_gaps": gaps,
        "response_checked": response is not None,
        "unresolved": [],
        "contradicted": [],
        "structural_status": "source_gaps" if gaps else "awaiting_observations",
        "semantic_audit": "required",
        "calibration_eligible": False,
        "model_calls": 0,
    }
    if response is None:
        return result
    if response.plan_sha256 != plan_hash:
        raise ValueError("observations belong to a different checklist")
    rows = {row.check_id: row for row in response.observations}
    if len(rows) != len(response.observations) or set(rows) != {c.check_id for c in plan.checks}:
        raise ValueError("observations must cover each check exactly once")
    for check in plan.checks:
        row = rows[check.check_id]
        allowed = {source.passage_id for source in check.sources}
        citation_keys = []
        for citation in row.citations:
            check_span(citation, catalog)
            if citation.passage_id not in allowed:
                raise ValueError("observation cites evidence outside its frozen bindings")
            citation_keys.append((citation.passage_id, citation.start, citation.end))
        if len(set(citation_keys)) != len(citation_keys):
            raise ValueError("duplicate evidence citation")
        if row.status != "insufficient" and not row.citations:
            raise ValueError("factual conclusion needs a bound, exact citation")
        if row.status == "insufficient":
            result["unresolved"].append(row.check_id)
        elif row.status == "contradicted":
            result["contradicted"].append(row.check_id)
    result["structural_status"] = (
        "unresolved" if result["unresolved"] else "awaiting_semantic_audit"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Retained V8-format fact input")
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--observations", type=Path)
    args = parser.parse_args(argv)
    try:

        def load(path):
            return json.loads(path.read_text(encoding="utf-8"))

        result = inspect_offline(
            CheckPlan.model_validate(load(args.plan)),
            load(args.input),
            load(args.rubric),
            args.sources,
            Observations.model_validate(load(args.observations)) if args.observations else None,
        )
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        # Schema errors can contain input values; don't print source/response contents.
        print(json.dumps({"error": "offline validation failed", "type": type(exc).__name__}))
        return 2
    print(json.dumps(result, indent=2))
    return 1 if result["source_gaps"] or result["unresolved"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
