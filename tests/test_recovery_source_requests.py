"""Synthetic source-ID request gates; no live endpoint or authentic ratings."""

import json

import pytest
from test_compact_evidence import envelope
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_evidence import audit_for
from test_recovery_evidence import evidence as evidence
from test_recovery_packet import prepared as prepared
from test_recovery_source_refs import response_for

from aia_mp1.recovery_evidence import parse_plan
from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.recovery_packet import require_ready
from aia_mp1.recovery_source_audit import accept_source_fact_audit, record_source_completion
from aia_mp1.recovery_source_contract import source_contract_hash
from aia_mp1.recovery_source_refs import SourceObservations, source_request
from aia_mp1.recovery_source_requests import prepare_source_next
from aia_mp1.tracing import digest


@pytest.fixture
def source_packet(prepared):
    selection_path = prepared / "selection.json"
    selection = json.loads(selection_path.read_text())
    selection["protocol"] = "recovery-preparation-v2"
    selection_path.write_text(json.dumps(selection))
    for i in range(10):
        path = prepared / f"synthetic-{i}/preparation-review.json"
        review = json.loads(path.read_text())
        review["insufficient_claims"] = []
        path.write_text(json.dumps(review))
    return prepared


def journal(tmp_path, source_packet):
    packet = require_ready(source_packet)
    return RecoveryLedger.create(
        tmp_path / "journal",
        list(packet["case_bindings"]),
        {
            "packet_sha256": packet["packet_sha256"],
            "case_bindings": packet["case_bindings"],
            "prepared_insufficient": packet["insufficient_claims"],
            "source_protocol": "recovery-source-refs-v1",
            "source_contract_sha256": source_contract_hash(),
            "uncertainty_policy": "audited-materiality-v1",
            "prompts": {"facts": "Synthetic source fact prompt", "score": "Synthetic score prompt"},
            "transport_policy": {
                "model": "synthetic-local-model",
                "temperature": 0.1,
                "max_tokens": 512,
                "timeout_seconds": 10,
                "endpoint": "http://127.0.0.1:8082/v1",
            },
        },
    )


def test_facts_request_replays_frozen_source_packet(source_packet, tmp_path):
    ledger = journal(tmp_path, source_packet)
    prepared_next = prepare_source_next(ledger, source_packet)
    case = source_packet / "synthetic-0"
    plan = parse_plan(json.loads((case / "plan.json").read_text()))
    content = json.loads((case / "input.json").read_text())
    rubric = json.loads((source_packet / "rubric.json").read_text())
    expected = source_request(plan, content, rubric, source_packet / "sources")
    expected["prepared_insufficient"] = []
    assert json.loads(prepared_next["request"]["messages"][1]["content"]) == expected
    assert prepared_next["receipt"]["protocol"] == "recovery-source-wire-v1"
    assert ledger.read()[2]["starts"] == 0


def test_score_request_requires_saved_source_fact_audit(source_packet, evidence, tmp_path):
    ledger = journal(tmp_path, source_packet)
    first = prepare_source_next(ledger, source_packet)
    payload = {"case_binding": first["binding"], "request": first["request"]}
    start = {
        "kind": "start",
        "item_id": first["item_id"],
        "stage": "facts",
        "request_sha256": digest(payload),
    }
    ledger.append(start, payload)
    with pytest.raises(ValueError, match="no unused"):
        prepare_source_next(ledger, source_packet)
    plan_raw, content, rubric, _ = evidence
    observations = SourceObservations.model_validate(response_for(plan_raw))
    record_source_completion(ledger, digest(start), envelope(observations.model_dump(mode="json")))
    with pytest.raises(ValueError, match="no unused"):
        prepare_source_next(ledger, source_packet)
    audit = audit_for(plan_raw, observations)
    audit.checks[0].explanation = "AUDIT_COMMENT_NOT_FOR_MODEL"
    accepted = accept_source_fact_audit(
        ledger, parse_plan(plan_raw), content, rubric, source_packet / "sources", audit
    )
    next_request = prepare_source_next(ledger, source_packet)
    text = next_request["request"]["messages"][1]["content"]
    assert next_request["stage"] == "score"
    assert json.loads(text)["scoring_input_sha256"] == digest(accepted["scoring_input"])
    assert "AUDIT_COMMENT_NOT_FOR_MODEL" not in text
    assert ledger.read()[2]["starts"] == 1


def test_packet_change_blocks_source_request_before_start(source_packet, tmp_path):
    ledger = journal(tmp_path, source_packet)
    path = source_packet / "synthetic-0/preparation-review.json"
    review = json.loads(path.read_text())
    review["entries"][0]["reason"] = "Changed synthetic review"
    path.write_text(json.dumps(review))
    with pytest.raises(ValueError, match="frozen"):
        prepare_source_next(ledger, source_packet)
    assert ledger.read()[2]["starts"] == 0
