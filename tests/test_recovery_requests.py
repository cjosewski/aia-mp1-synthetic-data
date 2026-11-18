"""Synthetic frozen packet/request integration; no live dispatch or real audits."""

import json

import pytest
from test_compact_evidence import envelope
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_evidence import audit_for, response
from test_recovery_evidence import evidence as evidence
from test_recovery_packet import prepared as prepared
from test_recovery_wire import request_data as request_data

from aia_mp1.recovery_audit_bridge import accept_fact_audit, record_completion
from aia_mp1.recovery_evidence import evidence_request, parse_plan
from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.recovery_packet import require_ready
from aia_mp1.recovery_requests import prepare_next
from aia_mp1.tracing import digest


def journal(tmp_path, prepared, request_data):
    packet = require_ready(prepared)
    policy = {k: request_data[k] for k in ("model", "temperature", "max_tokens", "timeout_seconds")}
    return RecoveryLedger.create(
        tmp_path / "journal",
        list(packet["case_bindings"]),
        {
            "packet_sha256": packet["packet_sha256"],
            "case_bindings": packet["case_bindings"],
            "prompts": {"facts": "Synthetic fact prompt", "score": "Synthetic score prompt"},
            "transport_policy": {**policy, "endpoint": "http://127.0.0.1:8082/v1"},
        },
    )


def test_facts_are_built_from_complete_frozen_packet(prepared, evidence, tmp_path, request_data):
    ledger = journal(tmp_path, prepared, request_data)
    result = prepare_next(ledger, prepared)
    plan, content, rubric, _ = evidence
    expected = evidence_request(parse_plan(plan), content, rubric, prepared / "sources")
    assert json.loads(result["request"]["messages"][1]["content"]) == expected
    assert result["request"]["messages"][0]["content"] == "Synthetic fact prompt"
    assert result["stage"] == "facts" and result["item_id"] == "synthetic-0"
    assert not result["execution_enabled"] and ledger.read()[2]["starts"] == 0


def test_score_request_reconstructs_accepted_facts(prepared, evidence, tmp_path, request_data):
    ledger = journal(tmp_path, prepared, request_data)
    first = prepare_next(ledger, prepared)
    payload = {"case_binding": first["binding"], "request": first["request"]}
    start = {
        "kind": "start",
        "item_id": first["item_id"],
        "stage": "facts",
        "request_sha256": digest(payload),
    }
    ledger.append(start, payload)
    with pytest.raises(ValueError, match="no unused"):
        prepare_next(ledger, prepared)
    observations = response(evidence)
    record_completion(ledger, digest(start), envelope(observations.model_dump(mode="json")))
    with pytest.raises(ValueError, match="no unused"):
        prepare_next(ledger, prepared)
    plan, content, rubric, _ = evidence
    audit = audit_for(plan, observations)
    audit.checks[0].explanation = "AUDIT_COMMENT_NOT_FOR_MODEL"
    accepted = accept_fact_audit(
        ledger, parse_plan(plan), content, rubric, prepared / "sources", audit
    )
    next_request = prepare_next(ledger, prepared)
    text = next_request["request"]["messages"][1]["content"]
    assert next_request["stage"] == "score"
    assert json.loads(text)["scoring_input_sha256"] == digest(accepted["scoring_input"])
    assert "AUDIT_COMMENT_NOT_FOR_MODEL" not in text
    assert ledger.read()[2]["starts"] == 1


def test_changed_preparation_blocks_request_without_start(prepared, tmp_path, request_data):
    ledger = journal(tmp_path, prepared, request_data)
    path = prepared / "synthetic-0/preparation-review.json"
    review = json.loads(path.read_text())
    review["entries"][0]["reason"] = "Changed synthetic review"
    path.write_text(json.dumps(review))
    with pytest.raises(ValueError, match="frozen"):
        prepare_next(ledger, prepared)
    assert ledger.read()[2]["starts"] == 0
