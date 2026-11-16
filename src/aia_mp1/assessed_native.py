"""Pinned native-Mac preflight around the existing assessed judge/calibration pipeline."""

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import Field

from .assessment import load_assessment, read_json, read_text
from .calibration import calibration_report
from .canonical_development import QWEN_MODEL_SHA, QWEN_SETTINGS, save
from .confirmation_review import byte_hash
from .confirmation_transport import RUNTIME, client_for, prepare_runtime, wire_for
from .factcheck_transport import LocalServer, VerifiedTransport, loopback_url
from .human_reference import load_reference
from .judge import JudgeConfig, judge_directory, judge_run, judge_status, messages_for
from .qualification import validate_qualification
from .tracing import digest, read_records, run_directory


class NativeJudgeConfig(JudgeConfig):
    server_reasoning_budget: Literal[4096] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


def native_plan(config, assessment_id, judge_run_id, *, report_id=None):
    loopback_url(config.base_url)
    parent, assessment, records, rubric = load_assessment(Path(config.artifact_root), assessment_id)
    reference = load_reference(parent, assessment, records)
    qualification = validate_qualification(config, assessment)
    prompt = read_text(Path(config.prompt_path))
    if (
        config.model_sha256 != QWEN_MODEL_SHA
        or {k: getattr(config, k) for k in QWEN_SETTINGS} != QWEN_SETTINGS
        or config.max_attempts != 2
        or config.reasoning_effort is not None
        or digest(prompt) != "66e59f09239a13e5a99919e95fbadff5094b30f4b309068e2bdfffba63efd000"
    ):
        raise ValueError("assessed configuration differs from selected frozen V13 settings")
    runtime = RUNTIME.copy()
    budget = getattr(config, "server_reasoning_budget", None)
    if budget is not None:
        if budget != 4096:
            raise ValueError("only the approved 4096 thinking cap is supported")
        runtime["reasoning_budget"] = budget
        if qualification["receipt"].get("native_runtime") != runtime:
            raise ValueError("qualification does not bind the amended native runtime")
        if not report_id:
            raise ValueError("amended run requires its own report identity")
    plan = {
        "protocol": "qwen35-assessed-native-v1",
        "assessment_id": assessment_id,
        "judge_run_id": judge_run_id,
        "assessment_sha256": assessment["manifest_sha256"],
        "human_reference_sha256": reference["sha256"],
        "qualification_sha256": qualification["sha256"],
        "settings": QWEN_SETTINGS.copy(),
        "runtime": runtime,
        "models": [{"phase": "candidate", "model": config.model, "sha256": config.model_sha256}],
        "cases": [
            {"item_id": r["item_id"], "messages": messages_for(prompt, rubric, r)} for r in records
        ],
        "maximum_starts": len(records) * 2,
        "consecutive_failure_stop": 2,
    }
    if report_id is not None:
        run_directory(parent / "calibration", report_id)
        plan["report_id"] = report_id
    plan["sha256"] = digest(plan)
    return plan


def verify_bundle(root):
    manifest = read_json(root / "bundle-manifest.json")
    required = {
        "judge-config.json",
        "native-plan.json",
        "project/uv.lock",
        "project/pyproject.toml",
        "project/prompts/judge-v13-hazards.md",
        "qualification/qualification.json",
    }
    required.update(f"project/src/aia_mp1/{p.name}" for p in Path(__file__).parent.glob("*.py"))
    if not required.issubset(manifest["files_sha256"]):
        raise ValueError("assessed bundle omits required frozen files")
    for relative, expected in manifest["files_sha256"].items():
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
            raise ValueError("unsafe assessed bundle path")
        if byte_hash(path) != expected:
            raise ValueError(f"assessed bundle changed: {relative}")
    config = NativeJudgeConfig.model_validate_json(read_text(root / "judge-config.json"))
    plan = read_json(root / "native-plan.json")
    expected = native_plan(
        config, plan["assessment_id"], plan["judge_run_id"], report_id=plan.get("report_id")
    )
    if expected != plan or manifest["plan_sha256"] != plan["sha256"]:
        raise ValueError("assessed plan differs from frozen selection and evidence")
    return config, plan


def verify_owned_runtime(root, model, budget):
    pid = int((root / "runtime/owned-server.pid").read_text())
    parent = int((root / "runtime/launcher.pid").read_text())
    argv = shlex.split(
        subprocess.check_output(
            ["/bin/ps", "-ww", "-o", "command=", "-p", str(pid)], text=True
        ).strip()
    )
    observed_parent = int(
        subprocess.check_output(["/bin/ps", "-o", "ppid=", "-p", str(pid)], text=True)
    )
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
        str(budget),
    ]
    if argv != expected or observed_parent != parent:
        raise ValueError("owned server command, parent or approved thinking budget differs")
    return {"pid": pid, "parent_pid": parent, "argv": argv}


class PinnedClient:
    def __init__(self, plan, endpoint, runtime, *, consecutive_failures=0, verify_process=None):
        if "reasoning_budget" in plan["runtime"] and verify_process is None:
            raise ValueError("budgeted run requires owned-process verification")
        self.verify_process = verify_process
        self.plan, self.endpoint, self.runtime = plan, endpoint, runtime
        self.model = plan["models"][0]
        self.cases = {c["item_id"]: c for c in plan["cases"]}
        self.failures = consecutive_failures
        self.current = None
        self.stop_reason = None

    def before_attempt(self, record, number):
        if self.failures >= self.plan["consecutive_failure_stop"]:
            self.stop_reason = "two consecutive failed judgments; inspect before continuation"
            raise KeyboardInterrupt
        self.current = self.cases[record["item_id"]]
        server = LocalServer(self.endpoint, "local-assessed")
        try:
            if self.verify_process is not None:
                self.verify_process()
            props = server.json("/props")
            first = self.runtime["properties"]
            if (
                server.json("/health")["status"] != "ok"
                or any(
                    props[k] != first[k]
                    for k in ("build_info", "model_path", "total_slots", "chat_template")
                )
                or props["default_generation_settings"]["n_ctx"] != RUNTIME["ctx_size"]
            ):
                raise ValueError("assessed runtime changed")
        except Exception as exc:
            self.stop_reason = f"pre-dispatch runtime check failed: {type(exc).__name__}"
            raise KeyboardInterrupt from exc
        finally:
            server.close()

    def generate(self, messages):
        if self.current is None or messages != self.current["messages"]:
            raise ValueError("assessed request differs from native preflight")
        wire = wire_for(self.plan, self.model, self.current)
        transport = VerifiedTransport(wire)
        with client_for(self.plan, self.model, self.endpoint, transport) as client:
            result = client.generate(messages)
        if transport.calls != 1:
            raise ValueError("no verified dispatch; preserve the unknown request start")
        valid = result.item is not None and result.response_model == self.model["model"]
        self.failures = 0 if valid else self.failures + 1
        print(json.dumps({"item_id": self.current["item_id"], "valid": valid}), flush=True)
        self.current = None
        return result


def execute(root, *, resume=False):
    config, plan = verify_bundle(root)
    evidence = Path(config.artifact_root)
    assessment_id, run_id = plan["assessment_id"], plan["judge_run_id"]
    directory = judge_directory(evidence / "assessments" / assessment_id, run_id)
    failures = 0
    if resume:
        status = judge_status(evidence, assessment_id, run_id)
        if status["unresolved_request_ids"]:
            raise ValueError("unknown assessed request outcome; inspect instead of resuming")
        for attempt in reversed(read_records(directory / "attempts.jsonl")):
            if attempt["valid"]:
                break
            failures += 1
        if failures >= 2:
            raise ValueError("consecutive-failure stop remains active")
    elif directory.exists():
        raise ValueError("assessed run already exists; inspect before explicit resume")
    runtime_dir = root / "runtime"
    runtime_dir.mkdir(exist_ok=True)
    verify_process = None
    if config.server_reasoning_budget is not None:

        def verify_process():
            return verify_owned_runtime(root, config.model, config.server_reasoning_budget)

        number = len(list(runtime_dir.glob("owned-launch-*.json"))) + 1
        save(runtime_dir / f"owned-launch-{number:03d}.json", verify_process())
    runtime = prepare_runtime(plan, "candidate", runtime_dir, config.base_url)
    client = PinnedClient(
        plan, config.base_url, runtime, consecutive_failures=failures, verify_process=verify_process
    )
    try:
        status = judge_run(
            evidence,
            assessment_id,
            run_id,
            config,
            client,
            resume=resume,
            before_attempt=client.before_attempt,
        )
    except KeyboardInterrupt:
        print(json.dumps({"stopped": client.stop_reason or "operator interruption"}), flush=True)
        return 1
    print(json.dumps(status, indent=2), flush=True)
    if status["status"] != "complete":
        return 1
    report = calibration_report(
        evidence, assessment_id, run_id, plan.get("report_id", "baseline-qwen35-v13-agreement-001")
    )
    save(root / "calibration-summary.json", report)
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "ready" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "execute"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "verify":
            _, plan = verify_bundle(args.root)
            print(
                json.dumps(
                    {"verified": True, "cases": len(plan["cases"]), "plan_sha256": plan["sha256"]}
                )
            )
            return 0
        return execute(args.root, resume=args.resume)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Assessed run stopped: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
