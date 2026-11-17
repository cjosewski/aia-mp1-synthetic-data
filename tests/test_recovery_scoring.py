"""Synthetic scoring/audit adversaries; fixtures are not authentic human reviews."""

import json
from copy import deepcopy

import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_checks import span

from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.recovery_checks import CheckPlan, Observations
from aia_mp1.recovery_scoring import (
    FactAudit,
    ScoreAudit,
    Scores,
    build_scoring_input,
    fingerprint,
    inspect_scores,
    main,
    scoring_request,
)
from aia_mp1.tracing import digest


@pytest.fixture
def scoring(packet):
    plan, content, rubric, root, rows = packet
    plan = CheckPlan.model_validate(plan)
    observations = Observations.model_validate(
        {"plan_sha256": fingerprint(plan), "observations": rows}
    )
    audit = FactAudit.model_validate(
        {
            "plan_sha256": fingerprint(plan),
            "observations_sha256": fingerprint(observations),
            "auditor": "Synthetic test actor",
            "origin": "assistant_review",
            "reviewed_at": "test-only",
            "checklist_atomic_and_complete": True,
            "sources_applicable_and_permitted": True,
            "no_reference_rating_leakage": True,
            "checks": [
                {"check_id": c.check_id, "accepted": True, "explanation": "Synthetic audit."}
                for c in plan.checks
            ],
        }
    )
    args = [plan, content, rubric, root, observations, audit]
    payload = build_scoring_input(*args)
    scores = {"scoring_input_sha256": digest(payload)}
    for d in DIMENSIONS:
        scores[d] = {
            "decision": 1,
            "effects": [
                {"check_id": k, "effect": "supports", "explanation": "Synthetic effect."}
                for k in payload["dimensions"][d]["required_checks"]
            ],
            "candidate_evidence": [span("C.answer", content["untrusted_item"]["answer"])],
            "justification": "Synthetic score, not human review.",
        }
    scores["D4"]["professional_review"] = "not_required"
    scores = Scores.model_validate(scores)
    score_audit = ScoreAudit.model_validate(
        {
            "scores_sha256": fingerprint(scores),
            "auditor": "Synthetic test actor",
            "origin": "assistant_review",
            "reviewed_at": "test-only",
            "dimensions": [
                {"dimension": d, "accepted": True, "explanation": "Synthetic audit."}
                for d in DIMENSIONS
            ],
        }
    )
    return args, scores, score_audit


def test_unreviewed_scores_never_project_or_become_calibration(scoring):
    args, scores, audit = scoring
    before = deepcopy(scores)
    report = inspect_scores(*args, scores)
    assert report["status"] == "audit_required"
    assert report["judgment"] is None
    report = inspect_scores(*args, scores, audit)
    assert report["status"] == "audited_development"
    assert set(report["judgment"]) == set(DIMENSIONS)
    assert report["calibration_eligible"] is False
    assert report["model_calls"] == 0
    assert scores == before
    assert (
        report["resolved_dimensions"]["D4"]["pass_anchor"]
        == args[2]["dimensions"][3]["pass_anchor"]
    )


def test_scoring_view_preserves_source_text_and_ids_without_audit_commentary(scoring):
    args, _, _ = scoring
    args[5].checks[0].explanation = "AUDIT_COMMENT_NOT_FOR_MODEL"
    full = build_scoring_input(*args)
    request = scoring_request(full)
    assert request["scoring_input_sha256"] == digest(full)
    assert request["untrusted_item"] == args[1]["untrusted_item"]
    assert request["untrusted_reference_context"] == args[1]["untrusted_reference_context"]
    assert request["checks"] == full["plan"]["checks"]
    assert request["observations"] == full["observations"]["observations"]
    for i, row in enumerate(request["primary_excerpts"]):
        assert row["passage_id"] == f"R.fact.{i}"
        assert row["text"] == args[1]["primary_excerpts"][i]["text"]
        assert row["version"] == args[1]["primary_excerpts"][i]["version"]
    assert "AUDIT_COMMENT_NOT_FOR_MODEL" not in json.dumps(request)
    request["untrusted_item"]["answer"] = "Changed transport copy."
    assert full["content"]["untrusted_item"]["answer"] != "Changed transport copy."


@pytest.mark.parametrize(
    "mutation",
    [
        "unresolved_fact",
        "audit_rejected",
        "missing_audit",
        "duplicate_audit",
        "wrong_plan",
        "wrong_response",
        "permission",
        "atomicity",
        "label_leakage",
    ],
)
def test_fact_stage_cannot_be_bypassed(scoring, mutation):
    args, _, _ = scoring
    obs, audit = args[4:]
    if mutation == "unresolved_fact":
        obs.observations[0].status = "insufficient"
        audit.observations_sha256 = fingerprint(obs)
    elif mutation == "audit_rejected":
        audit.checks[0].accepted = False
    elif mutation == "missing_audit":
        audit.checks.pop()
    elif mutation == "duplicate_audit":
        audit.checks.append(deepcopy(audit.checks[0]))
    elif mutation == "wrong_plan":
        audit.plan_sha256 = "0" * 64
    elif mutation == "wrong_response":
        audit.observations_sha256 = "0" * 64
    elif mutation == "permission":
        audit.sources_applicable_and_permitted = False
    elif mutation == "atomicity":
        audit.checklist_atomic_and_complete = False
    else:
        audit.no_reference_rating_leakage = False
    with pytest.raises(ValueError):
        build_scoring_input(*args)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_tip",
        "duplicate_check",
        "foreign_check",
        "source_as_candidate",
        "prose_as_id",
        "changed_fact_audit",
        "changed_candidate",
        "pass_with_defect",
        "no_candidate",
    ],
)
def test_scorer_roles_coverage_and_input_identity_are_enforced(scoring, mutation):
    args, scores, _ = scoring
    if mutation == "missing_tip":
        scores.D6.effects.pop()
    elif mutation == "duplicate_check":
        scores.D6.effects.append(deepcopy(scores.D6.effects[0]))
    elif mutation == "foreign_check":
        scores.D6.effects[0].check_id = "K9999"
    elif mutation == "source_as_candidate":
        scores.D1.candidate_evidence[0].passage_id = "R.fact.0"
    elif mutation == "prose_as_id":
        value = scores.model_dump()
        value["D1"]["effects"][0]["check_id"] = "Completeness requires all actions."
        with pytest.raises(ValueError):
            Scores.model_validate(value)
        return
    elif mutation == "changed_fact_audit":
        args[5].checks[0].explanation = "Different audit changes the envelope fingerprint."
    elif mutation == "changed_candidate":
        args[1]["untrusted_item"]["tips"][0] += " Extra instruction."
    elif mutation == "pass_with_defect":
        scores.D6.effects[0].effect = "defect"
    else:
        scores.D1.candidate_evidence = []
    with pytest.raises(ValueError):
        inspect_scores(*args, scores)


def test_contradiction_cannot_be_reversed_but_can_be_irrelevant_to_a_dimension(scoring):
    args, scores, _ = scoring
    tip_id = scores.D6.effects[0].check_id
    next(r for r in args[4].observations if r.check_id == tip_id).status = "contradicted"
    args[5].observations_sha256 = fingerprint(args[4])
    scores.scoring_input_sha256 = digest(build_scoring_input(*args))
    with pytest.raises(ValueError, match="reverse"):
        inspect_scores(*args, scores)
    for d in DIMENSIONS:
        for effect in getattr(scores, d).effects:
            if effect.check_id == tip_id:
                effect.effect = "not_decisive"
                effect.explanation = (
                    "Synthetic rationale requires semantic audit; not an auto-pass."
                )
    assert inspect_scores(*args, scores)["judgment"] is None
    scores.D6.effects[0].effect = "defect"
    scores.D6.decision = 0
    assert inspect_scores(*args, scores)["status"] == "audit_required"


@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "changed_score", "rejected", "uncertain"]
)
def test_final_audit_cannot_supply_missing_scores_or_approve_other_bytes(scoring, mutation):
    args, scores, audit = scoring
    if mutation == "missing":
        audit.dimensions.pop()
    elif mutation == "duplicate":
        audit.dimensions.append(deepcopy(audit.dimensions[0]))
    elif mutation == "changed_score":
        scores.D1.justification = "Changed after audit."
    elif mutation == "rejected":
        audit.dimensions[0].accepted = False
        report = inspect_scores(*args, scores, audit)
        assert report["judgment"] is None
        assert report["audit_rejected_dimensions"] == ["D1"]
        assert report["status"] == "audit_rejected"
        return
    else:
        scores.D4.professional_review = "uncertain"
    with pytest.raises(ValueError):
        inspect_scores(*args, scores, audit)


def test_explicit_unknown_dimension_survives_an_accepting_audit(scoring):
    args, scores, audit = scoring
    scores.D4.professional_review = "uncertain"
    scores.D4.decision = None
    audit.scores_sha256 = fingerprint(scores)
    report = inspect_scores(*args, scores, audit)
    assert report["unresolved_dimensions"] == ["D4"]
    assert report["judgment"] is None


def test_cli_offline_unreviewed_failure_and_accepted_receipt(scoring, tmp_path, capsys):
    args, scores, audit = scoring
    values = dict(
        zip(
            ("plan", "input", "rubric", "observations", "fact-audit", "scores"),
            (args[0], args[1], args[2], args[4], args[5], scores),
        )
    )
    argv = ["--sources", str(args[3])]
    for key, value in values.items():
        path = tmp_path / f"{key}.json"
        path.write_text(json.dumps(value.model_dump() if hasattr(value, "model_dump") else value))
        argv.extend([f"--{key}", str(path)])
    assert main(argv) == 1
    assert json.loads(capsys.readouterr().out)["judgment"] is None
    path = tmp_path / "audit.json"
    path.write_text(audit.model_dump_json())
    assert main(argv + ["--score-audit", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["calibration_eligible"] is False
    path.write_text('{"secret": "DO_NOT_ECHO"}')
    assert main(argv + ["--score-audit", str(path)]) == 2
    assert "DO_NOT_ECHO" not in capsys.readouterr().out
