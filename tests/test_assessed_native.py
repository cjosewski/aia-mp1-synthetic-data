"""Synthetic runtime checks: no live server, model requests or human ratings."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from assessed_fixtures import fixture_config, qualified_judge

from aia_mp1 import assessed_native as native
from aia_mp1.canonical_development import QWEN_SETTINGS
from aia_mp1.confirmation_transport import RUNTIME
from aia_mp1.model_client import AttemptResult
from aia_mp1.qualification import validate_qualification


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
        "runtime": RUNTIME.copy(),
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


def test_budget_requires_process_guard_and_stops_before_dispatch(pinned):
    old, state = pinned
    plan = old.plan | {"runtime": RUNTIME | {"reasoning_budget": 4096}}
    with pytest.raises(ValueError, match="owned-process"):
        native.PinnedClient(plan, old.endpoint, old.runtime)

    def changed_process():
        raise ValueError("Synthetic replacement server")

    client = native.PinnedClient(plan, old.endpoint, old.runtime, verify_process=changed_process)
    with pytest.raises(KeyboardInterrupt):
        client.before_attempt({"item_id": "synthetic-1"}, 1)
    assert client.stop_reason.startswith("pre-dispatch")
    assert state["closed"] == 1


def test_budget_configuration_requires_matching_selection_receipt(tmp_path):
    generator = fixture_config(tmp_path)
    old = qualified_judge(tmp_path, generator)
    assert native.NativeJudgeConfig(**old.model_dump()).public_settings() == old.public_settings()
    config = native.NativeJudgeConfig(**old.model_dump(), server_reasoning_budget=4096)
    assessment = {
        "generator_model_identity": generator.model_identity,
        "generator_model_sha256": generator.model_sha256,
    }
    with pytest.raises(ValueError, match="model/settings"):
        validate_qualification(config, assessment)
    path = Path(config.qualification_path)
    receipt = json.loads(path.read_text())
    receipt["settings"]["server_reasoning_budget"] = 4096
    path.write_text(json.dumps(receipt))
    assert validate_qualification(config, assessment)["receipt"] == receipt


@pytest.mark.parametrize("change", ["budget", "parent", "none"])
def test_owned_runtime_matches_exact_budget_and_parent(tmp_path, monkeypatch, change):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "owned-server.pid").write_text("123")
    (runtime / "launcher.pid").write_text("100")
    command = (
        "/opt/homebrew/bin/llama-server --model /synthetic/model.gguf --host 127.0.0.1 "
        "--port 8081 --ctx-size 16384 --parallel 1 --reasoning on "
        "--reasoning-format deepseek --reasoning-budget " + ("-1" if change == "budget" else "4096")
    )

    def output(args, **kwargs):
        return command if "command=" in args else ("99" if change == "parent" else "100")

    monkeypatch.setattr(native.subprocess, "check_output", output)
    if change == "none":
        assert (
            native.verify_owned_runtime(tmp_path, "/synthetic/model.gguf", 4096)["argv"][-1]
            == "4096"
        )
    else:
        with pytest.raises(ValueError, match="thinking budget differs"):
            native.verify_owned_runtime(tmp_path, "/synthetic/model.gguf", 4096)
