"""Synthetic runtime checks: no live server, model requests or human ratings."""

from copy import deepcopy

import pytest

from aia_mp1 import assessed_native as native
from aia_mp1.canonical_development import QWEN_SETTINGS
from aia_mp1.confirmation_transport import RUNTIME
from aia_mp1.model_client import AttemptResult


@pytest.fixture
def pinned(monkeypatch):
    props = {
        "build_info": RUNTIME["build_info"],
        "model_path": "/synthetic/model.gguf",
        "total_slots": 1,
        "chat_template": "synthetic template",
        "default_generation_settings": {"n_ctx": RUNTIME["ctx_size"]},
    }
    state = {"props": deepcopy(props), "health": "ok", "closed": 0}

    class Server:
        def __init__(self, *args):
            pass

        def json(self, path):
            return state["props"] if path == "/props" else {"status": state["health"]}

        def close(self):
            state["closed"] += 1

    monkeypatch.setattr(native, "LocalServer", Server)
    plan = {
        "models": [{"model": props["model_path"]}],
        "settings": QWEN_SETTINGS,
        "cases": [
            {"item_id": "synthetic-1", "messages": [{"role": "user", "content": "Synthetic only"}]}
        ],
        "consecutive_failure_stop": 2,
    }
    return native.PinnedClient(plan, "http://127.0.0.1:8081/v1", {"properties": props}), state


@pytest.mark.parametrize("failure", ["health", "model_path", "chat_template", "context"])
def test_runtime_change_stops_before_dispatch(pinned, failure):
    client, state = pinned
    if failure == "health":
        state["health"] = "unavailable"
    elif failure == "context":
        state["props"]["default_generation_settings"]["n_ctx"] = 8192
    else:
        state["props"][failure] = "changed"
    with pytest.raises(KeyboardInterrupt):
        client.before_attempt({"item_id": "synthetic-1"}, 1)
    assert "pre-dispatch" in client.stop_reason
    assert state["closed"] == 1


def test_failure_boundary_never_contacts_server(pinned):
    client, state = pinned
    client.failures = 2
    with pytest.raises(KeyboardInterrupt):
        client.before_attempt({"item_id": "synthetic-1"}, 2)
    assert state["closed"] == 0


def test_message_mutation_rejected_before_transport(pinned):
    client, _ = pinned
    client.before_attempt({"item_id": "synthetic-1"}, 1)
    with pytest.raises(ValueError, match="differs from native preflight"):
        client.generate([{"role": "user", "content": "Changed input"}])


def test_model_mismatch_counts_as_failure_and_cannot_reset_stop(pinned, monkeypatch):
    client, _ = pinned
    result = AttemptResult(object(), {}, None, None, "wrong model")
    monkeypatch.setattr(native, "wire_for", lambda *args: {})

    class Transport:
        def __init__(self, wire):
            self.calls = 0

    class ModelClient:
        def __init__(self, *args):
            self.transport = args[-1]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def generate(self, messages):
            self.transport.calls += 1
            return result

    monkeypatch.setattr(native, "VerifiedTransport", Transport)
    monkeypatch.setattr(native, "client_for", ModelClient)
    for number in (1, 2):
        client.before_attempt({"item_id": "synthetic-1"}, number)
        assert client.generate(client.cases["synthetic-1"]["messages"]) is result
    assert client.failures == 2
    with pytest.raises(KeyboardInterrupt):
        client.before_attempt({"item_id": "synthetic-1"}, 3)
