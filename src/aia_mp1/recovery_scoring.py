"""Offline recovery scoring with explicit audit lineage; never human labels.

An audit is an attributed review record, not cryptographic proof of truth. No
transport or assessed-calibration writer is provided by this development module.
"""

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Literal

from .evaluation_schemas import DIMENSIONS, Binary, Judgment
from .evidence_judge import StrictModel
from .factcheck import SHA, Dimension
from .recovery_checks import (
    CheckID,
    CheckPlan,
    Observations,
    Span,
    check_span,
    inspect_offline,
)
from .recovery_evidence import EvidencePlan, RuntimeEvidencePlan, inspect_evidence, parse_plan
from .recovery_runtime import runtime_context
from .schemas import NonBlank
from .tracing import digest


class CheckAudit(StrictModel):
    check_id: CheckID
    accepted: bool
    explanation: NonBlank


class FactAudit(StrictModel):
    plan_sha256: SHA
    observations_sha256: SHA
    auditor: NonBlank
    origin: Literal["assistant_review", "human_review"]
    reviewed_at: NonBlank
    checklist_atomic_and_complete: bool
    sources_applicable_and_permitted: bool
    no_reference_rating_leakage: bool
    checks: list[CheckAudit]


class EvidenceFactAudit(FactAudit):
    evidence_kinds_reviewed: bool
    authored_reasoning_checked: bool


class RuntimeApplicabilityAudit(StrictModel):
    record_id: NonBlank
    accepted: bool
    version_and_build_applicable: bool
    scheduled_cases_complete: bool
    script_matches_outputs: bool
    qualifiers_and_limits_reviewed: bool
    explanation: NonBlank


class RuntimeFactAudit(EvidenceFactAudit):
    runtime_records: list[RuntimeApplicabilityAudit]


class Effect(StrictModel):
    check_id: CheckID
    effect: Literal["supports", "defect", "not_decisive"]
    explanation: NonBlank


class DimensionScore(StrictModel):
    decision: Binary | None
    effects: list[Effect]
    candidate_evidence: list[Span]
    justification: NonBlank


class ScopeScore(DimensionScore):
    professional_review: Literal["required", "not_required", "uncertain"]


class Scores(StrictModel):
    scoring_input_sha256: SHA
    D1: DimensionScore
    D2: DimensionScore
    D3: DimensionScore
    D4: ScopeScore
    D5: DimensionScore
    D6: DimensionScore


class DimensionAudit(StrictModel):
    dimension: Dimension
    accepted: bool
    explanation: NonBlank


class ScoreAudit(StrictModel):
    scores_sha256: SHA
    auditor: NonBlank
    origin: Literal["assistant_review", "human_review"]
    reviewed_at: NonBlank
    dimensions: list[DimensionAudit]


def fingerprint(model: StrictModel) -> str:
    return digest(model.model_dump(mode="json"))


def build_scoring_input(
    plan: CheckPlan | EvidencePlan,
    content: dict,
    rubric: dict,
    source_root: Path,
    observations: Observations,
    audit: FactAudit,
) -> dict:
    """Recheck evidence before scoring; no unknown facts or unreviewed gaps."""
    if isinstance(plan, EvidencePlan):
        report = inspect_evidence(plan, content, rubric, source_root, observations)
        if not isinstance(audit, EvidenceFactAudit) or not (
            audit.evidence_kinds_reviewed and audit.authored_reasoning_checked
        ):
            raise ValueError("v2 requires evidence-kind and authored-reasoning audit")
        if isinstance(plan, RuntimeEvidencePlan):
            if not isinstance(audit, RuntimeFactAudit):
                raise ValueError("v3 requires explicit runtime applicability audits")
            records = {r.record_id: r for r in audit.runtime_records}
            if len(records) != len(audit.runtime_records) or set(records) != {
                r.record_id for r in plan.runtime_records
            }:
                raise ValueError("runtime audits must cover every record exactly once")
            if not all(
                r.accepted
                and r.version_and_build_applicable
                and r.scheduled_cases_complete
                and r.script_matches_outputs
                and r.qualifiers_and_limits_reviewed
                for r in records.values()
            ):
                raise ValueError("runtime applicability audit has unresolved objections")
    else:
        if type(audit) is not FactAudit:
            raise ValueError("v1 requires its original audit contract")
        report = inspect_offline(plan, content, rubric, source_root, observations)
    if report["unresolved"] or report["source_gaps"]:
        raise ValueError("unresolved facts prevent scoring")
    if audit.plan_sha256 != fingerprint(plan) or audit.observations_sha256 != fingerprint(
        observations
    ):
        raise ValueError("fact audit lineage changed")
    checked = {entry.check_id: entry for entry in audit.checks}
    if len(checked) != len(audit.checks) or set(checked) != {c.check_id for c in plan.checks}:
        raise ValueError("fact audit must cover every check exactly once")
    if not all(
        (
            audit.checklist_atomic_and_complete,
            audit.sources_applicable_and_permitted,
            audit.no_reference_rating_leakage,
            *(entry.accepted for entry in audit.checks),
        )
    ):
        raise ValueError("fact audit has unresolved objections")
    # Audits stay in the application envelope. Their commentary is not judge input.
    result = {
        "protocol": "recovery-scoring-v3"
        if isinstance(plan, RuntimeEvidencePlan)
        else "recovery-scoring-v2"
        if isinstance(plan, EvidencePlan)
        else "recovery-scoring-v1",
        "fact_audit_sha256": fingerprint(audit),
        "plan": plan.model_dump(mode="json"),
        "observations": observations.model_dump(mode="json"),
        "content": content,
        "dimensions": {
            row["id"]: {
                "pass_anchor": row["pass_anchor"],
                "fail_anchor": row["fail_anchor"],
                "required_checks": [c.check_id for c in plan.checks if row["id"] in c.dimensions],
            }
            for row in rubric["dimensions"]
        },
    }
    if isinstance(plan, RuntimeEvidencePlan):
        _, result["runtime_records"] = runtime_context(plan.runtime_records, source_root)
    return result


def scoring_request(scoring_input: dict) -> dict:
    """Lossless text view without the repeated passage catalog or audit comments.

    Call with build_scoring_input's validated result. Preserve its fingerprint
    in the wire envelope so the model copies an application-supplied value.
    Actual transport/token preflight is deliberately not part of this module.
    """
    content = scoring_input["content"]
    request = {
        "scoring_input_sha256": digest(scoring_input),
        "untrusted_item": content["untrusted_item"],
        "untrusted_reference_context": content["untrusted_reference_context"],
        "checks": scoring_input["plan"]["checks"],
        "observations": scoring_input["observations"]["observations"],
        "dimensions": scoring_input["dimensions"],
        "primary_excerpts": [
            {"passage_id": f"R.fact.{i}", "version": row["version"], "text": row["text"]}
            for i, row in enumerate(content["primary_excerpts"])
        ],
    }
    if scoring_input["protocol"] in {"recovery-scoring-v2", "recovery-scoring-v3"}:
        request["protocol"] = scoring_input["protocol"]
        request["reasoning_notes"] = [
            {"passage_id": f"E.{n['note_id']}", "version": digest(n), **n}
            for n in scoring_input["plan"]["reasoning_notes"]
        ]
    if scoring_input["protocol"] == "recovery-scoring-v3":
        request["runtime_records"] = scoring_input["runtime_records"]
    return deepcopy(request)


def inspect_scores(
    plan: CheckPlan | EvidencePlan,
    content: dict,
    rubric: dict,
    source_root: Path,
    observations: Observations,
    fact_audit: FactAudit,
    scores: Scores,
    score_audit: ScoreAudit | None = None,
) -> dict:
    scoring_input = build_scoring_input(
        plan, content, rubric, source_root, observations, fact_audit
    )
    if scores.scoring_input_sha256 != digest(scoring_input):
        raise ValueError("scores belong to a different scoring input")
    facts = {row.check_id: row for row in observations.observations}
    resolved = {}
    unresolved = []
    for dimension in DIMENSIONS:
        row = getattr(scores, dimension)
        effects = {entry.check_id: entry for entry in row.effects}
        required = set(scoring_input["dimensions"][dimension]["required_checks"])
        if (
            len(effects) != len(row.effects)
            or not required <= set(effects)
            or not set(effects) <= set(facts)
        ):
            raise ValueError("dimension omitted required findings or used duplicate/foreign IDs")
        if row.decision is not None and not row.candidate_evidence:
            raise ValueError("resolved dimension requires candidate evidence")
        seen = set()
        for citation in row.candidate_evidence:
            check_span(citation, content["passage_catalog"])
            if content["passage_catalog"][citation.passage_id]["authority"] != "candidate":
                raise ValueError("dimension evidence must cite candidate text")
            key = (citation.passage_id, citation.start, citation.end)
            if key in seen:
                raise ValueError("duplicate candidate citation")
            seen.add(key)
        for effect in row.effects:
            if facts[effect.check_id].status == "contradicted" and effect.effect == "supports":
                raise ValueError("scorer cannot reverse an audited contradiction")
            if effect.effect == "defect" and row.decision == 1:
                raise ValueError("a decisive rubric defect cannot accompany a pass")
        if (
            dimension == "D4"
            and row.professional_review == "uncertain"
            and row.decision is not None
        ):
            raise ValueError("uncertain professional-review applicability remains unresolved")
        if row.decision is None:
            unresolved.append(dimension)
        resolved[dimension] = {
            **scoring_input["dimensions"][dimension],
            **row.model_dump(mode="json"),
            "findings": [
                {
                    "check": next(c for c in plan.checks if c.check_id == key).model_dump(
                        mode="json"
                    ),
                    "observation": facts[key].model_dump(mode="json"),
                }
                for key in effects
            ],
        }
    accepted = False
    rejected = []
    if score_audit is not None:
        if score_audit.scores_sha256 != fingerprint(scores):
            raise ValueError("score audit lineage changed")
        dimensions = {row.dimension: row for row in score_audit.dimensions}
        if len(dimensions) != len(score_audit.dimensions) or set(dimensions) != set(DIMENSIONS):
            raise ValueError("score audit must cover all six dimensions exactly once")
        accepted = all(row.accepted for row in score_audit.dimensions)
        rejected = [row.dimension for row in score_audit.dimensions if not row.accepted]
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
        "model_calls": 0,
        "scoring_input_sha256": digest(scoring_input),
        "scores_sha256": fingerprint(scores),
        "fact_audit_sha256": fingerprint(fact_audit),
        "score_audit_sha256": fingerprint(score_audit) if score_audit else None,
        "resolved_dimensions": resolved,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "rubric", "sources", "plan", "observations", "fact-audit", "scores"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--score-audit", type=Path)
    args = parser.parse_args(argv)
    try:

        def load(path):
            return json.loads(path.read_text(encoding="utf-8"))

        plan = parse_plan(load(args.plan))
        audit_class = (
            RuntimeFactAudit
            if isinstance(plan, RuntimeEvidencePlan)
            else EvidenceFactAudit
            if isinstance(plan, EvidencePlan)
            else FactAudit
        )
        report = inspect_scores(
            plan,
            load(args.input),
            load(args.rubric),
            args.sources,
            Observations.model_validate(load(args.observations)),
            audit_class.model_validate(load(args.fact_audit)),
            Scores.model_validate(load(args.scores)),
            ScoreAudit.model_validate(load(args.score_audit)) if args.score_audit else None,
        )
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(
            json.dumps({"error": "offline scoring validation failed", "type": type(exc).__name__})
        )
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["judgment"] is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
