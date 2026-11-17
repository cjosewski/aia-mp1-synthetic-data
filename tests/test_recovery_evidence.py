"""Synthetic evidence-role attacks; no authentic reviews or real-item findings."""

import json
from copy import deepcopy

import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_checks import span
from test_recovery_scoring import scoring as scoring

from aia_mp1.recovery_checks import Observations
from aia_mp1.recovery_evidence import (
    EvidencePlan,
    evidence_request,
    inspect_evidence,
    main,
    parse_plan,
)
from aia_mp1.recovery_scoring import (
    Effect,
    EvidenceFactAudit,
    FactAudit,
    build_scoring_input,
    fingerprint,
    inspect_scores,
    scoring_request,
)
from aia_mp1.tracing import digest


@pytest.fixture
def evidence(packet):
    parent, content, rubric, root, _ = packet
    checks = []
    notes = []
    for original in parent["checks"]:
        check = deepcopy(original)
        check.update(
            parent_check_id=original["check_id"],
            evidence_kind="api_contract",
            basis_rationale="Synthetic API claim.",
        )
        if "D3" not in check["dimensions"]:
            check["dimensions"].append("D3")
        passage = check["subject"]["passage_id"]
        if passage == "R.task":
            check["evidence_kind"] = "task_comparison"
            check["sources"] = [{"passage_id": "R.task", "version": "frozen-task"}]
        elif passage in ("C.answer", "C.tips.0"):
            kind = "mathematical_derivation" if passage == "C.answer" else "workflow_reasoning"
            note = {
                "note_id": f"N{len(notes) + 1:04d}",
                "kind": kind,
                "author": "Synthetic test author",
                "origin": "assistant_authored",
                "created_at": "test-only",
                "premises": [deepcopy(check["subject"])],
                "reasoning": "Synthetic derivation α; not a real finding.",
                "limitations": "Does not prove an API exists or the candidate is true.",
            }
            notes.append(note)
            check["evidence_kind"] = kind
            check["sources"] = [{"passage_id": f"E.{note['note_id']}", "version": digest(note)}]
        checks.append(check)
    plan = {
        "protocol": "recovery-evidence-v2",
        "input_sha256": digest(content),
        "rubric_sha256": digest(rubric),
        "parent_plan_sha256": digest(parent),
        "parent_plan": deepcopy(parent),
        "reasoning_notes": notes,
        "checks": checks,
    }
    return plan, content, rubric, root


def inspect(evidence):
    plan, content, rubric, root = evidence
    return inspect_evidence(EvidencePlan.model_validate(plan), content, rubric, root)


def response(evidence):
    plan, content, _, _ = evidence
    catalog = {key: value["text"] for key, value in content["passage_catalog"].items()}
    catalog.update({f"E.{n['note_id']}": n["reasoning"] for n in plan["reasoning_notes"]})
    return Observations.model_validate(
        {
            "plan_sha256": digest(plan),
            "observations": [
                {
                    "check_id": c["check_id"],
                    "status": "supported",
                    "explanation": "Synthetic only.",
                    "citations": [
                        span(c["sources"][0]["passage_id"], catalog[c["sources"][0]["passage_id"]])
                    ],
                }
                for c in plan["checks"]
            ],
        }
    )


def audit_for(plan, observations, **overrides):
    return EvidenceFactAudit.model_validate(
        {
            "plan_sha256": digest(plan),
            "observations_sha256": digest(observations.model_dump(mode="json")),
            "auditor": "Synthetic reviewer",
            "origin": "assistant_review",
            "reviewed_at": "test-only",
            "checklist_atomic_and_complete": True,
            "sources_applicable_and_permitted": True,
            "no_reference_rating_leakage": True,
            "evidence_kinds_reviewed": True,
            "authored_reasoning_checked": True,
            "checks": [
                {"check_id": c["check_id"], "accepted": True, "explanation": "Synthetic review."}
                for c in plan["checks"]
            ],
            **overrides,
        }
    )


def test_separate_authorities_are_not_a_truth_or_calibration_certificate(evidence):
    before = deepcopy(evidence[:3])
    result = inspect(evidence)
    assert set(result["evidence_kinds"]) == {
        "api_contract",
        "task_comparison",
        "mathematical_derivation",
        "workflow_reasoning",
    }
    assert result["evidence_kind_audit"] == result["authored_reasoning_audit"] == "required"
    assert result["calibration_eligible"] is False
    assert result["model_calls"] == 0 and result["source_gaps"] == []
    assert evidence[:3] == before


@pytest.mark.parametrize(
    "kind,foreign",
    [
        ("api_contract", "R.task"),
        ("api_contract", "E.N0001"),
        ("api_contract", "C.answer"),
        ("task_comparison", "R.fact.0"),
        ("mathematical_derivation", "E.N0002"),
        ("workflow_reasoning", "E.N0001"),
        ("workflow_reasoning", "C.tips.0"),
    ],
)
def test_evidence_role_laundering_fails(evidence, kind, foreign):
    check = next(c for c in evidence[0]["checks"] if c["evidence_kind"] == kind)
    check["sources"][0]["passage_id"] = foreign
    with pytest.raises(ValueError, match="authority"):
        inspect(evidence)


@pytest.mark.parametrize(
    "mutation", ["note", "note_version", "parent", "parent_hash", "input", "rubric"]
)
def test_bound_lineage_changes_fail(evidence, mutation):
    plan = evidence[0]
    if mutation == "note":
        plan["reasoning_notes"][0]["reasoning"] = "Changed conclusion."
    elif mutation == "note_version":
        next(c for c in plan["checks"] if c["evidence_kind"] == "workflow_reasoning")["sources"][0][
            "version"
        ] = "0" * 64
    elif mutation == "parent":
        plan["parent_plan"]["checks"][0]["question"] = "Altered parent."
    else:
        key = {
            "parent_hash": "parent_plan_sha256",
            "input": "input_sha256",
            "rubric": "rubric_sha256",
        }[mutation]
        plan[key] = "0" * 64
    with pytest.raises(ValueError):
        inspect(evidence)


@pytest.mark.parametrize(
    "mutation",
    ["candidate_role", "rubric_premise", "unknown_premise", "duplicate_premise", "unused_note"],
)
def test_reasoning_does_not_get_a_hidden_reference_channel(evidence, mutation):
    plan, content, _, _ = evidence
    note = plan["reasoning_notes"][0]
    if mutation == "candidate_role":
        note["origin"] = "primary_documentation"
    elif mutation == "unused_note":
        extra = deepcopy(note)
        extra["note_id"] = "N0003"
        plan["reasoning_notes"].append(extra)
    elif mutation == "duplicate_premise":
        note["premises"].append(deepcopy(note["premises"][0]))
    elif mutation == "unknown_premise":
        note["premises"][0]["passage_id"] = "E.N0002"
    else:
        key = next(k for k, v in content["passage_catalog"].items() if v["authority"] == "rubric")
        note["premises"] = [span(key, content["passage_catalog"][key]["text"])]
    with pytest.raises(ValueError):
        inspect(evidence)


def split_first(evidence):
    plan = evidence[0]
    first = plan["checks"][0]
    second = deepcopy(first)
    first["question"] = "Synthetic first proposition?"
    second["question"] = "Synthetic second proposition sharing its subject?"
    plan["checks"].insert(1, second)
    for index, check in enumerate(plan["checks"], 1):
        check["check_id"] = f"K{index:04d}"


def test_overlapping_child_claims_preserve_parent_coverage(evidence):
    split_first(evidence)
    report = inspect(evidence)
    assert report["checks"] == report["parent_checks"] + 1
    assert report["semantic_audit"] == "required"


@pytest.mark.parametrize(
    "mutation", ["omission", "foreign_parent", "escape", "drop_dimension", "duplicate", "drop_kind"]
)
def test_child_split_cannot_hide_text_or_review(evidence, mutation):
    split_first(evidence)
    plan = evidence[0]
    child = plan["checks"][0]
    if mutation == "omission":
        for c in plan["checks"][:2]:
            c["subject"]["start"] += 1
            c["subject"]["quote"] = c["subject"]["quote"][1:]
    elif mutation == "foreign_parent":
        child["parent_check_id"] = "K9999"
    elif mutation == "escape":
        child["subject"] = deepcopy(plan["checks"][-1]["subject"])
    elif mutation == "drop_dimension":
        child["dimensions"] = []
    elif mutation == "drop_kind":
        child["kind"] = "context" if child["kind"] != "context" else "technical_claim"
    else:
        plan["checks"][1]["question"] = child["question"]
    with pytest.raises(ValueError):
        inspect(evidence)


def test_api_claim_in_context_still_requires_d3(evidence):
    check = next(c for c in evidence[0]["checks"] if c["subject"]["passage_id"] == "C.question")
    check["dimensions"].remove("D3")
    with pytest.raises(ValueError, match="dimension"):
        inspect(evidence)


def test_missing_primary_evidence_remains_unresolved(evidence):
    plan = EvidencePlan.model_validate(evidence[0])
    rows = response(evidence)
    check = next(c for c in plan.checks if c.evidence_kind == "api_contract")
    check.sources = []
    rows.plan_sha256 = digest(plan.model_dump(mode="json"))
    row = next(r for r in rows.observations if r.check_id == check.check_id)
    row.citations = []
    with pytest.raises(ValueError, match="requires exact"):
        inspect_evidence(plan, *evidence[1:], rows)
    row.status = "insufficient"
    report = inspect_evidence(plan, *evidence[1:], rows)
    assert report["unresolved"] == report["source_gaps"] == [check.check_id]


@pytest.mark.parametrize(
    "mutation",
    ["missing_child", "duplicate_child", "wrong_plan", "wrong_citation", "altered_quote"],
)
def test_observation_coverage_and_exact_citations(evidence, mutation):
    rows = response(evidence)
    if mutation == "missing_child":
        rows.observations.pop()
    elif mutation == "duplicate_child":
        rows.observations.append(deepcopy(rows.observations[0]))
    elif mutation == "wrong_plan":
        rows.plan_sha256 = "0" * 64
    elif mutation == "wrong_citation":
        rows.observations[0].citations[0].passage_id = "E.N0001"
    else:
        rows.observations[0].citations[0].quote += "invented"
    with pytest.raises(ValueError):
        inspect_evidence(EvidencePlan.model_validate(evidence[0]), *evidence[1:], rows)


@pytest.mark.parametrize(
    "missing", ["legacy", "evidence_kinds_reviewed", "authored_reasoning_checked"]
)
def test_v1_audit_or_missing_reasoning_review_cannot_unlock_scoring(evidence, missing):
    plan, content, rubric, root = evidence
    rows = response(evidence)
    audit = audit_for(plan, rows)
    if missing == "legacy":
        audit = FactAudit.model_validate(
            audit.model_dump(exclude={"evidence_kinds_reviewed", "authored_reasoning_checked"})
        )
    else:
        setattr(audit, missing, False)
    with pytest.raises(ValueError, match="v2 requires"):
        build_scoring_input(EvidencePlan.model_validate(plan), content, rubric, root, rows, audit)


def test_scoring_wire_view_keeps_reasoning_attribution_and_limits(evidence):
    plan, content, rubric, root = evidence
    rows = response(evidence)
    audit = audit_for(plan, rows)
    full = build_scoring_input(
        EvidencePlan.model_validate(plan), content, rubric, root, rows, audit
    )
    wire = scoring_request(full)
    assert wire["protocol"] == "recovery-scoring-v2"
    for original, sent in zip(plan["reasoning_notes"], wire["reasoning_notes"]):
        assert all(sent[k] == v for k, v in original.items())
        assert sent["version"] == digest(original)
    wire["reasoning_notes"][0]["reasoning"] = "Mutated wire copy"
    assert full["plan"]["reasoning_notes"][0]["reasoning"] != "Mutated wire copy"


def test_fact_request_is_exact_attributed_and_read_only(evidence):
    raw, content, rubric, root = evidence
    before = deepcopy(evidence[:3])
    request = evidence_request(EvidencePlan.model_validate(raw), content, rubric, root)
    assert request["plan_sha256"] == digest(raw)
    assert request["checks"] == raw["checks"]
    assert request["untrusted_item"] == content["untrusted_item"]
    assert request["reasoning_notes"][0]["origin"] == "assistant_authored"
    assert request["reasoning_notes"][0]["limitations"] == raw["reasoning_notes"][0]["limitations"]
    request["checks"][0]["question"] = "Changed wire copy"
    assert evidence[:3] == before


def test_v2_scores_still_need_both_audits_and_never_qualify(evidence, scoring):
    raw, content, rubric, root = evidence
    plan = EvidencePlan.model_validate(raw)
    observations = response(evidence)
    fact_audit = audit_for(raw, observations)
    payload = build_scoring_input(plan, content, rubric, root, observations, fact_audit)
    _, scores, score_audit = scoring
    scores.scoring_input_sha256 = digest(payload)
    for dimension, fields in payload["dimensions"].items():
        getattr(scores, dimension).effects = [
            Effect(check_id=k, effect="supports", explanation="Synthetic only.")
            for k in fields["required_checks"]
        ]
    args = (plan, content, rubric, root, observations, fact_audit, scores)
    assert inspect_scores(*args)["judgment"] is None
    score_audit.scores_sha256 = fingerprint(scores)
    result = inspect_scores(*args, score_audit)
    assert result["judgment"] is not None
    assert result["calibration_eligible"] is False and result["model_calls"] == 0
    fact_audit.authored_reasoning_checked = False
    with pytest.raises(ValueError, match="v2 requires"):
        inspect_scores(*args, score_audit)


def test_cli_is_read_only_and_redacts_invalid_input(evidence, tmp_path, capsys):
    plan, content, rubric, root = evidence
    args = ["--sources", str(root)]
    paths = []
    for name, value in [("plan", plan), ("input", content), ("rubric", rubric)]:
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        paths.append(path)
        args += [f"--{name}", str(path)]
    before = [p.read_bytes() for p in paths]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["calibration_eligible"] is False
    assert before == [p.read_bytes() for p in paths]
    paths[0].write_text('{"secret": "DO_NOT_ECHO"}')
    assert main(args) == 2
    assert "DO_NOT_ECHO" not in capsys.readouterr().out
    with pytest.raises(ValueError):
        parse_plan({**plan, "protocol": "recovery-evidence-v999"})
    with pytest.raises(ValueError):
        parse_plan([])
