"""Read-only native Mac process checks around recovery HTTP preflight."""

import shlex
from pathlib import PurePosixPath

from .recovery_preflight import preflight_next

CAPTURE = """set -eu
root="$1"
port="$2"
uname -sm
pid=$(cat "$root/runtime/owned-server.pid")
parent=$(cat "$root/runtime/launcher.pid")
case "$pid:$parent" in *[!0-9:]*|:*) exit 2;; esac
kill -0 "$parent"
printf '%s\\n' "$pid" "$parent"
/bin/ps -o ppid= -p "$pid"
/bin/ps -ww -o command= -p "$pid"
/usr/sbin/lsof -nP -t -iTCP:"$port" -sTCP:LISTEN
/bin/ps -o lstart= -p "$pid"
"""


def observe_process(experiment, read_remote):
    """Use a trusted SSH reader; PID files alone never establish ownership."""
    process = experiment.get("owned_process")
    if not isinstance(process, dict) or set(process) != {
        "remote_root",
        "executable",
        "port",
        "reasoning_budget",
    }:
        raise ValueError("frozen owned-process configuration is required")
    for name in ("remote_root", "executable"):
        value = process[name]
        if (
            not isinstance(value, str)
            or not value.startswith("/")
            or ".." in PurePosixPath(value).parts
        ):
            raise ValueError("remote paths must be absolute without parent traversal")
    if type(process["port"]) is not int or not 1 <= process["port"] <= 65535:
        raise ValueError("invalid frozen remote port")
    if type(process["reasoning_budget"]) is not int or process["reasoning_budget"] <= 0:
        raise ValueError("positive frozen reasoning budget is required")
    props = experiment["server_properties"]
    model = experiment["transport_policy"]["model"]
    if props["model_path"] != model:
        raise ValueError("process model differs from frozen server")
    context = props["default_generation_settings"]["n_ctx"]
    if type(context) is not int or context <= 0 or props["total_slots"] != 1:
        raise ValueError("positive context and one slot are required")
    # macOS ps does not quote argv. Fail closed for paths whose argument
    # boundaries cannot be reconstructed, instead of guessing ownership.
    if any(c.isspace() for value in (model, process["executable"]) for c in value):
        raise ValueError("process observation does not support whitespace in argv paths")
    expected = [
        process["executable"],
        "--model",
        model,
        "--host",
        "127.0.0.1",
        "--port",
        str(process["port"]),
        "--ctx-size",
        str(context),
        "--parallel",
        "1",
        "--reasoning",
        "on",
        "--reasoning-format",
        "deepseek",
        "--reasoning-budget",
        str(process["reasoning_budget"]),
    ]
    lines = (
        read_remote(CAPTURE, process["remote_root"], process["port"], timeout=30)
        .strip()
        .splitlines()
    )
    if len(lines) != 7 or lines[0] != "Darwin arm64":
        raise ValueError("native Mac process observation malformed")
    pid, parent, actual_parent = (int(line.strip()) for line in lines[1:4])
    listener = int(lines[5].strip())
    if (
        pid <= 1
        or parent <= 1
        or pid == parent
        or actual_parent != parent
        or listener != pid
        or shlex.split(lines[4]) != expected
        or not lines[6].strip()
    ):
        raise ValueError("owned process, listener or frozen arguments differ")
    return {
        "pid": pid,
        "parent_pid": parent,
        "listener_pid": listener,
        "started": lines[6].strip(),
        "argv": expected,
        "host": lines[0],
    }


def preflight_owned(ledger, packet_root, key, read_remote, *, transport=None):
    """Check the same live process on both sides; weight checks are still separate."""
    manifest, _, _, head = ledger.read()
    before = observe_process(manifest["experiment"], read_remote)
    result = preflight_next(ledger, packet_root, key, transport=transport)
    after = observe_process(manifest["experiment"], read_remote)
    if before != after or ledger.read()[3] != head or result["journal_head_sha256"] != head:
        raise ValueError("process or journal changed across preflight")
    return {**result, "owned_process": before}
