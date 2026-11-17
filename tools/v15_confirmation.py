"""Fresh V15 confirmation: frozen human review, WSL client, owned native Mac server."""

import argparse
import json
import platform
import subprocess
from pathlib import Path, PurePosixPath

import v15_remote
from v15_remote import ENDPOINT, owned, preflight

import aia_mp1
from aia_mp1.assessment import read_json, read_text
from aia_mp1.canonical_development import QWEN_FILES, QWEN_MODEL_SHA, QWEN_SETTINGS, save
from aia_mp1.confirmation_review import byte_hash, load_review, verify_packet
from aia_mp1.confirmation_transport import (
    GENERATOR_SHA,
    PHASES,
    RECOVERY_FILE,
    RUNTIME,
    audit,
    client_for,
    comparison_report,
    initialize,
    run_phase,
)
from aia_mp1.factcheck_transport import VerifiedTransport
from aia_mp1.tracing import digest, now

PACKET_SHA = "1098fb60c1497828deae342a7dc68a7647ae49f4952ee95258417947c7db1c07"
PROMPT_SHA = "0ff6b3170ff6a412d5c7846dc936e5ff699820c1f212d5592419eba2abe8b28d"
PACKET_ID = "qwen35-v15-blind-confirmation-v1"
BUNDLE_NAME = "MP1-QWEN35-V15-CONFIRMATION-001"
REMOTE_ROOT = "/Users/chadjosewski/AIA/MP1-handoff/" + BUNDLE_NAME


def make_plan(packet, review, model_paths, *, created_at=None):
    manifest, _ = verify_packet(packet, PACKET_SHA)
    reference = load_review(packet, PACKET_SHA, review)
    if (
        manifest["packet_id"] != PACKET_ID
        or manifest["prompt_sha256"] != PROMPT_SHA
        or manifest["settings"] != QWEN_SETTINGS
        or manifest["candidate_model_sha256"] != QWEN_MODEL_SHA
        or manifest["comparison_model_sha256"] != GENERATOR_SHA
        or manifest["prior_starts"] != 318
        or manifest["maximum_new_starts"] != 40
        or manifest["maximum_attempts_per_case_model"] != 2
        or manifest["runtime"].get("reasoning_budget") != 4096
        or any(manifest["runtime"][key] != value for key, value in RUNTIME.items())
    ):
        raise ValueError("V15 confirmation differs from the distributed protocol")
    names = (QWEN_FILES[0]["name"], "Qwen3-30B-A3B-Q4_K_M.gguf")
    if set(model_paths) != set(PHASES) or any(
        not PurePosixPath(model_paths[phase]).is_absolute()
        or PurePosixPath(model_paths[phase]).name != name
        for phase, name in zip(PHASES, names)
    ):
        raise ValueError("two frozen absolute Mac model paths required")
    plan = {
        "protocol": "qwen35-v15-blind-confirmation-v1",
        "created_at": created_at or now(),
        "packet_id": manifest["packet_id"],
        "packet_manifest_sha256": PACKET_SHA,
        "human_reference_sha256": reference["sha256"],
        "prior_starts": 318,
        "max_starts": 40,
        "settings": QWEN_SETTINGS.copy(),
        "runtime": {**RUNTIME, "reasoning_budget": 4096},
        "remote_root": REMOTE_ROOT,
        "models": [
            {"phase": phase, "model": model_paths[phase], "sha256": sha}
            for phase, sha in zip(PHASES, (QWEN_MODEL_SHA, GENERATOR_SHA))
        ],
        "cases": [
            json.loads(line) for line in read_text(packet / "model-inputs.jsonl").splitlines()
        ],
    }
    plan["sha256"] = digest(plan)
    return plan


def verify(root):
    manifest = read_json(root / "bundle-manifest.json")
    required = {
        "plan.json",
        "run-on-mac.sh",
        "project/uv.lock",
        "project/pyproject.toml",
        "project/tools/v15_confirmation.py",
        "project/tools/v15_remote.py",
        "project/src/aia_mp1/confirmation_transport.py",
        "packet/manifest.json",
        "review/human-reference.json",
        "review/submitted-answers.md",
    }
    if not required <= set(manifest["files_sha256"]):
        raise ValueError("V15 bundle is missing required files")
    for relative, expected in manifest["files_sha256"].items():
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("unsafe V15 bundle path")
        if byte_hash(path) != expected:
            raise ValueError(f"frozen V15 bundle file differs: {relative}")
    plan = read_json(root / "plan.json")
    expected = make_plan(
        root / "packet",
        root / "review",
        {m["phase"]: m["model"] for m in plan["models"]},
        created_at=plan["created_at"],
    )
    if plan != expected or manifest["plan_sha256"] != plan["sha256"]:
        raise ValueError("V15 plan differs from the frozen review or protocol")
    if manifest["human_reference_sha256"] != plan["human_reference_sha256"]:
        raise ValueError("V15 bundle human reference differs")
    if (root / "results" / RECOVERY_FILE).exists():
        raise ValueError("historical recovery amendment does not authorize V15 recovery")
    return plan


def execute(root, plan, phase):
    if platform.system() != "Linux" or "microsoft" not in platform.release().lower():
        raise ValueError("Python must run in WSL")
    # Run only the frozen implementation, including all imported project modules.
    project = Path(__file__).resolve().parents[1]
    if (
        project.resolve() != (root / "project").resolve()
        or Path(aia_mp1.__file__).resolve().parent != project / "src/aia_mp1"
        or Path(v15_remote.__file__).resolve() != project / "tools/v15_remote.py"
    ):
        raise ValueError("execute from the frozen bundle project")
    directory = root / "results"
    if not directory.exists():
        if phase != "candidate":
            raise ValueError("candidate phase must initialize the shared ledger")
        initialize(plan, directory)
    model = next(m for m in plan["models"] if m["phase"] == phase)
    remote_root = plan["remote_root"] + "/" + phase

    def check_owned():
        observation = read_json(directory / f"{phase}-runtime.json")
        process = owned(model["model"], remote_root)
        if (
            observation["plan_sha256"] != plan["sha256"]
            or observation["phase"] != phase
            or process != observation["owned_process"]
        ):
            raise ValueError("owned Mac process changed after preflight")
        return process

    def dispatch(model, case, wire):
        transport = VerifiedTransport(wire)
        with client_for(plan, model, ENDPOINT, transport) as client:
            result = client.generate(case["messages"])
        if transport.calls != 1:
            raise ValueError("unverified dispatch; preserve unknown start")
        return result.raw_response, result.error

    state = run_phase(
        plan,
        phase,
        directory,
        dispatch,
        verify_before=lambda: preflight(plan, directory, phase=phase, remote_root=remote_root),
        before_attempt=check_owned,
    )
    reference = load_review(root / "packet", PACKET_SHA, root / "review")
    result = comparison_report(plan, state, reference)
    save(directory / f"{phase}-report.json", result)
    print(json.dumps(result, indent=2))
    return 0 if len(state["successful"][phase]) == len(plan["cases"]) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "execute", "report"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--phase", choices=PHASES)
    args = parser.parse_args(argv)
    try:
        plan = verify(args.root)
        if args.action == "verify":
            print(json.dumps({"verified": True, "plan_sha256": plan["sha256"]}))
            return 0
        if args.action == "report":
            reference = load_review(args.root / "packet", PACKET_SHA, args.root / "review")
            print(
                json.dumps(comparison_report(plan, audit(plan, args.root / "results"), reference))
            )
            return 0
        if args.phase is None:
            raise ValueError("explicit phase required")
        return execute(args.root, plan, args.phase)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"V15 confirmation stopped: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
