"""V6 development contract: shared citations, strict references, no score repair."""

from typing import Annotated

from pydantic import Field, field_validator

from .evaluation_schemas import DIMENSIONS, Binary, Judgment
from .evidence_judge import (
    EvidenceClient,
    StrictModel,
    citation_catalog,
    completion_json,
)

Index = Annotated[int, Field(strict=True, ge=0, le=23)]


class CompactCitation(StrictModel):
    path: Annotated[str, Field(min_length=1, max_length=40)]
    quote: Annotated[str, Field(min_length=8, max_length=160)]

    @field_validator("quote")
    @classmethod
    def nonblank_quote(cls, value):
        if len(value.strip()) < 8:
            raise ValueError("quote must contain at least eight non-padding characters")
        return value


class CompactDecision(StrictModel):
    requirement: Index
    evidence: Annotated[list[Index], Field(min_length=1, max_length=24)]
    counter: Annotated[list[Index], Field(max_length=24)]
    decision: Binary
    justification: Annotated[str, Field(min_length=1, max_length=240)]

    @field_validator("justification")
    @classmethod
    def concise_justification(cls, value):
        if not value.strip() or len(value.split()) > 40:
            raise ValueError("justification must contain one to forty words")
        return value


class CompactJudgment(StrictModel):
    citations: Annotated[list[CompactCitation], Field(min_length=2, max_length=24)]
    D1: CompactDecision
    D2: CompactDecision
    D3: CompactDecision
    D4: CompactDecision
    D5: CompactDecision
    D6: CompactDecision


def compact_catalog(content: dict, rubric: dict) -> tuple[dict, dict]:
    candidates, requirements = citation_catalog(content, rubric)
    candidates = {
        path.removeprefix("/untrusted_item/").replace("/", "."): value
        for path, value in candidates.items()
    }
    references = {"task": requirements["/untrusted_reference_context/task/brief"]}
    for i, source in enumerate(content["untrusted_reference_context"]["sources"]):
        references[f"source.{i}"] = source["text"]
    for i, dimension in enumerate(DIMENSIONS):
        for anchor in ("pass", "fail"):
            references[f"{dimension}.{anchor}"] = requirements[
                f"/rubric/dimensions/{i}/{anchor}_anchor"
            ]
    return candidates, references


def parse_compact(raw: dict) -> CompactJudgment:
    return CompactJudgment.model_validate(completion_json(raw))


def validate_compact(report: CompactJudgment, content: dict, rubric: dict) -> Judgment:
    candidates, references = compact_catalog(content, rubric)
    catalog = candidates | references
    for citation in report.citations:
        if citation.path not in catalog or citation.quote not in catalog[citation.path]:
            raise ValueError("citation location or exact quote does not match")
    for dimension in DIMENSIONS:
        row = getattr(report, dimension)
        indices = [row.requirement, *row.evidence, *row.counter]
        if any(index >= len(report.citations) for index in indices):
            raise ValueError(f"{dimension}: citation index does not exist")
        if len(set(indices)) != len(indices):
            raise ValueError(f"{dimension}: repeated or conflicting citation reference")
        requirement = report.citations[row.requirement].path
        if requirement not in references or (
            requirement.startswith("D") and not requirement.startswith(dimension + ".")
        ):
            raise ValueError(f"{dimension}: requirement must cite task, source or its own anchor")
        if any(
            report.citations[index].path not in candidates for index in row.evidence + row.counter
        ):
            raise ValueError(f"{dimension}: evidence and counter must cite candidate fields")
    return Judgment.model_validate(
        {
            d: {
                "decision": getattr(report, d).decision,
                "justification": getattr(report, d).justification,
            }
            for d in DIMENSIONS
        }
    )


class CompactEvidenceClient(EvidenceClient):
    def __init__(self, client, rubric: dict):
        super().__init__(client, rubric, parser=parse_compact, validator=validate_compact)
