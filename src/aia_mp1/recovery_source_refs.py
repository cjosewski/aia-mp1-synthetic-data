"""Versioned source-ID observations for recovery development.

The model chooses only frozen source bindings. Structural validation does not
establish that a source supports a claim; every finding still needs an attributed
technical audit before it can inform a dimension score.
"""

from pathlib import Path
from typing import Literal

from .evidence_judge import StrictModel
from .factcheck import SHA
from .recovery_checks import CheckID, SourceBinding
from .recovery_evidence import EvidencePlan, evidence_request, fingerprint, validate_evidence_plan
from .schemas import NonBlank


class SourceObservation(StrictModel):
    check_id: CheckID
    status: Literal["supported", "contradicted", "insufficient"]
    sources: list[SourceBinding]
    explanation: NonBlank


class SourceObservations(StrictModel):
    protocol: Literal["recovery-source-refs-v1"]
    plan_sha256: SHA
    observations: list[SourceObservation]


def source_request(plan: EvidencePlan, content: dict, rubric: dict, source_root: Path) -> dict:
    """Return the old validated evidence request with an explicit ID-only contract."""
    request = evidence_request(plan, content, rubric, source_root)
    request["observation_protocol"] = "recovery-source-refs-v1"
    return request


def inspect_source_observations(
    plan: EvidencePlan,
    content: dict,
    rubric: dict,
    source_root: Path,
    response: SourceObservations,
) -> dict:
    """Check lineage, complete coverage and exact allowed source identities.

    A source ID identifies the entire immutable, versioned source passage. Its
    relevance to the specific claim is a separate semantic-audit decision.
    """
    validate_evidence_plan(plan, content, rubric, source_root)
    if response.plan_sha256 != fingerprint(plan):
        raise ValueError("source observations belong to a different evidence plan")
    if [row.check_id for row in response.observations] != [check.check_id for check in plan.checks]:
        raise ValueError("source observations must cover every ordered check exactly once")
    unresolved, contradicted = [], []
    for check, row in zip(plan.checks, response.observations, strict=True):
        allowed = {(s.passage_id, s.version) for s in check.sources}
        cited = [(s.passage_id, s.version) for s in row.sources]
        if len(cited) != len(set(cited)) or not set(cited) <= allowed:
            raise ValueError(f"{check.check_id}: duplicate or unbound source reference")
        if row.status != "insufficient" and not cited:
            raise ValueError(f"{check.check_id}: conclusion requires a bound source reference")
        if row.status == "insufficient":
            unresolved.append(check.check_id)
        elif row.status == "contradicted":
            contradicted.append(check.check_id)
    return {
        "protocol": response.protocol,
        "plan_sha256": response.plan_sha256,
        "checks": len(plan.checks),
        "unresolved": unresolved,
        "contradicted": contradicted,
        "semantic_audit": "required",
        "calibration_eligible": False,
    }
