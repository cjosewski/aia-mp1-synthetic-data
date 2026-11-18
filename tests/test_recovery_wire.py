"""Synthetic request text only; all model transport is intercepted offline."""

from copy import deepcopy

import pytest

from aia_mp1.recovery_wire import prepare_wire, verify_wire


@pytest.fixture
def request_data():
    return {
        "model": "synthetic-local-model",
        "temperature": 0.1,
        "max_tokens": 4096,
        "timeout_seconds": 300,
        "messages": [
            {"role": "system", "content": "Synthetic instructions."},
            {"role": "user", "content": '{"synthetic": true}'},
        ],
    }


@pytest.mark.parametrize("stage,marker", [("facts", "Observations"), ("score", "Scores")])
def test_actual_schema_wire_and_preservation(request_data, stage, marker):
    original = deepcopy(request_data)
    receipt = prepare_wire(request_data, stage)
    assert request_data == original
    wire = verify_wire(request_data, stage, receipt)
    assert marker in wire["messages"][0]["content"]
    assert wire["messages"][1] == original["messages"][1]
    assert wire["response_format"] == {"type": "json_object"}
    assert receipt["token_preflight"] == "not_measured"
    assert not receipt["execution_enabled"] and not receipt["calibration_eligible"]
    wire["model"] = "mutated"
    assert receipt["wire"]["model"] == original["model"]


@pytest.mark.parametrize(
    "field,value", [("model", "changed"), ("max_tokens", 2048), ("timeout_seconds", 90)]
)
def test_settings_drift_including_non_wire_timeout(request_data, field, value):
    receipt = prepare_wire(request_data, "facts")
    request_data[field] = value
    with pytest.raises(ValueError, match="differs"):
        verify_wire(request_data, "facts", receipt)


def test_schema_stage_or_wire_changes_fail(request_data):
    receipt = prepare_wire(request_data, "facts")
    with pytest.raises(ValueError, match="differs"):
        verify_wire(request_data, "score", receipt)
    receipt["wire"]["messages"][0]["content"] = "schema removed"
    with pytest.raises(ValueError, match="differs"):
        verify_wire(request_data, "facts", receipt)


def test_unknown_fields_and_legacy_stage_rejected(request_data):
    with pytest.raises(ValueError, match="unexpected"):
        prepare_wire(request_data, "control")
    request_data["reasoning_effort"] = "high"
    with pytest.raises(ValueError, match="unexpected"):
        prepare_wire(request_data, "facts")


@pytest.mark.parametrize(
    "messages",
    [[], [None, None], [{"role": "system", "content": ""}, {"role": "user", "content": "x"}]],
)
def test_invalid_message_shape_is_controlled(request_data, messages):
    request_data["messages"] = messages
    with pytest.raises(ValueError, match="explicit"):
        prepare_wire(request_data, "facts")
