"""Synthetic process captures; never contact or control a real machine."""

from copy import deepcopy

import pytest

from aia_mp1.recovery_process import CAPTURE, observe_process, preflight_owned


@pytest.fixture
def experiment():
    return {
        "owned_process": {
            "remote_root": "/synthetic/run",
            "executable": "/synthetic/llama-server",
            "port": 8082,
            "reasoning_budget": 4096,
        },
        "transport_policy": {"model": "/synthetic/model.gguf"},
        "server_properties": {
            "model_path": "/synthetic/model.gguf",
            "total_slots": 1,
            "default_generation_settings": {"n_ctx": 65536},
        },
    }


def capture():
    return [
        "Darwin arm64",
        "123",
        "120",
        "120",
        "/synthetic/llama-server --model /synthetic/model.gguf --host 127.0.0.1 "
        "--port 8082 --ctx-size 65536 --parallel 1 --reasoning on "
        "--reasoning-format deepseek --reasoning-budget 4096",
        "123",
        "Wed Nov 18 02:00:00 2026",
    ]


def test_frozen_command_parent_and_listener_are_checked(experiment):
    def read(script, root, port, timeout):
        assert script == CAPTURE and root == "/synthetic/run" and port == 8082 and timeout == 30
        return "\n".join(capture())

    result = observe_process(experiment, read)
    assert result["pid"] == result["listener_pid"] == 123
    assert result["parent_pid"] == 120


@pytest.mark.parametrize(
    "change", ["parent", "listener", "port", "context", "budget", "extra_listener"]
)
def test_stale_or_foreign_process_cannot_pass(experiment, change):
    lines = capture()
    if change == "parent":
        lines[3] = "121"
    elif change == "listener":
        lines[5] = "999"
    elif change == "extra_listener":
        lines[5] = "123\n999"
    else:
        original, replacement = {
            "port": ("8082", "8081"),
            "context": ("65536", "16384"),
            "budget": ("4096", "8192"),
        }[change]
        lines[4] = lines[4].replace(original, replacement)
    with pytest.raises(ValueError):
        observe_process(experiment, lambda *a, **kw: "\n".join(lines))


def test_invalid_path_does_not_reach_remote(experiment):
    experiment["owned_process"]["remote_root"] = "/synthetic/../other"
    with pytest.raises(ValueError):
        observe_process(experiment, lambda *a, **kw: pytest.fail("remote call"))


@pytest.mark.parametrize("restarted", [False, True])
def test_process_identity_is_bracketed_around_http_preflight(experiment, monkeypatch, restarted):
    class Journal:
        def read(self):
            return {"experiment": deepcopy(experiment)}, [], {}, "synthetic-head"

    calls = []

    def read(*args, **kwargs):
        lines = capture()
        if calls and restarted:
            lines[6] = "Wed Nov 18 02:01:00 2026"
        calls.append("process")
        return "\n".join(lines)

    def http(*args, **kwargs):
        calls.append("http")
        return {"journal_head_sha256": "synthetic-head", "execution_enabled": False}

    monkeypatch.setattr("aia_mp1.recovery_process.preflight_next", http)
    monkeypatch.setattr("aia_mp1.recovery_process.observe_files", lambda *a: [])
    if restarted:
        with pytest.raises(ValueError, match="changed across"):
            preflight_owned(Journal(), None, "synthetic-key", read)
    else:
        result = preflight_owned(Journal(), None, "synthetic-key", read)
        assert result["owned_process"]["pid"] == 123 and not result["execution_enabled"]
    assert calls == ["process", "http", "process"]
