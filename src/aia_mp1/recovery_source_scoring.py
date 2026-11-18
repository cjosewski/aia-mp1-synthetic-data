"""Offline recovery scoring with application-resolved evidence IDs.

This development protocol preserves independent model findings and requires
separate attributed fact and score audits. It never writes human labels or an
assessed calibration receipt.
"""

from pathlib import Path
from typing import Literal

from .evaluation_schemas import DIMENSIONS, Binary, Judgment
from .evidence_judge import StrictModel
from .factcheck import SHA, Dimension
from .recovery_evidence import EvidencePlan, RuntimeEvidencePlan
from .recovery_runtime import runtime_context
from .recovery_scoring import (
    Effect,
    EvidenceFactAudit,
    RuntimeFactAudit,
    UncertaintyScoreAudit,
    fingerprint,
)
from .recovery_source_refs import SourceObservations, inspect_source_observations
from .schemas import NonBlank
from .tracing import digest


class SourceDimensionScore(StrictModel):
    decision: Binary | None
    effects: list[Effect]
    candidate_evidence: list[NonBlank]
    justification: NonBlank


class SourceScopeScore(SourceDimensionScore):
    professional_review: Literal["required", "not_required", "uncertain"]


class SourceScores(StrictModel):
    scoring_input_sha256: SHA
    D1: SourceDimensionScore
    D2: SourceDimensionScore
    D3: SourceDimensionScore
    D4: SourceScopeScore
    D5: SourceDimensionScore
    D6: SourceDimensionScore


def build_source_scoring_input(
    plan: EvidencePlan,
    content: dict,
    rubric: dict,
    source_root: Path,
    observations: SourceObservations,
    fact_audit: EvidenceFactAudit,
    *,
    allow_insufficient: bool = False,
) -> dict:
    report = inspect_source_observations(plan, content, rubric, source_root, observations)
    if report["unresolved"] and not allow_insufficient:
        raise ValueError("unresolved facts prevent strict scoring")
    if isinstance(plan, RuntimeEvidencePlan):
        if not isinstance(fact_audit, RuntimeFactAudit):
            raise ValueError("runtime evidence requires explicit applicability audit")
        runtime_audits = {row.record_id: row for row in fact_audit.runtime_records}
        if len(runtime_audits) != len(fact_audit.runtime_records) or set(runtime_audits) != {
            row.record_id for row in plan.runtime_records
        }:
            raise ValueError("runtime audit must cover every record exactly once")
        if not all(
            row.accepted
            and row.version_and_build_applicable
            and row.scheduled_cases_complete
            and row.script_matches_outputs
            and row.qualifiers_and_limits_reviewed
            for row in runtime_audits.values()
        ):
            raise ValueError("runtime audit has unresolved objections")
    if fact_audit.plan_sha256 != fingerprint(plan) or fact_audit.observations_sha256 != fingerprint(
        observations
    ):
        raise ValueError("source fact audit lineage changed")
    checks = {row.check_id: row for row in fact_audit.checks}
    if len(checks) != len(fact_audit.checks) or set(checks) != {
        row.check_id for row in plan.checks
    }:
        raise ValueError("fact audit must cover every check exactly once")
    if not all(
        (
            fact_audit.checklist_atomic_and_complete,
            fact_audit.sources_applicable_and_permitted,
            fact_audit.no_reference_rating_leakage,
            fact_audit.evidence_kinds_reviewed,
            fact_audit.authored_reasoning_checked,
            *(entry.accepted for entry in fact_audit.checks),
        )
    ):
        raise ValueError("fact audit has unresolved objections")
    result = {
        "protocol": "recovery-source-scoring-v1",
        "plan": plan.model_dump(mode="json"),
        "content": content,
        "observations": observations.model_dump(mode="json"),
        "fact_audit_sha256": fingerprint(fact_audit),
        "uncertain_check_ids": report["unresolved"] if allow_insufficient else [],
        "dimensions": {
            row["id"]: {
                "pass_anchor": row["pass_anchor"],
                "fail_anchor": row["fail_anchor"],
                "required_checks": [
                    check.check_id for check in plan.checks if row["id"] in check.dimensions
                ],
            }
            for row in rubric["dimensions"]
        },
    }
    if isinstance(plan, RuntimeEvidencePlan):
        _, result["runtime_records"] = runtime_context(plan.runtime_records, source_root)
    return result


def source_scoring_request(scoring_input: dict) -> dict:
    """Omit audit comments and duplicate source-file bytes from model input."""
    content = scoring_input["content"]
    request = {
        "protocol": scoring_input["protocol"],
        "scoring_input_sha256": digest(scoring_input),
        "untrusted_item": content["untrusted_item"],
        "untrusted_reference_context": content["untrusted_reference_context"],
        "checks": scoring_input["plan"]["checks"],
        "observations": scoring_input["observations"]["observations"],
        "dimensions": scoring_input["dimensions"],
        "uncertain_check_ids": scoring_input["uncertain_check_ids"],
        "primary_excerpts": [
            {"passage_id": f"R.fact.{i}", "version": row["version"], "text": row["text"]}
            for i, row in enumerate(content["primary_excerpts"])
        ],
        "reasoning_notes": [
            {"passage_id": f"E.{note['note_id']}", "version": digest(note), **note}
            for note in scoring_input["plan"]["reasoning_notes"]
        ],
    }
    if "runtime_records" in scoring_input:
        request["runtime_records"] = scoring_input["runtime_records"]
    return request


def inspect_source_scores(
    plan: EvidencePlan,
    content: dict,
    rubric: dict,
    source_root: Path,
    observations: SourceObservations,
    fact_audit: EvidenceFactAudit,
    scores: SourceScores,
    score_audit: UncertaintyScoreAudit | None = None,
    *,
    allow_insufficient: bool = False,
) -> dict:
    scoring_input = build_source_scoring_input(
        plan,
        content,
        rubric,
        source_root,
        observations,
        fact_audit,
        allow_insufficient=allow_insufficient,
    )
    if scores.scoring_input_sha256 != digest(scoring_input):
        raise ValueError("scores belong to a different scoring input")
    facts = {row.check_id: row for row in observations.observations}
    candidate_ids = {
        key for key, row in content["passage_catalog"].items() if row["authority"] == "candidate"
    }
    unresolved: list[Dimension] = []
    for dimension in DIMENSIONS:
        row = getattr(scores, dimension)
        effects = {effect.check_id: effect for effect in row.effects}
        required = set(scoring_input["dimensions"][dimension]["required_checks"])
        if (
            len(effects) != len(row.effects)
            or not required <= set(effects)
            or not set(effects) <= set(facts)
        ):
            raise ValueError("dimension omitted required findings or used foreign/duplicate IDs")
        if (
            len(row.candidate_evidence) != len(set(row.candidate_evidence))
            or not set(row.candidate_evidence) <= candidate_ids
            or (row.decision is not None and not row.candidate_evidence)
        ):
            raise ValueError("dimension requires distinct candidate passage IDs")
        for effect in row.effects:
            status = facts[effect.check_id].status
            if status == "insufficient" and effect.effect != "not_decisive":
                raise ValueError("uncertain finding cannot prove support or defect")
            if status == "contradicted" and effect.effect == "supports":
                raise ValueError("contradiction cannot be reversed by scorer")
            if effect.effect == "defect" and row.decision == 1:
                raise ValueError("decisive defect cannot accompany a pass")
        if (
            dimension == "D4"
            and row.professional_review == "uncertain"
            and row.decision is not None
        ):
            raise ValueError("uncertain professional-review applicability remains unresolved")
        if row.decision is None:
            unresolved.append(dimension)
    accepted = False
    rejected: list[Dimension] = []
    if score_audit is not None:
        if score_audit.scores_sha256 != fingerprint(scores):
            raise ValueError("score audit lineage changed")
        dimensions = {row.dimension: row for row in score_audit.dimensions}
        if len(dimensions) != len(score_audit.dimensions) or set(dimensions) != set(DIMENSIONS):
            raise ValueError("score audit must cover all six dimensions exactly once")
        accepted = all(row.accepted for row in score_audit.dimensions)
        rejected = [row.dimension for row in score_audit.dimensions if not row.accepted]
        needed = {
            (check.check_id, dimension)
            for check in plan.checks
            if facts[check.check_id].status == "insufficient"
            for dimension in check.dimensions
        }
        materiality = {(row.check_id, row.dimension): row for row in score_audit.materiality}
        if len(materiality) != len(score_audit.materiality) or set(materiality) != needed:
            raise ValueError("materiality must cover every uncertain dimension exactly once")
        for (check_id, dimension), finding in materiality.items():
            decision = getattr(scores, dimension).decision
            if decision == 1 and finding.finding != "immaterial":
                raise ValueError("uncertain materiality cannot accompany a pass")
            if (
                decision == 0
                and finding.finding == "uncertain"
                and not any(
                    effect.effect == "defect" and facts[effect.check_id].status != "insufficient"
                    for effect in getattr(scores, dimension).effects
                )
            ):
                raise ValueError("failure with uncertainty needs an independent decisive defect")
    judgment = None
    if accepted and not unresolved:
        judgment = Judgment.model_validate(
            {
                d: {
                    "decision": getattr(scores, d).decision,
                    "justification": getattr(scores, d).justification,
                }
                for d in DIMENSIONS
            }
        ).model_dump(mode="json")
    return {
        "status": "unresolved"
        if unresolved
        else "audit_rejected"
        if rejected
        else "audited_development"
        if judgment
        else "audit_required",
        "unresolved_dimensions": unresolved,
        "audit_rejected_dimensions": rejected,
        "judgment": judgment,
        "calibration_eligible": False,
        "scoring_input_sha256": digest(scoring_input),
        "scores_sha256": fingerprint(scores),
        "fact_audit_sha256": fingerprint(fact_audit),
        "score_audit_sha256": fingerprint(score_audit) if score_audit else None,
    }
