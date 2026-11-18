"""Read-only native Mac process checks around recovery HTTP preflight."""

import re
import shlex
from pathlib import PurePosixPath

from .recovery_preflight import preflight_next

FILE_CAPTURE = """set -eu
file="$1"
/usr/bin/stat -Lf '%z|%m|%i' "$file"
/usr/bin/shasum -a 256 "$file"
/usr/bin/stat -Lf '%z|%m|%i' "$file"
"""


def observe_files(experiment, read_remote):
    """Hash every frozen shard and executable; no model inference is performed."""
    files = experiment.get("runtime_files")
    model = PurePosixPath(experiment["transport_policy"]["model"])
    executable = experiment["owned_process"]["executable"]
    match = re.fullmatch(r"(.+)-00001-of-(\d{5})\.gguf", model.name)
    if match:
        count = int(match[2])
        if not 1 <= count <= 16:
            raise ValueError("unsupported shard count")
        required = {
            str(model.parent / f"{match[1]}-{i:05d}-of-{count:05d}.gguf")
            for i in range(1, count + 1)
        }
    else:
        if re.search(r"-\d{5}-of-\d{5}\.gguf$", model.name):
            raise ValueError("model must identify the first shard")
        required = {str(model)}
    required.add(executable)
    if not isinstance(files, list) or len(files) != len(required):
        raise ValueError("all model shards and the executable must be frozen")
    paths = []
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "bytes", "sha256"}:
            raise ValueError("invalid frozen file record")
        path = entry["path"]
        if (
            not isinstance(path, str)
            or not path.startswith("/")
            or ".." in PurePosixPath(path).parts
            or any(c in path for c in "\r\n")
            or type(entry["bytes"]) is not int
            or entry["bytes"] <= 0
            or not isinstance(entry["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
        ):
            raise ValueError("invalid frozen path, size or hash")
        paths.append(path)
    if set(paths) != required or len(set(paths)) != len(paths):
        raise ValueError("runtime file coverage differs from model and executable")
    observed = []
    for entry in files:
        raw = read_remote(FILE_CAPTURE, entry["path"], timeout=600)
        lines = raw.strip().splitlines()
        if len(lines) != 3 or lines[0] != lines[2]:
            raise ValueError("file changed during hashing or capture was incomplete")
        metadata = lines[0].split("|")
        if (
            len(metadata) != 3
            or not all(v.isdigit() for v in metadata)
            or int(metadata[0]) != entry["bytes"]
            or lines[1] != entry["sha256"] + "  " + entry["path"]
        ):
            raise ValueError("runtime file identity differs from frozen record")
        observed.append(
            {**entry, "mtime": int(metadata[1]), "inode": int(metadata[2]), "raw_capture": raw}
        )
    return observed


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
    """Check frozen files and the same live process around HTTP preflight."""
    manifest, _, _, head = ledger.read()
    before = observe_process(manifest["experiment"], read_remote)
    files = observe_files(manifest["experiment"], read_remote)
    result = preflight_next(ledger, packet_root, key, transport=transport)
    for entry in files:
        observed = read_remote(
            "set -eu\n/usr/bin/stat -Lf '%z|%m|%i' \"$1\"\n", entry["path"], timeout=30
        ).strip()
        expected = f"{entry['bytes']}|{entry['mtime']}|{entry['inode']}"
        if observed != expected:
            raise ValueError("runtime file metadata changed after hashing")
    after = observe_process(manifest["experiment"], read_remote)
    if before != after or ledger.read()[3] != head or result["journal_head_sha256"] != head:
        raise ValueError("process or journal changed across preflight")
    return {**result, "owned_process": before, "runtime_files": files}
