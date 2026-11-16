"""Approval-gated, two-case development probe; never writes assessed judgments."""

import argparse
import json
import shlex
import subprocess
from pathlib import Path

from aia_mp1.assessment import read_json
from aia_mp1.canonical_development import save
from aia_mp1.confirmation_review import byte_hash
from aia_mp1.confirmation_transport import (
    RUNTIME,
    client_for,
    initialize,
    prepare_runtime,
    run_phase,
)
from aia_mp1.factcheck_transport import VerifiedTransport
from aia_mp1.tracing import digest

SOURCE_SHA = "fa1b157fe4f0336a6eeed633597163950d878b1da8095950f7cd5e08573a1c85"
CASES = ("baseline-001-b01-item-0015", "baseline-001-b01-item-0028")


def derive_plan(source):
    if (
        source["sha256"] != SOURCE_SHA
        or digest({k: v for k, v in source.items() if k != "sha256"}) != SOURCE_SHA
    ):
        raise ValueError("source assessed plan differs")
    by_id = {case["item_id"]: case for case in source["cases"]}
    plan = {
        "protocol": "qwen35-thinking-budget-probe-v1",
        "purpose": "Development feasibility on two known cases; not assessed calibration",
        "source_plan_sha256": SOURCE_SHA,
        "settings": source["settings"],
        "runtime": RUNTIME | {"reasoning_budget": 4096},
        "models": source["models"],
        "cases": [by_id[item_id] for item_id in CASES],
        "max_starts": 4,
        "prior_starts": 0,
    }
    plan["sha256"] = digest(plan)
    return plan


def verify(root):
    manifest = read_json(root / "bundle-manifest.json")
    required = {
        "plan.json",
        "source-plan.json",
        "run-on-mac.sh",
        "project/tools/reasoning_budget_probe.py",
        "project/uv.lock",
        "project/pyproject.toml",
    }
    required.update(
        f"project/src/aia_mp1/{p.name}"
        for p in (Path(__file__).resolve().parents[1] / "src/aia_mp1").glob("*.py")
    )
    if not required <= manifest["files_sha256"].keys():
        raise ValueError("probe manifest omits required files")
    for name, sha in manifest["files_sha256"].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
            raise ValueError("unsafe probe path")
        if byte_hash(path) != sha:
            raise ValueError(f"frozen probe file changed: {name}")
    plan = read_json(root / "plan.json")
    if (
        plan != derive_plan(read_json(root / "source-plan.json"))
        or plan["sha256"] != manifest["plan_sha256"]
    ):
        raise ValueError("probe differs from proposed exact inputs and budget")
    return plan


def require_approval(root, plan):
    path = root / "owner-approval.json"
    if not path.exists():
        raise ValueError("owner approval required for changing the frozen thinking budget")
    approval = read_json(path)
    if (
        approval.get("plan_sha256") != plan["sha256"]
        or approval.get("approved_by") != "Chad Josewski"
        or approval.get("source") != "user_message"
        or not isinstance(approval.get("owner_statement"), str)
        or not approval["owner_statement"].strip()
        or not approval.get("approved_at")
    ):
        raise ValueError("owner approval does not cover this frozen probe")
    return approval


def server_command(model):
    return [
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


def check_owned_server(root, model):
    pid = int((root / "runtime/owned-server.pid").read_text())
    parent = int((root / "runtime/launcher.pid").read_text())
    command = subprocess.check_output(
        ["/bin/ps", "-o", "command=", "-p", str(pid)], text=True
    ).strip()
    observed_parent = int(
        subprocess.check_output(["/bin/ps", "-o", "ppid=", "-p", str(pid)], text=True)
    )
    if shlex.split(command) != server_command(model) or observed_parent != parent:
        raise ValueError("owned server command or thinking budget differs")
    return {"pid": pid, "parent_pid": parent, "argv": shlex.split(command)}


def execute(root, plan):
    approval = require_approval(root, plan)
    directory = root / "results"
    initialize(plan, directory)
    save(directory / "approval.json", approval)
    model = plan["models"][0]
    endpoint = "http://127.0.0.1:8081/v1"

    def preflight():
        save(directory / "owned-launch.json", check_owned_server(root, model["model"]))
        prepare_runtime(plan, "candidate", directory, endpoint)

    def dispatch(model, case, wire):
        check_owned_server(root, model["model"])
        transport = VerifiedTransport(wire)
        with client_for(plan, model, endpoint, transport) as client:
            result = client.generate(case["messages"])
        if transport.calls != 1:
            raise ValueError("unverified dispatch; preserve unknown request start")
        return result.raw_response, result.error

    state = run_phase(plan, "candidate", directory, dispatch, verify_before=preflight)
    summary = {
        "plan_sha256": plan["sha256"],
        "starts": len(state["attempts"]),
        "complete_cases": len(state["successful"]["candidate"]),
        "required_cases": 2,
        "assessed_calibration": False,
        "automatic_follow_on_run": False,
    }
    save(directory / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary["complete_cases"] == 2 else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "authorize", "execute"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        plan = verify(args.root)
        if args.action == "verify":
            print(
                json.dumps({"verified": True, "plan_sha256": plan["sha256"], "model_requests": 0})
            )
            return 0
        require_approval(args.root, plan)
        if args.action == "authorize":
            print(json.dumps({"authorized": True, "plan_sha256": plan["sha256"]}))
            return 0
        return execute(args.root, plan)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"Probe stopped: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
