"""Final V15 baseline allocation: frozen WSL client and owned native Mac server."""

import argparse
import json
import platform
import subprocess
from pathlib import Path

import v15_remote
from v15_confirmation import PROMPT_SHA

import aia_mp1
from aia_mp1.assessed_native import NativeJudgeConfig, PinnedClient
from aia_mp1.assessment import load_assessment, read_json, read_text, save_new
from aia_mp1.calibration import calibration_report
from aia_mp1.canonical_development import QWEN_MODEL_SHA, QWEN_SETTINGS
from aia_mp1.confirmation_review import byte_hash
from aia_mp1.confirmation_transport import RUNTIME
from aia_mp1.human_reference import load_reference
from aia_mp1.judge import judge_directory, judge_run, messages_for
from aia_mp1.qualification import validate_qualification
from aia_mp1.tracing import digest

BUNDLE_NAME = "MP1-QWEN35-V15-BASELINE-003"
ASSESSMENT_ID = "baseline-review-001"
ASSESSMENT_SHA = "dd0cfe746464e441ce42f1dfd706af7b65e10a2c3b8b2b304709b877a4f06932"
REFERENCE_SHA = "1e555ed74a0417120ac4d16052c3082e02e8e03550c3e2e09a64eda89856e4a8"
RUN_ID = "baseline-qwen35-v15-budget4096-003"
REPORT_ID = "baseline-qwen35-v15-budget4096-agreement-003"
PRIOR_RUNS = {"baseline-qwen35-v13-001", "baseline-qwen35-v13-budget4096-002"}
REMOTE_ROOT = "/Users/chadjosewski/AIA/MP1-handoff/" + BUNDLE_NAME + "/candidate"


def make_plan(config):
    parent, assessment, records, rubric = load_assessment(Path(config.artifact_root), ASSESSMENT_ID)
    reference = load_reference(parent, assessment, records)
    selection = validate_qualification(config, assessment)
    prompt = read_text(Path(config.prompt_path))
    runtime = RUNTIME | {"reasoning_budget": 4096}
    receipt = selection["receipt"]
    if (
        assessment["manifest_sha256"] != ASSESSMENT_SHA
        or reference["sha256"] != REFERENCE_SHA
        or len(records) != 50
        or len(assessment["selected_ids"]) != 20
    ):
        raise ValueError("requires the original fifty-item baseline and twenty frozen reviews")
    if (
        config.model_sha256 != QWEN_MODEL_SHA
        or {k: getattr(config, k) for k in QWEN_SETTINGS} != QWEN_SETTINGS
        or config.base_url != v15_remote.ENDPOINT
        or config.purpose != "baseline"
        or config.max_attempts != 2
        or config.reasoning_effort is not None
        or config.server_reasoning_budget != 4096
        or config.prompt_variant != "judge-v15-task-contract"
        or byte_hash(Path(config.prompt_path)) != PROMPT_SHA
        or receipt.get("prompt_sha256_bytes") != PROMPT_SHA
        or receipt.get("prompt_variant") != config.prompt_variant
        or receipt.get("native_runtime") != runtime
    ):
        raise ValueError("baseline differs from the selected V15 model, prompt or settings")
    versions = {p.name for p in (parent / "judges").iterdir()}
    if versions - {RUN_ID} != PRIOR_RUNS:
        raise ValueError("prior assessed versions differ; do not reset the three-version budget")
    plan = {
        "protocol": "qwen35-v15-final-baseline-v1",
        "assessment_id": ASSESSMENT_ID,
        "judge_run_id": RUN_ID,
        "report_id": REPORT_ID,
        "assessment_sha256": ASSESSMENT_SHA,
        "human_reference_sha256": REFERENCE_SHA,
        "qualification_sha256": selection["sha256"],
        "settings": QWEN_SETTINGS.copy(),
        "runtime": runtime,
        "models": [{"phase": "candidate", "model": config.model, "sha256": config.model_sha256}],
        "cases": [
            {"item_id": r["item_id"], "messages": messages_for(prompt, rubric, r)} for r in records
        ],
        "maximum_starts": 100,
        "consecutive_failure_stop": 2,
        "prior_starts": 338,
        "prior_assessed_versions": sorted(PRIOR_RUNS),
        "remote_root": REMOTE_ROOT,
        "acceptance_policy": "course-per-dimension-80-v1",
    }
    plan["sha256"] = digest(plan)
    return plan


def verify(root):
    manifest = read_json(root / "bundle-manifest.json")
    required = {
        "judge-config.json",
        "plan.json",
        "qualification/qualification.json",
        "run-on-mac.sh",
        "project/uv.lock",
        "project/pyproject.toml",
        "project/prompts/judge-v15-task-contract.md",
        "project/tools/v15_baseline.py",
        "project/tools/v15_remote.py",
        "project/tools/v15_confirmation.py",
    }
    required.update(
        f"project/src/aia_mp1/{p.name}" for p in Path(aia_mp1.__file__).parent.glob("*.py")
    )
    if not required.issubset(manifest["files_sha256"]):
        raise ValueError("baseline bundle omits required frozen files")
    for relative, expected in manifest["files_sha256"].items():
        path = root / relative
        if (
            not path.resolve().is_relative_to(root.resolve())
            or path.is_symlink()
            or byte_hash(path) != expected
        ):
            raise ValueError(f"frozen baseline bundle changed: {relative}")
    config = NativeJudgeConfig.model_validate_json(read_text(root / "judge-config.json"))
    # Relative configuration always resolves from this bundle, never the caller's cwd.
    config = config.model_copy(
        update={
            "artifact_root": str(root / "evidence"),
            "prompt_path": str(root / "project/prompts/judge-v15-task-contract.md"),
            "qualification_path": str(root / "qualification/qualification.json"),
        }
    )
    plan = read_json(root / "plan.json")
    if plan != make_plan(config) or manifest["plan_sha256"] != plan["sha256"]:
        raise ValueError("baseline plan differs from frozen selection and evidence")
    return config, plan


def execute(root):
    if platform.system() != "Linux" or "microsoft" not in platform.release().lower():
        raise ValueError("Python must run in WSL")
    project = root / "project"
    if (
        Path(__file__).resolve() != (project / "tools/v15_baseline.py").resolve()
        or Path(aia_mp1.__file__).resolve().parent != (project / "src/aia_mp1").resolve()
        or Path(v15_remote.__file__).resolve() != (project / "tools/v15_remote.py").resolve()
    ):
        raise ValueError("execute from the frozen baseline project")
    config, plan = verify(root)
    evidence = Path(config.artifact_root)
    directory = judge_directory(evidence / "assessments" / ASSESSMENT_ID, RUN_ID)
    if directory.exists() or (root / "runtime").exists():
        raise ValueError(
            "baseline allocation already started; preserve and inspect, no automatic resume"
        )
    runtime_dir = root / "runtime"
    runtime_dir.mkdir()
    v15_remote.preflight(plan, runtime_dir, remote_root=REMOTE_ROOT)
    runtime = read_json(runtime_dir / "candidate-runtime.json")

    def check_owned():
        process = v15_remote.owned(config.model, REMOTE_ROOT)
        if process != runtime["owned_process"]:
            raise ValueError("owned Mac process changed after baseline preflight")

    client = PinnedClient(plan, config.base_url, runtime, verify_process=check_owned)
    try:
        status = judge_run(
            evidence, ASSESSMENT_ID, RUN_ID, config, client, before_attempt=client.before_attempt
        )
    except KeyboardInterrupt:
        print(json.dumps({"stopped": client.stop_reason or "operator interruption"}), flush=True)
        return 1
    print(json.dumps(status), flush=True)
    if status["status"] != "complete":
        return 1
    report = calibration_report(evidence, ASSESSMENT_ID, RUN_ID, REPORT_ID)
    save_new(root / "calibration-summary.json", report)
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "ready" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "execute", "report"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.action == "execute":
            return execute(root)
        config, plan = verify(root)
        if args.action == "verify":
            print(
                json.dumps(
                    {"verified": True, "cases": len(plan["cases"]), "plan_sha256": plan["sha256"]}
                )
            )
        else:
            print(
                json.dumps(
                    calibration_report(
                        Path(config.artifact_root), ASSESSMENT_ID, RUN_ID, REPORT_ID, write=False
                    ),
                    indent=2,
                )
            )
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"V15 baseline stopped: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
