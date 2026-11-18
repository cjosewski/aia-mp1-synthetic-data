"""Synthetic Windows observations; no SSH tunnel or model service is started."""

from copy import deepcopy

import pytest

from aia_mp1.recovery_tunnel import observe_tunnel, preflight_with_tunnel, read_windows_tunnel


@pytest.fixture
def experiment():
    return {
        "transport_policy": {"endpoint": "http://127.0.0.1:18082/v1"},
        "owned_process": {"port": 8082},
        "owned_tunnel": {
            "ssh_executable": "C:/Windows/ssh.exe",
            "pid": 123,
            "ssh_host_alias": "mac.local",
            "ssh_destination": "user@mac",
            "local_port": 18082,
            "remote_port": 8082,
        },
    }


@pytest.fixture
def observation():
    return {
        "pid": 123,
        "listener_pid": 123,
        "executable": "C:/Windows/ssh.exe",
        "argv": [
            "ssh.exe",
            "-o",
            "BatchMode=yes",
            "-o",
            "HostKeyAlias=mac.local",
            "-L",
            "127.0.0.1:18082:127.0.0.1:8082",
            "user@mac",
        ],
        "started": "synthetic time",
    }


def test_exact_forward_and_owner(experiment, observation):
    assert observe_tunnel(experiment, lambda expected: observation)["pid"] == 123


@pytest.mark.parametrize("change", ["listener", "forward", "host", "destination", "extra_forward"])
def test_different_tunnel_cannot_pass(experiment, observation, change):
    observed = deepcopy(observation)
    if change == "listener":
        observed["listener_pid"] = 999
    elif change == "forward":
        observed["argv"][6] = "127.0.0.1:18082:127.0.0.1:8081"
    elif change == "host":
        observed["argv"][4] = "HostKeyAlias=other"
    elif change == "destination":
        observed["argv"][-1] = "user@other"
    else:
        observed["argv"].extend(["-L", "127.0.0.1:18083:127.0.0.1:8083"])
    with pytest.raises(ValueError):
        observe_tunnel(experiment, lambda expected: observed)


def test_tunnel_restart_during_preflight_stops(monkeypatch, experiment, observation):
    class Journal:
        def read(self):
            return {"experiment": experiment}, [], {}, "head"

    calls = []

    def read(expected):
        calls.append("tunnel")
        value = deepcopy(observation)
        if len(calls) > 2:
            value["pid"] = value["listener_pid"] = 124
        return value

    def mac(*a, **kw):
        calls.append("mac")
        return {"journal_head_sha256": "head", "execution_enabled": False}

    monkeypatch.setattr("aia_mp1.recovery_tunnel.preflight_owned", mac)
    with pytest.raises(ValueError, match="SSH tunnel owner"):
        preflight_with_tunnel(Journal(), None, "key", None, read)
    assert calls == ["tunnel", "mac", "tunnel"]


def test_windows_reader_uses_bounded_native_queries(monkeypatch, experiment, observation):
    import subprocess

    calls = []
    monkeypatch.setattr("aia_mp1.recovery_tunnel.platform.system", lambda: "Linux")
    monkeypatch.setattr("aia_mp1.recovery_tunnel.platform.release", lambda: "WSL2-microsoft")

    def run(args, **kwargs):
        calls.append((args, kwargs))
        if args[0] == "wslpath":
            return subprocess.CompletedProcess(args, 0, "C:\\synthetic\\reader.ps1\n", "")
        return subprocess.CompletedProcess(args, 0, __import__("json").dumps(observation), "")

    monkeypatch.setattr("aia_mp1.recovery_tunnel.subprocess.run", run)
    assert read_windows_tunnel(experiment["owned_tunnel"]) == observation
    assert calls[1][0][-4:] == ["-ProcessId", "123", "-LocalPort", "18082"]
    assert all(call[1]["check"] and call[1]["timeout"] <= 20 for call in calls)
