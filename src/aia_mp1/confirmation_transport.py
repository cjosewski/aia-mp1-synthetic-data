"""Matched native-Mac confirmation, gated on a frozen attributed human review."""

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import httpx

from .assessment import exclusive, read_json, read_text
from .canonical_development import (
    QWEN_FILES,
    QWEN_MODEL_SHA,
    QWEN_SETTINGS,
    parse,
    save,
    verify_runtime,
)
from .confirmation_review import byte_hash, load_review, verify_packet
from .evaluation_schemas import DIMENSIONS, Judgment
from .factcheck_transport import LocalServer, VerifiedTransport, loopback_url
from .model_client import InstructorClient
from .tracing import digest, now

PHASES = ("candidate", "comparator")
GENERATOR_SHA = "9f1a24700a339b09c06009b729b5c809e0b64c213b8af5b711b3dbdfd0c5ba48"
RUNTIME = {"build_info": "b12110-cd959bae9", "ctx_size": 16384, "parallel": 1}
RECOVERY_FILE = "external-interruption-recovery.json"


def check_external_interruption(attempts):
    """Only two recorded connection losses, after an otherwise valid prefix, qualify."""
    if len(attempts) < 2:
        raise ValueError("two recorded connection failures required for recovery")
    tail = attempts[-2:]
    if (
        any(a["result"]["judgment"] is None for a in attempts[:-2])
        or [a["start"]["number"] for a in tail] != [1, 2]
        or len({(a["start"]["phase"], a["start"]["item_id"]) for a in tail}) != 1
        or any(
            a["result"]["raw_response"] is not None
            or a["result"]["error"] != "Connection error."
            or a["result"]["judgment"] is not None
            for a in tail
        )
    ):
        raise ValueError("recovery requires a confirmed external connection-loss boundary")


def record_external_recovery(plan, directory, incident):
    """Record an explicit protocol amendment; never erase attempts or rerun successes."""
    with exclusive(directory):
        if (directory / RECOVERY_FILE).exists():
            raise ValueError("external interruption recovery already recorded")
        state = audit(plan, directory)
        check_external_interruption(state["attempts"])
        if state["consecutive_failures"] != 2 or len(state["attempts"]) >= plan["max_starts"]:
            raise ValueError("recovery needs a stopped ledger with remaining total budget")
        required = {"reported_by", "incident_statement", "availability_statement"}
        if set(incident) != required or any(
            not isinstance(v, str) or not v.strip() for v in incident.values()
        ):
            raise ValueError("attributed incident and availability statements required")
        count = len(state["attempts"])
        receipt = {
            "protocol_amendment": "external-interruption-recovery-v1",
            "plan_sha256": plan["sha256"],
            "created_at": now(),
            "after_serial": count,
            "additional_attempts_for_interrupted_case": 1,
            "total_start_limit": plan["max_starts"],
            "incident": incident,
            "attribution_boundary": "Owner statements recorded; not independently authenticated.",
            "prefix_files_sha256": {
                f"{i:03d}-{kind}.json": byte_hash(directory / f"{i:03d}-{kind}.json")
                for i in range(1, count + 1)
                for kind in ("start", "result")
            },
        }
        receipt["sha256"] = digest(receipt)
        save(directory / RECOVERY_FILE, receipt)
        return receipt


def read_external_recovery(plan, directory):
    path = directory / RECOVERY_FILE
    if not path.exists():
        return None
    receipt = read_json(path)
    count = receipt["after_serial"]
    if (
        type(count) is not int
        or not 2 <= count < plan["max_starts"]
        or receipt["sha256"] != digest({k: v for k, v in receipt.items() if k != "sha256"})
        or receipt["protocol_amendment"] != "external-interruption-recovery-v1"
        or receipt["plan_sha256"] != plan["sha256"]
        or receipt["additional_attempts_for_interrupted_case"] != 1
        or receipt["total_start_limit"] != plan["max_starts"]
    ):
        raise ValueError("external recovery amendment identity differs")
    expected = {
        f"{i:03d}-{kind}.json": byte_hash(directory / f"{i:03d}-{kind}.json")
        for i in range(1, count + 1)
        for kind in ("start", "result")
    }
    if receipt["prefix_files_sha256"] != expected:
        raise ValueError("interrupted ledger prefix changed")
    return receipt


def make_plan(packet, manifest_sha256, review, model_paths, *, created_at=None):
    manifest, _ = verify_packet(packet, manifest_sha256)
    reference = load_review(packet, manifest_sha256, review)
    if (
        manifest["settings"] != QWEN_SETTINGS
        or manifest["candidate_model_sha256"] != QWEN_MODEL_SHA
        or manifest["comparison_model_sha256"] != GENERATOR_SHA
        or manifest["prior_starts"] != 190
        or manifest["maximum_new_starts"] != 40
        or manifest["maximum_attempts_per_case_model"] != 2
        or any(manifest["runtime"][key] != value for key, value in RUNTIME.items())
    ):
        raise ValueError("confirmation protocol differs from the distributed packet")
    expected_names = (QWEN_FILES[0]["name"], "Qwen3-30B-A3B-Q4_K_M.gguf")
    if set(model_paths) != set(PHASES) or any(
        not Path(model_paths[phase]).is_absolute() or Path(model_paths[phase]).name != name
        for phase, name in zip(PHASES, expected_names)
    ):
        raise ValueError("confirmation requires the two frozen absolute model paths")
    plan = {
        "protocol": "qwen35-v13-blind-confirmation-v1",
        "created_at": created_at or now(),
        "packet_id": manifest["packet_id"],
        "packet_manifest_sha256": manifest_sha256,
        "human_reference_sha256": reference["sha256"],
        "prior_starts": 190,
        "max_starts": 40,
        "settings": QWEN_SETTINGS.copy(),
        "runtime": RUNTIME.copy(),
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


def load_plan(path, packet, review):
    plan = read_json(path)
    expected = make_plan(
        packet,
        plan["packet_manifest_sha256"],
        review,
        {model["phase"]: model["model"] for model in plan["models"]},
        created_at=plan["created_at"],
    )
    if plan != expected:
        raise ValueError("confirmation plan no longer matches reviewed inputs and frozen settings")
    return plan


def client_for(plan, model, endpoint, transport=None):
    return InstructorClient(
        base_url=endpoint,
        model=model["model"],
        api_key="local-confirmation",
        response_model=Judgment,
        _transport=transport,
        **plan["settings"],
    )


def wire_for(plan, model, case):
    captured = []

    def capture(request):
        captured.append(json.loads(request.content))
        return httpx.Response(400, json={"error": {"message": "Offline serialization"}})

    with client_for(plan, model, "http://127.0.0.1:1/v1", httpx.MockTransport(capture)) as client:
        client.generate(case["messages"])
    if len(captured) != 1 or "reasoning_effort" in captured[0]:
        raise ValueError("confirmation wire differs from native-thinking configuration")
    return captured[0]


def queue_for(plan):
    return [(model, case) for model in plan["models"] for case in plan["cases"]]


def initialize(plan, directory):
    if directory.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError("confirmation evidence must stay outside the repository")
    directory.mkdir(parents=True, exist_ok=False)
    save(
        directory / "manifest.json",
        {
            "plan_sha256": plan["sha256"],
            "schema_sha256": digest(Judgment.model_json_schema()),
        },
    )


def audit(plan, directory):
    """Replay the entire two-model ledger; a phase switch cannot reset failures."""
    if plan["sha256"] != digest({k: v for k, v in plan.items() if k != "sha256"}):
        raise ValueError("confirmation plan hash differs")
    if read_json(directory / "manifest.json") != {
        "plan_sha256": plan["sha256"],
        "schema_sha256": digest(Judgment.model_json_schema()),
    }:
        raise ValueError("confirmation ledger identity differs")
    queue = queue_for(plan)
    recovery = read_external_recovery(plan, directory)
    attempts, successful = [], {phase: {} for phase in PHASES}
    next_index, number, failures = 0, 1, 0
    starts = sorted(directory.glob("*-start.json"))
    if len(starts) > plan["max_starts"]:
        raise ValueError("confirmation total request budget exceeded")
    for serial, path in enumerate(starts, 1):
        if failures >= 2 or next_index >= len(queue):
            raise ValueError("confirmation request after terminal boundary")
        model, case = queue[next_index]
        start = read_json(path)
        if (
            path.name != f"{serial:03d}-start.json"
            or start["phase"] != model["phase"]
            or start["item_id"] != case["item_id"]
            or start["number"] != number
            or start["plan_sha256"] != plan["sha256"]
            or start["wire_sha256"] != digest(wire_for(plan, model, case))
        ):
            raise ValueError("confirmation request order or wire differs")
        result_path = directory / f"{serial:03d}-result.json"
        if not result_path.exists():
            raise ValueError("unknown request outcome; preserve for inspection, no retry")
        result = read_json(result_path)
        judgment = parse(result["raw_response"], model["model"])
        if (
            result["start_sha256"] != digest(start)
            or result["sha256"] != digest({k: v for k, v in result.items() if k != "sha256"})
            or result["judgment"] != judgment
        ):
            raise ValueError("confirmation result lineage or parsed judgment differs")
        attempts.append({"start": start, "result": result})
        if judgment:
            successful[model["phase"]][case["item_id"]] = judgment
            failures, number = 0, 1
            next_index += 1
        else:
            failures += 1
            number += 1
            if number > 2:
                next_index += 1
                number = 1
        if recovery and serial == recovery["after_serial"]:
            check_external_interruption(attempts)
            if failures != 2:
                raise ValueError("recovery does not follow the terminal connection losses")
            # The two original starts still count. Permit exactly one third attempt.
            next_index -= 1
            number, failures = 3, 0
    if len(list(directory.glob("*-result.json"))) != len(starts):
        raise ValueError("orphan confirmation result")
    return {
        "attempts": attempts,
        "successful": successful,
        "next_index": next_index,
        "next_number": number,
        "consecutive_failures": failures,
        "external_interruption_recovery": recovery,
    }


def next_phase(plan, state):
    queue = queue_for(plan)
    if state["consecutive_failures"] >= 2 or len(state["attempts"]) >= plan["max_starts"]:
        return None
    return queue[state["next_index"]][0]["phase"] if state["next_index"] < len(queue) else None


def weight_identity(model):
    path = Path(model["model"])
    if model["phase"] == "candidate":
        observed = []
        for expected in QWEN_FILES:
            shard = path.parent / expected["name"]
            with shard.open("rb") as stream:
                sha = hashlib.file_digest(stream, "sha256").hexdigest()
            observed.append({"name": shard.name, "bytes": shard.stat().st_size, "sha256": sha})
        if observed != QWEN_FILES:
            raise ValueError("confirmation candidate shard identity differs")
        checksum = digest(observed)
    else:
        with path.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    if checksum != model["sha256"]:
        raise ValueError("confirmation model checksum differs")
    return checksum


def prepare_runtime(plan, phase, directory, endpoint):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("native Apple Silicon Mac required")
    model = next(model for model in plan["models"] if model["phase"] == phase)
    server = LocalServer(endpoint, "local-confirmation")
    try:
        props = server.json("/props")
        models = server.json("/v1/models")["data"]
        if (
            props["build_info"] != RUNTIME["build_info"]
            or props["total_slots"] != RUNTIME["parallel"]
            or props["default_generation_settings"]["n_ctx"] != RUNTIME["ctx_size"]
            or props["model_path"] != model["model"]
            or len(models) != 1
            or models[0]["id"] != model["model"]
            or server.json("/health")["status"] != "ok"
        ):
            raise ValueError("confirmation runtime differs from the frozen plan")
        checksum = weight_identity(model)
        checks = []
        for case in plan["cases"]:
            wire = wire_for(plan, model, case)
            rendered = server.json("/apply-template", wire)["prompt"]
            if not rendered.rstrip().endswith("<|im_start|>assistant\n<think>"):
                raise ValueError("confirmation template did not open native thinking")
            check = server.token_fit(wire, RUNTIME["ctx_size"])
            if not check["fits"]:
                raise ValueError("confirmation input plus output allowance exceeds context")
            checks.append({"item_id": case["item_id"], **check})
        observation = {
            "plan_sha256": plan["sha256"],
            "phase": phase,
            "properties": props,
            "token_checks": checks,
            "python": platform.python_version(),
            "machine": platform.node(),
            "weight_sha256": checksum,
        }
        first = directory / f"{phase}-runtime.json"
        if first.exists():
            verify_runtime(read_json(first), observation)
            number = len(list(directory.glob(f"{phase}-observation-*.json"))) + 1
            save(directory / f"{phase}-observation-{number:03d}.json", observation)
        else:
            save(first, observation)
        return observation
    finally:
        server.close()


def run_phase(plan, phase, directory, dispatch, *, verify_before=None):
    """Persist each start before dispatch; replay and bounded stopping are shared."""
    with exclusive(directory):
        state = audit(plan, directory)
        if next_phase(plan, state) != phase:
            raise ValueError("requested phase is not the next permitted phase")
        if verify_before:
            verify_before()
        queue = queue_for(plan)
        while next_phase(plan, state) == phase:
            model, case = queue[state["next_index"]]
            wire = wire_for(plan, model, case)
            serial = len(state["attempts"]) + 1
            start = {
                "phase": phase,
                "item_id": case["item_id"],
                "number": state["next_number"],
                "plan_sha256": plan["sha256"],
                "wire_sha256": digest(wire),
                "started_at": now(),
            }
            save(directory / f"{serial:03d}-start.json", start)
            began = time.monotonic()
            raw, error = dispatch(model, case, wire)
            result = {
                "start_sha256": digest(start),
                "raw_response": raw,
                "error": error,
                "judgment": parse(raw, model["model"]),
                "completed_at": now(),
                "seconds": time.monotonic() - began,
            }
            result["sha256"] = digest(result)
            save(directory / f"{serial:03d}-result.json", result)
            print(
                json.dumps(
                    {
                        "attempt": serial,
                        "phase": phase,
                        "item_id": case["item_id"],
                        "valid": result["judgment"] is not None,
                    }
                ),
                flush=True,
            )
            state = audit(plan, directory)
        return state


def comparison_report(plan, state, reference):
    if reference["sha256"] != plan["human_reference_sha256"]:
        raise ValueError("comparison human reference differs")
    labels = {label["item_id"]: label["decisions"] for label in reference["labels"]}
    reports = {}
    for phase in PHASES:
        judged = state["successful"][phase]
        attempts = [a for a in state["attempts"] if a["start"]["phase"] == phase]
        initial = [a for a in attempts if a["start"]["number"] == 1]
        dimensions = {}
        for d in DIMENSIONS:
            dimensions[d] = {
                "matching": sum(j[d]["decision"] == labels[i][d] for i, j in judged.items()),
                "compared": len(judged),
                "selected": len(plan["cases"]),
                "false_approvals": sum(
                    j[d]["decision"] == 1 and labels[i][d] == 0 for i, j in judged.items()
                ),
                "false_rejections": sum(
                    j[d]["decision"] == 0 and labels[i][d] == 1 for i, j in judged.items()
                ),
            }
        reports[phase] = {
            "starts": len(attempts),
            "selected": len(plan["cases"]),
            "initial_started": len(initial),
            "initial_valid": sum(a["result"]["judgment"] is not None for a in initial),
            "valid_cases": len(judged),
            "unresolved": len(plan["cases"]) - len(judged),
            "retry_starts": len(attempts) - len(initial),
            "dimensions": dimensions,
            "seconds": sum(a["result"]["seconds"] for a in attempts),
        }
    return {
        "purpose": "Fresh authored confirmation; not assessed calibration or automatic selection",
        "plan_sha256": plan["sha256"],
        "human_reference_sha256": reference["sha256"],
        "starts": len(state["attempts"]),
        "cumulative_starts": plan["prior_starts"] + len(state["attempts"]),
        "protocol_amendment": state.get("external_interruption_recovery"),
        "models": reports,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("prepare", "validate", "preflight", "execute", "report", "recover")
    )
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--candidate-model")
    parser.add_argument("--comparator-model")
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--phase", choices=PHASES)
    parser.add_argument("--incident", type=Path)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8081/v1")
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            if args.plan.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
                raise ValueError("confirmation plan must stay outside the repository")
            plan = make_plan(
                args.packet,
                args.manifest_sha256,
                args.review,
                {"candidate": args.candidate_model, "comparator": args.comparator_model},
            )
            save(args.plan, plan)
            print(json.dumps({"plan_sha256": plan["sha256"], "model_requests": 0}))
            return 0
        plan = load_plan(args.plan, args.packet, args.review)
        if args.action == "validate":
            if args.phase:
                if args.directory is None:
                    raise ValueError("phase validation requires a ledger directory")
                if args.directory.exists():
                    if next_phase(plan, audit(plan, args.directory)) != args.phase:
                        raise ValueError("requested phase is not the next permitted phase")
                elif args.phase != "candidate":
                    raise ValueError("candidate phase must start the shared ledger")
            print(json.dumps({"plan_sha256": plan["sha256"], "review_verified": True}))
            return 0
        if args.directory is None:
            raise ValueError("ledger directory required")
        if args.action == "recover":
            if args.incident is None:
                raise ValueError("attributed incident file required")
            receipt = record_external_recovery(plan, args.directory, read_json(args.incident))
            print(json.dumps({"recovery_sha256": receipt["sha256"], "model_requests": 0}))
            return 0
        if args.action == "report":
            reference = load_review(args.packet, plan["packet_manifest_sha256"], args.review)
            print(
                json.dumps(
                    comparison_report(plan, audit(plan, args.directory), reference), indent=2
                )
            )
            return 0
        if args.phase is None:
            raise ValueError("model phase required")
        loopback_url(args.endpoint)
        if not args.directory.exists():
            if args.phase != "candidate":
                raise ValueError("candidate phase must start the shared ledger")
            initialize(plan, args.directory)

        def verify():
            load_plan(args.plan, args.packet, args.review)
            prepare_runtime(plan, args.phase, args.directory, args.endpoint)

        if args.action == "preflight":
            with exclusive(args.directory):
                if next_phase(plan, audit(plan, args.directory)) != args.phase:
                    raise ValueError("requested phase is not the next permitted phase")
                verify()
            return 0

        def dispatch(model, case, wire):
            transport = VerifiedTransport(wire)
            with client_for(plan, model, args.endpoint, transport) as client:
                result = client.generate(case["messages"])
            if transport.calls != 1:
                raise ValueError("no verified dispatch; preserve unknown start")
            return result.raw_response, result.error

        state = run_phase(plan, args.phase, args.directory, dispatch, verify_before=verify)
        return 0 if len(state["successful"][args.phase]) == len(plan["cases"]) else 1
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as exc:
        print(f"Confirmation stopped: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
