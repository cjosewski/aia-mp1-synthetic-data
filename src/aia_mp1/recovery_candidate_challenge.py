"""Offline candidate-applicability challenge for source-ID findings.

This is a development probe. It cannot amend a rejected journal, release a
score request, or create a human label. A valid challenge still needs a
separate technical audit of the cited candidate and source passages.
"""

from typing import Literal

from .evidence_judge import StrictModel
from .factcheck import SHA
from .recovery_checks import CheckID, SourceBinding
from .recovery_evidence import EvidencePlan, fingerprint
from .recovery_source_refs import SourceObservations
from .schemas import NonBlank


class ApplicabilityFinding(StrictModel):
    check_id: CheckID
    verdict: Literal["retain", "reject", "insufficient"]
    candidate_passage_ids: list[NonBlank]
    source_refs: list[SourceBinding]
    prerequisite: NonBlank
    explanation: NonBlank


class CandidateApplicabilityChallenge(StrictModel):
    protocol: Literal["candidate-applicability-challenge-v1"]
    plan_sha256: SHA
    observations_sha256: SHA
    findings: list[ApplicabilityFinding]


def challenge_request(plan: EvidencePlan, content: dict, observations: SourceObservations) -> dict:
    """Present every tentative support with the full candidate and bound evidence.

    The original source observations are untrusted model output. Their status is
    not accepted merely because this request can be built.
    """
    if observations.plan_sha256 != fingerprint(plan):
        raise ValueError("observations belong to a different plan")
    if [row.check_id for row in observations.observations] != [row.check_id for row in plan.checks]:
        raise ValueError("observations must cover ordered checks")
    for check, observation in zip(plan.checks, observations.observations, strict=True):
        allowed = {(row.passage_id, row.version) for row in check.sources}
        cited = [(row.passage_id, row.version) for row in observation.sources]
        if (
            len(cited) != len(set(cited))
            or not set(cited) <= allowed
            or (observation.status == "supported" and not cited)
        ):
            raise ValueError("observation has unbound or missing source references")
    supported = {
        row.check_id: row for row in observations.observations if row.status == "supported"
    }
    return {
        "protocol": "candidate-applicability-challenge-v1",
        "plan_sha256": fingerprint(plan),
        "observations_sha256": fingerprint(observations),
        "untrusted_item": content["untrusted_item"],
        "candidate_passages": [
            {"passage_id": passage_id, "text": row["text"]}
            for passage_id, row in content["passage_catalog"].items()
            if row["authority"] == "candidate"
        ],
        "supported_checks": [
            {
                "check_id": check.check_id,
                "subject": check.subject.model_dump(mode="json"),
                "question": check.question,
                "candidate_claim": supported[check.check_id].explanation,
                "source_refs": [row.model_dump(mode="json") for row in check.sources],
            }
            for check in plan.checks
            if check.check_id in supported
        ],
        "primary_excerpts": [
            {"passage_id": f"R.fact.{index}", "version": row["version"], "text": row["text"]}
            for index, row in enumerate(content["primary_excerpts"])
        ],
        "reasoning_notes": [
            {"passage_id": f"E.{note.note_id}", "text": note.reasoning}
            for note in plan.reasoning_notes
        ],
        "reference_task": content["untrusted_reference_context"],
    }


def inspect_candidate_challenge(
    plan: EvidencePlan,
    content: dict,
    observations: SourceObservations,
    challenge: CandidateApplicabilityChallenge,
) -> dict:
    """Validate lineage and references; never certify semantic applicability."""
    request = challenge_request(plan, content, observations)
    if (
        challenge.plan_sha256 != request["plan_sha256"]
        or challenge.observations_sha256 != request["observations_sha256"]
    ):
        raise ValueError("challenge lineage differs from the saved facts")
    expected = [row["check_id"] for row in request["supported_checks"]]
    if [row.check_id for row in challenge.findings] != expected:
        raise ValueError("challenge must cover tentative support in order")
    candidate_ids = {row["passage_id"] for row in request["candidate_passages"]}
    checks = {row.check_id: row for row in plan.checks}
    rejected = []
    unresolved = []
    for finding in challenge.findings:
        if len(finding.candidate_passage_ids) != len(set(finding.candidate_passage_ids)):
            raise ValueError("duplicate candidate passage")
        if not set(finding.candidate_passage_ids) <= candidate_ids:
            raise ValueError("foreign candidate passage")
        allowed = {(row.passage_id, row.version) for row in checks[finding.check_id].sources}
        cited = [(row.passage_id, row.version) for row in finding.source_refs]
        if len(cited) != len(set(cited)) or not set(cited) <= allowed:
            raise ValueError("foreign or duplicate source reference")
        if finding.verdict == "retain" and (
            not finding.candidate_passage_ids or not finding.source_refs
        ):
            raise ValueError("retained support needs candidate and source references")
        if finding.verdict == "reject":
            rejected.append(finding.check_id)
        elif finding.verdict == "insufficient":
            unresolved.append(finding.check_id)
    return {
        "status": "awaiting_technical_audit",
        "reviewed_supported_checks": len(expected),
        "challenged_support": rejected,
        "unresolved_support": unresolved,
        "calibration_eligible": False,
    }
