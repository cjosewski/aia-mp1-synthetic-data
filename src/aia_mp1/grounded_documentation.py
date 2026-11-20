"""Small, attribution-checked development evidence contract; never computes verdicts."""

from typing import Annotated, Literal

from pydantic import Field

from .evaluation_schemas import Judgment
from .evidence_judge import StrictModel

Text = Annotated[str, Field(min_length=1, max_length=360)]
Status = Literal["supported", "contradicted", "missing", "uncertain"]


class FieldEvidence(StrictModel):
    candidate_ids: Annotated[list[str], Field(max_length=8)]
    status: Status
    note: Text


class TaskEvidence(FieldEvidence):
    task_quote: Text


class TipEvidence(FieldEvidence):
    tip_id: str


class DocumentationEvidence(StrictModel):
    candidate_id: str
    passage_id: str | None
    quote: Text | None
    status: Literal["supported", "contradicted", "uncertain"]
    note: Text


class GroundedJudgment(StrictModel):
    task_checks: Annotated[list[TaskEvidence], Field(min_length=1, max_length=8)]
    safety: FieldEvidence
    bindings: Annotated[list[TaskEvidence], Field(min_length=1, max_length=8)]
    tips: Annotated[list[TipEvidence], Field(max_length=8)]
    documentation: Annotated[list[DocumentationEvidence], Field(max_length=10)]
    ratings: Judgment


def candidate_catalog(case):
    item = case["untrusted_item"]
    fields = (
        "question",
        "answer",
        "equipment_problem",
        "tools_required",
        "steps",
        "safety_info",
        "tips",
    )
    if set(item) != set(fields):
        raise ValueError("Expected the original seven candidate fields")
    result = {}
    for field in fields:
        value = item[field]
        if isinstance(value, list):
            for index, text in enumerate(value):
                result[f"{field}[{index}]"] = text
        else:
            result[field] = value
    if any(not isinstance(text, str) for text in result.values()):
        raise ValueError("Candidate evidence must resolve to original text")
    return result


def validate_grounding(result, case, pages):
    """Reject attribution errors, without deciding whether a semantic claim is correct."""
    catalog = candidate_catalog(case)
    task = case["untrusted_reference_context"]["task"]["brief"]
    expected_tips = [key for key in catalog if key.startswith("tips[")]
    if [row.tip_id for row in result.tips] != expected_tips:
        raise ValueError("Grounding must address every original tip in order")
    for row in [*result.task_checks, result.safety, *result.bindings, *result.tips]:
        if (
            len(row.candidate_ids) != len(set(row.candidate_ids))
            or not set(row.candidate_ids) <= catalog.keys()
        ):
            raise ValueError("Candidate field ID does not resolve uniquely")
        if row.status in {"supported", "contradicted"} and not row.candidate_ids:
            raise ValueError("Positive or contrary evidence must locate a candidate field")
    for row in result.tips:
        if row.tip_id not in row.candidate_ids:
            raise ValueError("Each tip finding must locate its original tip")
    if not set(result.safety.candidate_ids) <= {"safety_info"}:
        raise ValueError("D2 evidence may only cite safety_info")
    for row in [*result.task_checks, *result.bindings]:
        if not row.task_quote.strip() or row.task_quote not in task:
            raise ValueError("Task grounding quote is not an exact original task span")
    passages = {
        f"{page['id']}.{excerpt['id']}": excerpt["text"]
        for page in pages
        for excerpt in page["excerpts"]
    }
    for row in result.documentation:
        if row.candidate_id not in catalog:
            raise ValueError("Documentation claim candidate ID does not resolve")
        if row.passage_id is None:
            if row.quote is not None or row.status != "uncertain":
                raise ValueError("Missing documentation is uncertain, not evidence of absence")
        elif row.passage_id not in passages:
            raise ValueError("Documentation passage ID was not shown")
        elif row.quote is not None and (
            not row.quote.strip() or row.quote not in passages[row.passage_id]
        ):
            raise ValueError("Documentation quote is not in the cited shown passage")
    return result.ratings
