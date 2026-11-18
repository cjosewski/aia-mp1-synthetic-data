"""Synthetic durable source-ID lineage; no authentic audit or human label."""

import pytest
from test_compact_evidence import envelope
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_evidence import evidence as evidence
from test_recovery_source_scoring import setup

from aia_mp1.recovery_audit_bridge import case_binding
from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.recovery_scoring import UncertaintyScoreAudit, fingerprint
from aia_mp1.recovery_source_audit import (
    accept_source_fact_audit,
    accept_source_score_audit,
    record_source_completion,
)
from aia_mp1.recovery_source_contract import source_contract_hash
from aia_mp1.recovery_source_scoring import SourceScores
from aia_mp1.tracing import digest


def started_facts(tmp_path, evidence, *, raw=None, stale=False):
    plan, content, rubric, root, obs, fact_audit, _, raw_scores = setup(evidence)
    binding = case_binding(plan, content, rubric)
    cases = [f"synthetic-{i}" for i in range(10)]
    ledger = RecoveryLedger.create(
        tmp_path / "journal",
        cases,
        {
            "source_protocol": "recovery-source-refs-v1",
            "source_contract_sha256": source_contract_hash(),
            "uncertainty_policy": "audited-materiality-v1",
            "prepared_insufficient": [],
            "case_bindings": {cases[0]: binding},
        },
    )
    payload = {
        "case_binding": {**binding, "input_sha256": "0" * 64} if stale else binding,
        "request": {"synthetic": True},
    }
    start = {
        "kind": "start",
        "item_id": cases[0],
        "stage": "facts",
        "request_sha256": digest(payload),
    }
    ledger.append(start, payload)
    result = record_source_completion(
        ledger, digest(start), raw if raw is not None else envelope(obs.model_dump(mode="json"))
    )
    return ledger, (plan, content, rubric, root, obs, fact_audit, raw_scores), result


def score_audit(scores):
    return UncertaintyScoreAudit.model_validate(
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


def test_saved_source_facts_and_scores_require_two_audits(tmp_path, evidence):
    ledger, (plan, content, rubric, root, _, fact_audit, raw_scores), result = started_facts(
        tmp_path, evidence
    )
    assert result["schema_error_type"] is None
    accepted = accept_source_fact_audit(ledger, plan, content, rubric, root, fact_audit)
    assert accepted["state"]["next_request"]["stage"] == "score"
    scores = SourceScores.model_validate(raw_scores)
    payload = {
        "case_binding": case_binding(plan, content, rubric),
        "scoring_input_sha256": digest(accepted["scoring_input"]),
        "request": {"synthetic": True},
    }
    start = {
        "kind": "start",
        "item_id": "synthetic-0",
        "stage": "score",
        "request_sha256": digest(payload),
    }
    ledger.append(start, payload)
    record_source_completion(ledger, digest(start), envelope(scores.model_dump(mode="json")))
    scored = accept_source_score_audit(ledger, plan, content, rubric, root, score_audit(scores))
    assert scored["state"]["next_request"] == {"item_id": "synthetic-1", "stage": "facts"}
    assert scored["report"]["status"] == "audited_development"
    assert scored["report"]["calibration_eligible"] is False


@pytest.mark.parametrize("attack", ["start", "fact_audit", "raw", "protocol"])
def test_bad_source_fact_lineage_never_appends_acceptance(tmp_path, evidence, attack):
    raw = envelope({"wrong": "schema"}) if attack == "raw" else None
    ledger, (plan, content, rubric, root, _, fact_audit, _), _ = started_facts(
        tmp_path, evidence, raw=raw, stale=attack == "start"
    )
    if attack == "fact_audit":
        fact_audit.checks[0].accepted = False
    if attack == "protocol":
        ledger_manifest = ledger.directory / "manifest.json"
        # A forged manifest must fail the ledger's own hash/checkpoint validation.
        text = ledger_manifest.read_text().replace("recovery-source-refs-v1", "wrong-protocol")
        ledger_manifest.write_text(text)
    before = (ledger.directory / "events.jsonl").read_bytes()
    with pytest.raises(ValueError):
        accept_source_fact_audit(ledger, plan, content, rubric, root, fact_audit)
    assert (ledger.directory / "events.jsonl").read_bytes() == before


def test_invalid_source_completion_is_retained_not_retried(tmp_path, evidence):
    ledger, _, result = started_facts(tmp_path, evidence, raw=envelope({"wrong": "schema"}))
    assert result["schema_error_type"]
    assert result["state"]["cases"]["synthetic-0"]["facts"] == "failed"
    assert result["state"]["cases"]["synthetic-0"]["score"] == "skipped"
    assert result["state"]["starts"] == 1
