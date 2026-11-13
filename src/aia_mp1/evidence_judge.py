"""Development-only evidence contract; no changes to assessed judge defaults.

Verbatim citations establish traceability, not truth, relevance or completeness.
Only an accepted evidence response may be projected to the existing Judgment.
"""

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .evaluation_schemas import DIMENSIONS, Binary, Judgment
from .model_client import AttemptResult
from .schemas import QAItem

CANDIDATE_FIELDS = (
    "question",
    "answer",
    "equipment_problem",
    "tools_required",
    "steps",
    "safety_info",
    "tips",
)
CandidateField = Literal[
    "question", "answer", "equipment_problem", "tools_required", "steps", "safety_info", "tips"
]
ShortText = Annotated[str, Field(min_length=1, max_length=240)]


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class Citation(StrictModel):
    path: Annotated[str, Field(min_length=1, max_length=160)]
    quote: Annotated[str, Field(min_length=8, max_length=240)]

    @field_validator("quote")
    @classmethod
    def meaningful_quote(cls, value):
        if len(value.strip()) < 8:
            raise ValueError("quote needs at least eight non-padding characters")
        return value


class EvidenceDecision(StrictModel):
    requirement: Citation
    candidate_evidence: Annotated[list[Citation], Field(min_length=1, max_length=3)]
    counterevidence: Annotated[list[Citation], Field(max_length=2)]
    missing_information: Annotated[str, Field(max_length=240)]
    searched_fields: list[CandidateField]
    decision: Binary
    justification: ShortText

    @model_validator(mode="after")
    def check_absence_claim(self):
        if len(set(self.searched_fields)) != len(self.searched_fields):
            raise ValueError("searched_fields contains duplicates")
        if self.missing_information.strip():
            if set(self.searched_fields) != set(CANDIDATE_FIELDS) or self.decision != 0:
                raise ValueError("a decisive absence claim requires all seven fields and a failure")
        elif self.searched_fields:
            raise ValueError("use empty searched_fields when no decisive absence is claimed")
        if not self.justification.strip() or len(self.justification.split()) > 40:
            raise ValueError("justification must contain one to forty words")
        return self


class EvidenceJudgment(StrictModel):
    D1: EvidenceDecision
    D2: EvidenceDecision
    D3: EvidenceDecision
    D4: EvidenceDecision
    D5: EvidenceDecision
    D6: EvidenceDecision


def citation_catalog(content: dict, rubric: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Allow only candidate text and task/source/rubric anchors, never human labels."""
    if set(content) != {"untrusted_item", "untrusted_reference_context"}:
        raise ValueError("evidence input must contain only candidate and reference context")
    candidate = content["untrusted_item"]
    QAItem.model_validate(candidate)
    if set(candidate) != set(CANDIDATE_FIELDS):
        raise ValueError("evidence input must use the canonical seven fields")
    candidate_paths = {}
    for name in CANDIDATE_FIELDS:
        value = candidate[name]
        path = f"/untrusted_item/{name}"
        if isinstance(value, list):
            candidate_paths.update({f"{path}/{i}": text for i, text in enumerate(value)})
        else:
            candidate_paths[path] = value
    reference = content["untrusted_reference_context"]
    reference_paths = {"/untrusted_reference_context/task/brief": reference["task"]["brief"]}
    for i, source in enumerate(reference["sources"]):
        reference_paths[f"/untrusted_reference_context/sources/{i}/text"] = source["text"]
    dimensions = rubric["dimensions"]
    if [d["id"] for d in dimensions] != list(DIMENSIONS):
        raise ValueError("expected the six ordered frozen rubric dimensions")
    for i, dimension in enumerate(dimensions):
        for anchor in ("pass_anchor", "fail_anchor"):
            reference_paths[f"/rubric/dimensions/{i}/{anchor}"] = dimension[anchor]
    if any(not isinstance(v, str) or not v.strip() for v in reference_paths.values()):
        raise ValueError("reference citation text must be nonblank strings")
    return candidate_paths, reference_paths


def validate_evidence(report: EvidenceJudgment, content: dict, rubric: dict) -> Judgment:
    candidate_paths, reference_paths = citation_catalog(content, rubric)
    for i, dimension in enumerate(DIMENSIONS):
        evidence = getattr(report, dimension)
        allowed_reference = {
            path: value
            for path, value in reference_paths.items()
            if not path.startswith("/rubric/") or path.startswith(f"/rubric/dimensions/{i}/")
        }
        pairs = [(evidence.requirement, allowed_reference)]
        pairs.extend((citation, candidate_paths) for citation in evidence.candidate_evidence)
        pairs.extend((citation, candidate_paths) for citation in evidence.counterevidence)
        for citation, catalog in pairs:
            if citation.path not in catalog or citation.quote not in catalog[citation.path]:
                # Avoid echoing raw model text in error messages.
                raise ValueError(f"{dimension}: citation location or exact quote does not match")
        citations = evidence.candidate_evidence + evidence.counterevidence
        if len({(c.path, c.quote) for c in citations}) != len(citations):
            raise ValueError(f"{dimension}: duplicate candidate/counterevidence citation")
    return Judgment.model_validate(
        {
            dimension: {
                "decision": getattr(report, dimension).decision,
                "justification": getattr(report, dimension).justification,
            }
            for dimension in DIMENSIONS
        }
    )


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key in evidence response")
        result[key] = value
    return result


def completion_json(raw: dict) -> dict:
    """Require complete, plain JSON and preserve the original raw response separately."""
    if not isinstance(raw, dict) or not isinstance(raw.get("choices"), list):
        raise ValueError("expected a chat completion with choices")
    if len(raw["choices"]) != 1:
        raise ValueError("evidence response must have one untruncated completion")
    choice = raw["choices"][0]
    if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
        raise ValueError("evidence response must have one untruncated completion")
    message = choice.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ValueError("evidence response must contain a text message")
    text = message["content"]
    return json.loads(text, object_pairs_hook=_unique_keys)


def parse_evidence(raw: dict) -> EvidenceJudgment:
    return EvidenceJudgment.model_validate(completion_json(raw))


class EvidenceClient:
    """Wrap a single-attempt client; validation failure consumes that attempt.

    The underlying client must request EvidenceJudgment. Full evidence stays in
    raw_response, while item contains only the validated canonical projection.
    The caller owns starts, retry budgets, immutable persistence and reporting.
    """

    def __init__(
        self,
        client,
        rubric: dict,
        *,
        parser=parse_evidence,
        validator=validate_evidence,
        input_validator=citation_catalog,
    ):
        self.client = client
        self.rubric = rubric
        self.parser = parser
        self.validator = validator
        self.input_validator = input_validator

    def generate(self, messages: list[dict]) -> AttemptResult:
        if len(messages) != 2 or [m["role"] for m in messages] != ["system", "user"]:
            raise ValueError("expected one system and one user message")
        content = json.loads(messages[1]["content"])
        self.input_validator(content, self.rubric)  # Reject bad inputs before a model call.
        result = self.client.generate(messages)
        if result.item is None:
            return result
        try:
            report = self.parser(result.raw_response)
            if report.model_dump() != result.item.model_dump():
                raise ValueError("parsed evidence differs from raw response")
            judgment = self.validator(report, content, self.rubric)
        except (ValueError, TypeError, KeyError, IndexError):
            return AttemptResult(
                item=None,
                raw_response=result.raw_response,
                error="Evidence response failed strict citation/contract validation",
                error_type="EvidenceValidationError",
                response_model=result.response_model,
            )
        return AttemptResult(
            item=judgment,
            raw_response=result.raw_response,
            error=None,
            error_type=None,
            response_model=result.response_model,
        )
