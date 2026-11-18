"""Synthetic source-ID transport; all network calls are intercepted."""

import json

import httpx
import pytest
from test_compact_evidence import envelope

from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.recovery_source_contract import source_contract_hash
from aia_mp1.recovery_source_transport import dispatch_source_next
from aia_mp1.recovery_source_wire import prepare_source_wire
from aia_mp1.tracing import digest


def setup(tmp_path):
    binding = {"plan_sha256": "a" * 64, "input_sha256": "b" * 64, "rubric_sha256": "c" * 64}
    endpoint = "http://127.0.0.1:8082/v1"
    request = {
        "model": "synthetic-local-model",
        "temperature": 0.1,
        "max_tokens": 512,
        "timeout_seconds": 10,
        "messages": [
            {"role": "system", "content": "Synthetic source-ID fact prompt"},
            {"role": "user", "content": '{"synthetic":true}'},
        ],
    }
    policy = {
        key: request[key] for key in ("model", "temperature", "max_tokens", "timeout_seconds")
    }
    ledger = RecoveryLedger.create(
        tmp_path / "journal",
        [f"synthetic-{i}" for i in range(10)],
        {
            "source_protocol": "recovery-source-refs-v1",
            "source_contract_sha256": source_contract_hash(),
            "uncertainty_policy": "audited-materiality-v1",
            "transport_policy": {**policy, "endpoint": endpoint},
            "case_bindings": {"synthetic-0": binding},
        },
    )
    args = [
        ledger,
        "synthetic-0",
        "facts",
        request,
        prepare_source_wire(request, "facts"),
        binding,
        endpoint,
        "synthetic-private-credential-123",
    ]
    return ledger, args


@pytest.mark.parametrize("outcome", ["valid", "malformed", "http_error", "timeout"])
def test_one_source_start_retains_outcome_without_retry(tmp_path, outcome):
    ledger, args = setup(tmp_path)
    calls = []
    raw = envelope(
        {"protocol": "recovery-source-refs-v1", "plan_sha256": "a" * 64, "observations": []}
    )
    raw["model"] = args[3]["model"]

    def send(request):
        assert ledger.read()[2]["starts"] == 1 and ledger.read()[2]["unknown_outcome"]
        assert json.loads(request.content) == args[4]["wire"]
        calls.append(request)
        if outcome == "timeout":
            raise httpx.ReadTimeout("synthetic-private-credential-123")
        if outcome == "malformed":
            return httpx.Response(200, text="synthetic-private-credential-123 malformed")
        if outcome == "http_error":
            return httpx.Response(503, json={"error": "synthetic unavailable"})
        return httpx.Response(200, json=raw)

    result = dispatch_source_next(*args, transport=httpx.MockTransport(send))
    assert len(calls) == 1
    assert args[-1] not in (ledger.directory / "events.jsonl").read_text()
    assert result["state"]["starts"] == 1 and not result["calibration_eligible"]
    if outcome == "valid":
        assert result["state"]["awaiting_audit"]
    elif outcome == "timeout":
        assert result["state"]["halt"] == "transport_outcome_unknown"
    else:
        assert result["state"]["cases"]["synthetic-0"]["facts"] == "failed"
    with pytest.raises(ValueError):
        dispatch_source_next(*args, transport=httpx.MockTransport(send))
    assert len(calls) == 1


@pytest.mark.parametrize("attack", ["endpoint", "wire", "binding"])
def test_stale_source_preparation_never_starts(tmp_path, attack):
    ledger, args = setup(tmp_path)
    if attack == "endpoint":
        args[6] = "http://127.0.0.1:8083/v1"
    elif attack == "wire":
        args[4]["wire"]["model"] = "changed"
    else:
        args[5] = {"wrong": True}
    with pytest.raises(ValueError):
        dispatch_source_next(
            *args, transport=httpx.MockTransport(lambda request: pytest.fail("network call"))
        )
    assert ledger.read()[2]["starts"] == 0


def test_source_response_model_identity_failure_halts(tmp_path):
    ledger, args = setup(tmp_path)
    raw = envelope(
        {"protocol": "recovery-source-refs-v1", "plan_sha256": "a" * 64, "observations": []}
    )
    raw["model"] = "wrong-model"
    result = dispatch_source_next(
        *args, transport=httpx.MockTransport(lambda _: httpx.Response(200, json=raw))
    )
    assert result["state"]["halt"] == "response_model_identity_failed"


def test_score_stage_binds_accepted_fact_fingerprint(tmp_path):
    ledger, args = setup(tmp_path)
    payload = {"synthetic": True}
    start = {
        "kind": "start",
        "item_id": "synthetic-0",
        "stage": "facts",
        "request_sha256": digest(payload),
    }
    finish = {
        "kind": "finish",
        "start_sha256": digest(start),
        "completion_sha256": digest(payload),
        "structurally_valid": True,
    }
    audit = {
        "kind": "audit",
        "finish_sha256": digest(finish),
        "audit_sha256": digest(payload),
        "accepted": True,
    }
    for event in (start, finish, audit):
        ledger.append(event, payload)
    args[2] = "score"
    args[3]["messages"][1]["content"] = json.dumps({"scoring_input_sha256": "d" * 64})
    args[4] = prepare_source_wire(args[3], "score")
    raw = envelope(
        {"protocol": "recovery-source-refs-v1", "plan_sha256": "a" * 64, "observations": []}
    )
    raw["model"] = args[3]["model"]
    result = dispatch_source_next(
        *args, transport=httpx.MockTransport(lambda _: httpx.Response(200, json=raw))
    )
    assert result["state"]["cases"]["synthetic-0"]["score"] == "failed"
    rows = [
        json.loads(line) for line in (ledger.directory / "events.jsonl").read_text().splitlines()
    ]
    assert rows[-2]["payload"]["scoring_input_sha256"] == "d" * 64
