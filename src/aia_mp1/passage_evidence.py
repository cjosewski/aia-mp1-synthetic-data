"""V7 development protocol: cite application-supplied immutable text locations."""

from typing import Annotated

from pydantic import Field

from .evaluation_schemas import DIMENSIONS, Binary, Judgment
from .evidence_judge import EvidenceClient, StrictModel, citation_catalog, completion_json
from .schemas import NonBlank

PassageID = Annotated[str, Field(min_length=1, max_length=80)]


class PassageDecision(StrictModel):
    requirement: PassageID
    evidence: Annotated[list[PassageID], Field(min_length=1, max_length=64)]
    counter: Annotated[list[PassageID], Field(max_length=64)]
    decision: Binary
    justification: NonBlank


class PassageJudgment(StrictModel):
    D1: PassageDecision
    D2: PassageDecision
    D3: PassageDecision
    D4: PassageDecision
    D5: PassageDecision
    D6: PassageDecision


def passage_catalog(content: dict, rubric: dict) -> dict[str, dict[str, str]]:
    """Each passage is one complete original field/list entry, never model text."""
    candidates, references = citation_catalog(content, rubric)
    catalog = {}
    for path, text in candidates.items():
        identifier = "C." + path.removeprefix("/untrusted_item/").replace("/", ".")
        catalog[identifier] = {"path": path, "text": text}
    for path, text in references.items():
        if path == "/untrusted_reference_context/task/brief":
            identifier = "R.task"
        elif path.startswith("/untrusted_reference_context/sources/"):
            identifier = "R.source." + path.split("/")[3]
        else:
            _, _, _, index, anchor = path.split("/")
            identifier = f"R.{DIMENSIONS[int(index)]}.{anchor.removesuffix('_anchor')}"
        catalog[identifier] = {"path": path, "text": text}
    return catalog


def passage_input(content: dict, rubric: dict) -> dict:
    catalog = passage_catalog(content, rubric)
    return {
        **content,
        "passage_index": {identifier: p["path"] for identifier, p in catalog.items()},
    }


def validate_passage_input(content: dict, rubric: dict) -> dict:
    if set(content) != {"untrusted_item", "untrusted_reference_context", "passage_index"}:
        raise ValueError("expected candidate, reference context and application passage index")
    base = {key: value for key, value in content.items() if key != "passage_index"}
    catalog = passage_catalog(base, rubric)
    if content["passage_index"] != {identifier: p["path"] for identifier, p in catalog.items()}:
        raise ValueError("passage index differs from original candidate/reference locations")
    return catalog


def parse_passage(raw: dict) -> PassageJudgment:
    return PassageJudgment.model_validate(completion_json(raw))


def validate_passage(report: PassageJudgment, content: dict, rubric: dict) -> Judgment:
    catalog = validate_passage_input(content, rubric)
    for dimension in DIMENSIONS:
        row = getattr(report, dimension)
        ids = [row.requirement, *row.evidence, *row.counter]
        if any(identifier not in catalog for identifier in ids):
            raise ValueError(f"{dimension}: unknown passage ID")
        if len(set(ids)) != len(ids):
            raise ValueError(f"{dimension}: repeated or conflicting passage reference")
        if not row.requirement.startswith("R.") or (
            row.requirement.startswith("R.D") and not row.requirement.startswith(f"R.{dimension}.")
        ):
            raise ValueError(f"{dimension}: requirement must cite task, source or its own anchor")
        if any(not identifier.startswith("C.") for identifier in row.evidence + row.counter):
            raise ValueError(f"{dimension}: evidence and counter must cite the candidate")
    return Judgment.model_validate(
        {
            d: {
                "decision": getattr(report, d).decision,
                "justification": getattr(report, d).justification,
            }
            for d in DIMENSIONS
        }
    )


def resolved_passages(report: PassageJudgment, content: dict, rubric: dict) -> dict:
    """Return auditable full text only after validating the model's references."""
    validate_passage(report, content, rubric)
    catalog = validate_passage_input(content, rubric)
    return {
        d: {
            "requirement": {
                "id": getattr(report, d).requirement,
                **catalog[getattr(report, d).requirement],
            },
            **{
                field: [
                    {"id": identifier, **catalog[identifier]}
                    for identifier in getattr(getattr(report, d), field)
                ]
                for field in ("evidence", "counter")
            },
        }
        for d in DIMENSIONS
    }


class PassageEvidenceClient(EvidenceClient):
    def __init__(self, client, rubric: dict):
        super().__init__(
            client,
            rubric,
            parser=parse_passage,
            validator=validate_passage,
            input_validator=validate_passage_input,
        )
