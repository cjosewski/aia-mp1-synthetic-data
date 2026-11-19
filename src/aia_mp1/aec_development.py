"""Ground a development judge in a checklist prepared before it sees the answer."""

import re
from typing import Annotated, Literal

from pydantic import Field

from .evidence_judge import StrictModel
from .passage_evidence import PassageID, PassageJudgment, validate_passage, validate_passage_input
from .schemas import NonBlank


class ReferenceCheck(StrictModel):
    task_passage: NonBlank
    expected_evidence: NonBlank
    basis: Literal["task", "source", "unresolved"]
    source_passages: list[PassageID]


class TaskChecklist(StrictModel):
    checks: Annotated[list[ReferenceCheck], Field(min_length=1, max_length=15)]


def reference_catalog(context: dict) -> dict:
    task = re.split(r"(?<=[.!?;])\s+(?=[A-Za-z])", context["task"]["brief"])
    sources = {}
    for source in context["sources"]:
        for index, line in enumerate(source["text"].splitlines(), 1):
            if line.strip():
                sources[f"{source['id']}.{index}"] = {"text": line, "version": source["version"]}
    return {"task": {f"B{i}": line for i, line in enumerate(task, 1)}, "sources": sources}


def checked_reference(plan: TaskChecklist, catalog: dict) -> list[dict]:
    rows = []
    for index, check in enumerate(plan.checks, 1):
        if check.task_passage not in catalog["task"]:
            raise ValueError("Checklist obligation has no matching task passage")
        if check.basis == "source":
            if (
                not check.source_passages
                or not set(check.source_passages) <= catalog["sources"].keys()
            ):
                raise ValueError("Checklist source passage does not resolve")
        elif check.source_passages:
            raise ValueError("Only a source-based claim can carry a source citation")
        rows.append(
            {
                "id": f"T{index}",
                **check.model_dump(),
                "task_text": catalog["task"][check.task_passage],
                "sources": {k: catalog["sources"][k] for k in check.source_passages},
            }
        )
    return rows


class CoverageFinding(StrictModel):
    check_id: NonBlank
    status: Literal["established", "gap", "check_exceeds_task"]
    candidate_ids: list[PassageID]
    reason: NonBlank


class TipFinding(StrictModel):
    tip_id: PassageID
    status: Literal["adds_value", "repeats", "technical_error", "tangential"]
    dependency_ids: list[PassageID]
    reason: NonBlank


class DevelopmentJudgment(StrictModel):
    coverage: list[CoverageFinding]
    tips: list[TipFinding]
    ratings: PassageJudgment


def checked_judgment(result: DevelopmentJudgment, content: dict, rubric: dict, checks: list[dict]):
    catalog = validate_passage_input(content, rubric)
    evidence = {key for key in catalog if key.startswith("C.")}
    if [r.check_id for r in result.coverage] != [r["id"] for r in checks]:
        raise ValueError("Coverage must address every ordered task obligation")
    if [r.tip_id for r in result.tips] != [key for key in catalog if key.startswith("C.tips.")]:
        raise ValueError("Tip findings must cover every candidate tip in order")
    for row in result.coverage:
        if row.status == "established" and not row.candidate_ids:
            raise ValueError("A fulfilled obligation must identify the candidate evidence")
        if not set(row.candidate_ids) <= evidence or len(row.candidate_ids) != len(
            set(row.candidate_ids)
        ):
            raise ValueError("Invalid candidate coverage references")
    for tip in result.tips:
        if not set(tip.dependency_ids) <= evidence - {tip.tip_id} or len(
            set(tip.dependency_ids)
        ) != len(tip.dependency_ids):
            raise ValueError("Invalid tip dependency references")
    return validate_passage(result.ratings, content, rubric)
