"""WSL Python client with a separately owned native Mac inference server."""

import hashlib
import platform
import shlex
import subprocess
from pathlib import PurePosixPath

from aia_mp1.canonical_development import QWEN_FILES, QWEN_MODEL_SHA, save
from aia_mp1.confirmation_transport import (
    GENERATOR_SHA,
    QWEN3_TEMPLATE_SHA,
    RUNTIME,
    verify_thinking_template,
    wire_for,
)
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.tracing import now

REMOTE_ROOT = "/Users/chadjosewski/AIA/MP1-handoff/MP1-QWEN35-V15-20261117"
ENDPOINT = "http://127.0.0.1:18081/v1"
TEMPLATE_SHA = "a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715"
SSH = [
    "/mnt/c/Windows/System32/OpenSSH/ssh.exe",
    "-i",
    "C:/Users/cjose/.ssh/id_ed25519_aia_mp1_mac",
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=10",
    "-o",
    "HostKeyAlias=hammerhead-shark.local",
    "chadjosewski@192.168.0.216",
]


def remote(script, *args, timeout=30):
    command = "bash -s -- " + " ".join(shlex.quote(str(a)) for a in args)
    return subprocess.check_output(SSH + [command], input=script, text=True, timeout=timeout)


def validate_owned(text, model):
    lines = text.strip().splitlines()
    if len(lines) != 5 or lines[0] != "Darwin arm64":
        raise ValueError("native Mac ownership observation malformed")
    pid, parent, observed_parent = (int(x) for x in lines[1:4])
    expected = [
        "/opt/homebrew/bin/llama-server",
        "--model",
        model,
        "--host",
        "127.0.0.1",
        "--port",
        "8081",
        "--ctx-size",
        "16384",
        "--parallel",
        "1",
        "--reasoning",
        "on",
        "--reasoning-format",
        "deepseek",
        "--reasoning-budget",
        "4096",
    ]
    argv = shlex.split(lines[4])
    if pid <= 1 or parent <= 1 or observed_parent != parent or argv != expected:
        raise ValueError("owned Mac command, parent or budget differs")
    return {"pid": pid, "parent_pid": parent, "argv": argv, "host": lines[0]}


def owned(model, remote_root=REMOTE_ROOT):
    text = remote(
        """set -eu
root="$1"
uname -sm
pid=$(cat "$root/runtime/owned-server.pid")
cat "$root/runtime/owned-server.pid" "$root/runtime/launcher.pid"
/bin/ps -o ppid= -p "$pid"
/bin/ps -ww -o command= -p "$pid"
""",
        remote_root,
    )
    return validate_owned(text, model)


def preflight(plan, directory, *, phase="candidate", remote_root=REMOTE_ROOT, endpoint=ENDPOINT):
    if platform.system() != "Linux" or "microsoft" not in platform.release().lower():
        raise ValueError("Python must run in WSL")
    model = next(m for m in plan["models"] if m["phase"] == phase)
    observed_files = []
    expected_files = (
        QWEN_FILES
        if phase == "candidate"
        else [{"name": PurePosixPath(model["model"]).name, "sha256": GENERATOR_SHA}]
    )
    for expected in expected_files:
        path = PurePosixPath(model["model"]).parent / expected["name"]
        result = remote(
            """set -eu
/usr/bin/stat -f %z "$1"
/usr/bin/shasum -a 256 "$1"
""",
            path,
            timeout=600,
        ).splitlines()
        observed_files.append(
            {"name": path.name, "bytes": int(result[0]), "sha256": result[1].split()[0]}
        )
    if (
        phase == "candidate" and (observed_files != QWEN_FILES or model["sha256"] != QWEN_MODEL_SHA)
    ) or (
        phase == "comparator"
        and (observed_files[0]["sha256"] != GENERATOR_SHA or model["sha256"] != GENERATOR_SHA)
    ):
        raise ValueError("Mac weight identity differs")
    process = owned(model["model"], remote_root)
    server = LocalServer(endpoint, "local-confirmation")
    try:
        props = server.json("/props")
        models = server.json("/v1/models")["data"]
        if (
            props["build_info"] != RUNTIME["build_info"]
            or props["total_slots"] != RUNTIME["parallel"]
            or props["default_generation_settings"]["n_ctx"] != RUNTIME["ctx_size"]
            or props["model_path"] != model["model"]
            or hashlib.sha256(props["chat_template"].encode()).hexdigest()
            != (TEMPLATE_SHA if phase == "candidate" else QWEN3_TEMPLATE_SHA)
            or len(models) != 1
            or models[0]["id"] != model["model"]
            or server.json("/health")["status"] != "ok"
        ):
            raise ValueError("Mac endpoint runtime differs")
        checks = []
        for case in plan["cases"]:
            wire = wire_for(plan, model, case)
            rendered = server.json("/apply-template", wire)["prompt"]
            verify_thinking_template(phase, props, rendered)
            check = server.token_fit(wire, RUNTIME["ctx_size"])
            if not check["fits"]:
                raise ValueError("input plus output exceeds context")
            checks.append({"item_id": case["item_id"], **check})
        save(
            directory / f"{phase}-runtime.json",
            {
                "recorded_at": now(),
                "plan_sha256": plan["sha256"],
                "phase": phase,
                "properties": props,
                "token_checks": checks,
                "weights": observed_files,
                "owned_process": process,
                "client_platform": platform.platform(),
                "python": platform.python_version(),
                "transport": "WSL client via SSH loopback tunnel; native Mac inference",
                "endpoint": endpoint,
            },
        )
    finally:
        server.close()
