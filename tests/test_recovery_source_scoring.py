"""Synthetic source-ID scoring attacks; never assessed calibration evidence."""

from copy import deepcopy

import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_evidence import audit_for
from test_recovery_evidence import evidence as evidence
from test_recovery_source_refs import response_for

from aia_mp1.recovery_evidence import EvidencePlan
from aia_mp1.recovery_scoring import UncertaintyScoreAudit, fingerprint
from aia_mp1.recovery_source_refs import SourceObservations
from aia_mp1.recovery_source_scoring import (
    SourceScores,
    build_source_scoring_input,
    inspect_source_scores,
    source_scoring_request,
)
from aia_mp1.tracing import digest


def setup(evidence, *, uncertain=False):
    raw_plan, content, rubric, root = evidence
    plan = EvidencePlan.model_validate(raw_plan)
    raw = response_for(raw_plan)
    if uncertain:
        raw["observations"][0]["status"] = "insufficient"
        raw["observations"][0]["sources"] = []
    observations = SourceObservations.model_validate(raw)
    fact_audit = audit_for(raw_plan, observations)
    scoring_input = build_source_scoring_input(
        plan, content, rubric, root, observations, fact_audit, allow_insufficient=uncertain
    )
    scores = {
        "scoring_input_sha256": digest(scoring_input),
        **{
            dimension: {
                "decision": 1,
                "effects": [
                    {
                        "check_id": check_id,
                        "effect": "not_decisive"
                        if uncertain and check_id == "K0001"
                        else "supports",
                        "explanation": "Synthetic finding only.",
                    }
                    for check_id in row["required_checks"]
                ],
                "candidate_evidence": ["C.answer"],
                "justification": "Synthetic judgment only.",
                **({"professional_review": "not_required"} if dimension == "D4" else {}),
            }
            for dimension, row in scoring_input["dimensions"].items()
        },
    }
    return plan, content, rubric, root, observations, fact_audit, scoring_input, scores


def test_source_ids_score_only_after_separate_audits(evidence):
    plan, content, rubric, root, obs, fact_audit, scoring_input, raw = setup(evidence)
    request = source_scoring_request(scoring_input)
    assert request["scoring_input_sha256"] == digest(scoring_input)
    assert request["observations"] == obs.model_dump(mode="json")["observations"]
    scores = SourceScores.model_validate(raw)
    report = inspect_source_scores(plan, content, rubric, root, obs, fact_audit, scores)
    assert report["status"] == "audit_required" and report["judgment"] is None
    audit = UncertaintyScoreAudit.model_validate(
        {
            "scores_sha256": fingerprint(scores),
            "auditor": "Synthetic reviewer",
            "origin": "assistant_review",
            "reviewed_at": "test-only",
            "dimensions": [
                {"dimension": f"D{i}", "accepted": True, "explanation": "Synthetic audit."}
                for i in range(1, 7)
            ],
            "materiality": [],
        }
    )
    report = inspect_source_scores(plan, content, rubric, root, obs, fact_audit, scores, audit)
    assert report["status"] == "audited_development"
    assert report["calibration_eligible"] is False


@pytest.mark.parametrize(
    "attack", ["foreign_candidate", "duplicate_candidate", "wrong_fact_hash", "missing_effect"]
)
def test_source_scorer_rejects_foreign_or_incomplete_evidence(evidence, attack):
    plan, content, rubric, root, obs, fact_audit, _, raw = setup(evidence)
    raw = deepcopy(raw)
    if attack == "foreign_candidate":
        raw["D1"]["candidate_evidence"] = ["R.task"]
    elif attack == "duplicate_candidate":
        raw["D1"]["candidate_evidence"] = ["C.answer", "C.answer"]
    elif attack == "wrong_fact_hash":
        raw["scoring_input_sha256"] = "0" * 64
    else:
        raw["D1"]["effects"].pop()
    with pytest.raises(ValueError):
        inspect_source_scores(
            plan, content, rubric, root, obs, fact_audit, SourceScores.model_validate(raw)
        )


def test_uncertain_fact_cannot_become_support_or_pass_without_materiality(evidence):
    plan, content, rubric, root, obs, fact_audit, _, raw = setup(evidence, uncertain=True)
    affected = next(
        d
        for d in (f"D{i}" for i in range(1, 7))
        if any(effect["check_id"] == "K0001" for effect in raw[d]["effects"])
    )
    tampered = deepcopy(raw)
    next(effect for effect in tampered[affected]["effects"] if effect["check_id"] == "K0001")[
        "effect"
    ] = "supports"
    with pytest.raises(ValueError, match="uncertain finding"):
        inspect_source_scores(
            plan,
            content,
            rubric,
            root,
            obs,
            fact_audit,
            SourceScores.model_validate(tampered),
            allow_insufficient=True,
        )
    scores = SourceScores.model_validate(raw)
    audit = UncertaintyScoreAudit.model_validate(
        {
            "scores_sha256": fingerprint(scores),
            "auditor": "Synthetic reviewer",
            "origin": "assistant_review",
            "reviewed_at": "test-only",
            "dimensions": [
                {"dimension": f"D{i}", "accepted": True, "explanation": "Synthetic audit."}
                for i in range(1, 7)
            ],
            "materiality": [],
        }
    )
    with pytest.raises(ValueError, match="materiality"):
        inspect_source_scores(
            plan,
            content,
            rubric,
            root,
            obs,
            fact_audit,
            scores,
            audit,
            allow_insufficient=True,
        )
