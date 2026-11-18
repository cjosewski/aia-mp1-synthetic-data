"""Synthetic wire receipts; local mock intercepts every attempted request."""

from copy import deepcopy

import pytest

from aia_mp1.recovery_source_wire import prepare_source_wire, verify_source_wire


@pytest.fixture
def wire_request():
    return {
        "model": "synthetic-local-model",
        "temperature": 0.1,
        "max_tokens": 512,
        "timeout_seconds": 10,
        "messages": [
            {"role": "system", "content": "Synthetic test system prompt."},
            {"role": "user", "content": '{"synthetic":true}'},
        ],
    }


def test_distinct_stage_schemas_and_exact_wire_receipts(wire_request):
    original = deepcopy(wire_request)
    facts = prepare_source_wire(wire_request, "facts")
    score = prepare_source_wire(wire_request, "score")
    assert wire_request == original
    assert facts["protocol"] == score["protocol"] == "recovery-source-wire-v1"
    assert facts["schema_sha256"] != score["schema_sha256"]
    assert facts["wire_sha256"] != score["wire_sha256"]
    assert verify_source_wire(wire_request, "facts", facts) == facts["wire"]
    assert facts["execution_enabled"] is score["calibration_eligible"] is False


@pytest.mark.parametrize("change", ["message", "timeout", "schema", "wire"])
def test_stale_or_tampered_receipt_fails(wire_request, change):
    receipt = prepare_source_wire(wire_request, "facts")
    if change == "message":
        wire_request["messages"][1]["content"] = '{"synthetic":false}'
    elif change == "timeout":
        wire_request["timeout_seconds"] = 11
    elif change == "schema":
        receipt["schema_sha256"] = "0" * 64
    else:
        receipt["wire"]["temperature"] = 0.2
    with pytest.raises(ValueError):
        verify_source_wire(wire_request, "facts", receipt)


@pytest.mark.parametrize("change", ["role", "blank", "extra", "stage"])
def test_invalid_request_never_gets_a_receipt(wire_request, change):
    if change == "role":
        wire_request["messages"][0]["role"] = "assistant"
    elif change == "blank":
        wire_request["messages"][1]["content"] = " "
    elif change == "extra":
        wire_request["unknown"] = 1
    else:
        with pytest.raises(ValueError):
            prepare_source_wire(wire_request, "unknown")
        return
    with pytest.raises(ValueError):
        prepare_source_wire(wire_request, "facts")
