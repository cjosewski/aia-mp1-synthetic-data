"""Synthetic transport only; no local service or real review is used."""

import json

import httpx
import pytest
from test_compact_evidence import envelope
from test_recovery_wire import request_data as request_data

from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.recovery_transport import dispatch_next
from aia_mp1.recovery_wire import prepare_wire
from aia_mp1.tracing import digest


def setup(tmp_path, request_data):
    binding = {"plan_sha256": "a" * 64, "input_sha256": "b" * 64, "rubric_sha256": "c" * 64}
    endpoint = "http://127.0.0.1:8082/v1"
    policy = {k: request_data[k] for k in ("model", "temperature", "max_tokens", "timeout_seconds")}
    ledger = RecoveryLedger.create(
        tmp_path / "journal",
        [f"synthetic-{i}" for i in range(10)],
        {
            "transport_policy": {**policy, "endpoint": endpoint},
            "case_bindings": {"synthetic-0": binding},
        },
    )
    args = [
        ledger,
        "synthetic-0",
        "facts",
        request_data,
        prepare_wire(request_data, "facts"),
        binding,
        endpoint,
        "synthetic-private-credential-123",
    ]
    return ledger, args


@pytest.mark.parametrize("outcome", ["valid", "malformed", "http_error", "timeout"])
def test_one_started_request_retains_outcome_without_retry(tmp_path, request_data, outcome):
    ledger, args = setup(tmp_path, request_data)
    calls = []
    raw = envelope({"plan_sha256": "a" * 64, "observations": []})

    def send(request):
        state = ledger.read()[2]
        assert state["starts"] == 1 and state["unknown_outcome"]
        assert json.loads(request.content) == args[4]["wire"]
        calls.append(request)
        if outcome == "timeout":
            raise httpx.ReadTimeout("synthetic-private-credential-123")
        if outcome == "malformed":
            return httpx.Response(200, text="synthetic-private-credential-123 malformed")
        if outcome == "http_error":
            return httpx.Response(503, json={"error": "synthetic unavailable"})
        return httpx.Response(200, json=raw)

    result = dispatch_next(*args, transport=httpx.MockTransport(send))
    assert len(calls) == 1
    text = (ledger.directory / "events.jsonl").read_text()
    assert args[-1] not in text
    assert result["state"]["starts"] == 1
    assert not result["calibration_eligible"]
    if outcome == "valid":
        assert result["state"]["awaiting_audit"]
        assert json.loads(text.splitlines()[-1])["payload"] == raw
    elif outcome == "timeout":
        assert result["state"]["halt"] == "transport_outcome_unknown"
    else:
        assert result["state"]["cases"]["synthetic-0"]["facts"] == "failed"
    with pytest.raises(ValueError):
        dispatch_next(*args, transport=httpx.MockTransport(send))
    assert len(calls) == 1


@pytest.mark.parametrize("changed", ["endpoint", "wire", "binding"])
def test_changed_preparation_never_starts(tmp_path, request_data, changed):
    ledger, args = setup(tmp_path, request_data)
    if changed == "endpoint":
        args[6] = "http://127.0.0.1:8083/v1"
    elif changed == "wire":
        args[4]["wire"]["model"] = "changed"
    else:
        args[5] = {"wrong": True}
    with pytest.raises(ValueError):
        dispatch_next(
            *args, transport=httpx.MockTransport(lambda request: pytest.fail("network call"))
        )
    assert ledger.read()[2]["starts"] == 0


def test_failed_start_checkpoint_never_reaches_network(tmp_path, request_data, monkeypatch):
    ledger, args = setup(tmp_path, request_data)

    def fail(*args):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr("aia_mp1.recovery_ledger.write_checkpoint", fail)
    with pytest.raises(ValueError):
        dispatch_next(
            *args, transport=httpx.MockTransport(lambda request: pytest.fail("network call"))
        )
    with pytest.raises(ValueError, match="event/head"):
        ledger.read()


def test_score_stage_uses_score_schema_and_retains_input_binding(tmp_path, request_data):
    ledger, args = setup(tmp_path, request_data)
    # Synthetic low-level schedule scaffolding, not a real accepting fact audit.
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
    args[4] = prepare_wire(args[3], "score")

    def send(request):
        assert ledger.read()[2]["starts"] == 2
        assert "Scores" in json.loads(request.content)["messages"][0]["content"]
        # Valid observation schema must not pass as a score response.
        return httpx.Response(200, json=envelope({"plan_sha256": "a" * 64, "observations": []}))

    result = dispatch_next(*args, transport=httpx.MockTransport(send))
    assert result["state"]["cases"]["synthetic-0"]["score"] == "failed"
    rows = [
        json.loads(line) for line in (ledger.directory / "events.jsonl").read_text().splitlines()
    ]
    assert rows[-2]["payload"]["scoring_input_sha256"] == "d" * 64
