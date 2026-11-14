"""Bounded canonical known-case screens; outputs are not automatic qualification."""

import argparse
import copy
import hashlib
import json
import os
import platform
import time
from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict

from .assessment import exclusive, read_json
from .evaluation_schemas import DimensionJudgment, Judgment
from .factcheck_transport import LocalServer, VerifiedTransport
from .model_client import InstructorClient
from .tracing import digest, now

MODEL_SHA = "582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d"
SETTINGS = {
    "mode": "json",
    "temperature": 0.1,
    "max_tokens": 8192,
    "timeout_seconds": 300.0,
    "reasoning_effort": "high",
}
QWEN_SETTINGS = {key: value for key, value in SETTINGS.items() if key != "reasoning_effort"}
QWEN_FILES = [
    {
        "name": "Qwen_Qwen3.5-122B-A10B-Q4_K_M-00001-of-00002.gguf",
        "bytes": 39925205312,
        "sha256": "e6f74fc4e5ff7da7888cb0a135f9fafbf1265b748f5db9f72c7794061a333843",
    },
    {
        "name": "Qwen_Qwen3.5-122B-A10B-Q4_K_M-00002-of-00002.gguf",
        "bytes": 37691305984,
        "sha256": "1c07a0f86507ad661830a2c317f9c4450e40a836bf9133225926054ab0722316",
    },
]
QWEN_MODEL_SHA = digest(QWEN_FILES)


def is_qwen(plan):
    return plan["protocol"] in {
        "qwen35-canonical-development",
        "qwen35-v4-development",
        "qwen35-v10-development",
        "qwen35-v13-development",
    }


class CoreJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    D1: DimensionJudgment
    D2: DimensionJudgment
    D3: DimensionJudgment
    D4: DimensionJudgment
    D6: DimensionJudgment


class ContextJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    D5: DimensionJudgment


def schema_for(plan, case):
    if plan["protocol"] == "v11-isolated-development":
        return {"core": CoreJudgment, "context": ContextJudgment}[case["stage"]]
    return Judgment


def schema_identity(plan):
    if plan["protocol"] == "v11-isolated-development":
        return digest(
            {
                "core": CoreJudgment.model_json_schema(),
                "context": ContextJudgment.model_json_schema(),
            }
        )
    return digest(Judgment.model_json_schema())


def save(path: Path, value: dict):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())


def validate_plan(plan):
    allocations = {
        "v9-canonical-development": (99, 20),
        "v10-canonical-development": (109, 20),
        "v11-isolated-development": (119, 40),
        "v12-presentation-development": (139, 20),
        "qwen35-canonical-development": (149, 20),
        "qwen35-v4-development": (159, 20),
        "qwen35-v10-development": (169, 20),
        "qwen35-v13-development": (180, 20),
    }
    isolated = plan["protocol"] == "v11-isolated-development"
    expected_ids = [f"qualification-v1-{i:02d}" for i in range(1, 11)]
    if isolated:
        expected_ids = [f"{item}:{stage}" for item in expected_ids for stage in ("core", "context")]
    if (
        plan["protocol"] not in allocations
        or (plan["prior_starts"], plan["max_starts"]) != allocations[plan["protocol"]]
        or plan["settings"] != (QWEN_SETTINGS if is_qwen(plan) else SETTINGS)
        or plan["model_sha256"] != (QWEN_MODEL_SHA if is_qwen(plan) else MODEL_SHA)
        or [c["item_id"] for c in plan["cases"]] != expected_ids
    ):
        raise ValueError("canonical development protocol, identities or budget changed")
    for case in plan["cases"]:
        messages = case["messages"]
        if (
            len(messages) != 2
            or messages[0]["role"] != "system"
            or messages[1]["role"] != "user"
            or set(json.loads(messages[1]["content"]))
            != {"untrusted_item", "untrusted_reference_context"}
        ):
            raise ValueError("development input contains unexpected roles or fields")
        if plan["protocol"] == "v12-presentation-development" and messages[1][
            "content"
        ] != json.dumps(json.loads(messages[1]["content"]), ensure_ascii=False, indent=2):
            raise ValueError("V12 requires the frozen readable JSON serialization")
    if isolated:
        for core, context in zip(plan["cases"][::2], plan["cases"][1::2]):
            for case, stage in ((core, "core"), (context, "context")):
                if (
                    case["stage"] != stage
                    or case["item_id"] != f"{case['original_item_id']}:{stage}"
                ):
                    raise ValueError("isolated stage identity differs")
            if core["messages"][1] != context["messages"][1]:
                raise ValueError("isolated calls must receive identical original input")


def client_for(plan, endpoint, transport=None, *, case=None):
    return InstructorClient(
        base_url=endpoint,
        model=plan["model"],
        api_key="local-development",
        response_model=schema_for(plan, case),
        _transport=transport,
        **plan["settings"],
    )


def wire_for(plan, case):
    captured = []

    def capture(request):
        captured.append(json.loads(request.content))
        return httpx.Response(400, json={"error": {"message": "Offline serialization"}})

    with client_for(
        plan, "http://127.0.0.1:1/v1", httpx.MockTransport(capture), case=case
    ) as client:
        client.generate(case["messages"])
    if len(captured) != 1 or (
        ("reasoning_effort" in captured[0])
        if is_qwen(plan)
        else captured[0].get("reasoning_effort") != "high"
    ):
        raise ValueError("exact model-specific request serialization failed")
    return captured[0]


def parse(raw, model, response_model=Judgment):
    try:
        if raw["model"] != model or len(raw["choices"]) != 1:
            return None
        choice = raw["choices"][0]
        if choice["finish_reason"] != "stop":
            return None
        return response_model.model_validate_json(choice["message"]["content"]).model_dump()
    except (ValueError, KeyError, TypeError):
        return None


def audit(plan, directory):
    validate_plan(plan)
    manifest = read_json(directory / "manifest.json")
    if manifest["plan_sha256"] != digest(plan) or manifest["schema_sha256"] != schema_identity(
        plan
    ):
        raise ValueError("development identity changed")
    attempts, successful, failures = [], {}, 0
    starts = sorted(directory.glob("*-start.json"))
    if len(starts) > plan["max_starts"]:
        raise ValueError("development request budget exceeded")
    expected_case, number = 0, 1
    for start_path in starts:
        if failures >= 2 or expected_case >= len(plan["cases"]):
            raise ValueError("request after stop boundary")
        case = plan["cases"][expected_case]
        start = read_json(start_path)
        if (
            start_path.name != f"{len(attempts) + 1:03d}-start.json"
            or start["case_id"] != case["item_id"]
            or start["number"] != number
            or start["plan_sha256"] != digest(plan)
            or start["wire_sha256"] != digest(wire_for(plan, case))
        ):
            raise ValueError("development request order or input differs")
        result_path = start_path.with_name(start_path.name.replace("-start", "-result"))
        if not result_path.exists():
            raise ValueError("unknown request outcome; preserve for inspection, no retry")
        result = read_json(result_path)
        if result["start_sha256"] != digest(start) or result["sha256"] != digest(
            {k: v for k, v in result.items() if k != "sha256"}
        ):
            raise ValueError("development result lineage changed")
        judgment = parse(result["raw_response"], plan["model"], schema_for(plan, case))
        if result["judgment"] != judgment:
            raise ValueError("stored judgment differs from raw completion")
        attempts.append(result)
        if judgment:
            successful[case["item_id"]] = judgment
            failures = 0
            expected_case += 1
            number = 1
        else:
            failures += 1
            number += 1
            if number > 2:
                expected_case += 1
                number = 1
    if len(list(directory.glob("*-result.json"))) != len(starts):
        raise ValueError("orphan development result")
    return {
        "attempts": attempts,
        "successful": successful,
        "consecutive_failures": failures,
        "next_case": expected_case,
        "next_number": number,
    }


def compose(plan, state):
    """A canonical result requires both independently completed stage outputs."""
    if plan["protocol"] != "v11-isolated-development":
        return state["successful"]
    combined = {}
    for case in plan["cases"][::2]:
        item = case["original_item_id"]
        core = state["successful"].get(f"{item}:core")
        context = state["successful"].get(f"{item}:context")
        if core is not None and context is not None:
            combined[item] = Judgment.model_validate(
                CoreJudgment.model_validate(core).model_dump()
                | ContextJudgment.model_validate(context).model_dump()
            ).model_dump()
    return combined


def run(plan, directory, dispatch):
    """Every dispatch has a fsynced start; resume cannot bypass failures or unknowns."""
    with exclusive(directory):
        state = audit(plan, directory)
        while (
            state["next_case"] < len(plan["cases"])
            and state["consecutive_failures"] < 2
            and len(state["attempts"]) < plan["max_starts"]
        ):
            case = plan["cases"][state["next_case"]]
            wire = wire_for(plan, case)
            serial = len(state["attempts"]) + 1
            start = {
                "case_id": case["item_id"],
                "number": state["next_number"],
                "plan_sha256": digest(plan),
                "wire_sha256": digest(wire),
                "started_at": now(),
            }
            save(directory / f"{serial:03d}-start.json", start)
            began = time.monotonic()
            raw, error = dispatch(case, wire)
            result = {
                "start_sha256": digest(start),
                "raw_response": raw,
                "error": error,
                "judgment": parse(raw, plan["model"], schema_for(plan, case)),
                "completed_at": now(),
                "seconds": time.monotonic() - began,
            }
            result["sha256"] = digest(result)
            save(directory / f"{serial:03d}-result.json", result)
            print(
                json.dumps(
                    {
                        "attempt": serial,
                        "item_id": case["item_id"],
                        "valid": result["judgment"] is not None,
                        "seconds": result["seconds"],
                    }
                ),
                flush=True,
            )
            state = audit(plan, directory)
        return state


def weight_identity(plan, weight):
    if is_qwen(plan):
        if weight.name != QWEN_FILES[0]["name"]:
            raise ValueError("Qwen first shard identity differs")
        observed = []
        for expected in QWEN_FILES:
            shard = weight.parent / expected["name"]
            with shard.open("rb") as stream:
                sha = hashlib.file_digest(stream, "sha256").hexdigest()
            observed.append({"name": shard.name, "bytes": shard.stat().st_size, "sha256": sha})
        if observed != QWEN_FILES:
            raise ValueError("Qwen shard size or checksum differs")
        checksum = digest(observed)
    else:
        with weight.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    if checksum != plan["model_sha256"]:
        raise ValueError("served weight checksum differs")
    return checksum


def validate_template(plan, rendered):
    if is_qwen(plan):
        if not rendered.rstrip().endswith("<|im_start|>assistant\n<think>"):
            raise ValueError("Qwen template did not open the thinking channel")
    elif "Reasoning: high" not in rendered:
        raise ValueError("chat template did not apply high reasoning effort")


def prepare_runtime(plan, directory, endpoint):
    validate_plan(plan)
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("native Apple Silicon Mac required")
    server = LocalServer(endpoint, "local-development")
    try:
        props = server.json("/props")
        models = server.json("/v1/models")["data"]
        if (
            props["build_info"] != plan["build_info"]
            or props["total_slots"] != 1
            or props["default_generation_settings"]["n_ctx"] != 16384
            or props["model_path"] != plan["model"]
            or len(models) != 1
            or models[0]["id"] != plan["model"]
            or server.json("/health")["status"] != "ok"
        ):
            raise ValueError("Mac runtime differs from frozen plan")
        weight = Path(props["model_path"])
        checksum = weight_identity(plan, weight)
        checks = []
        for case in plan["cases"]:
            wire = wire_for(plan, case)
            rendered = server.json("/apply-template", wire)["prompt"]
            validate_template(plan, rendered)
            check = server.token_fit(wire, 16384)
            if not check["fits"]:
                raise ValueError("exact wire input plus output allowance exceeds context")
            checks.append({"item_id": case["item_id"], **check})
        manifest = {
            "plan_sha256": digest(plan),
            "schema_sha256": schema_identity(plan),
            "properties": props,
            "token_checks": checks,
            "python": platform.python_version(),
            "machine": platform.node(),
            "weight_sha256": checksum,
        }
        if (directory / "manifest.json").exists():
            verify_runtime(read_json(directory / "manifest.json"), manifest)
            number = len(list(directory.glob("runtime-observation-*.json"))) + 1
            save(directory / f"runtime-observation-{number:03d}.json", manifest)
        else:
            directory.mkdir(parents=True, exist_ok=False)
            save(directory / "manifest.json", manifest)
        return manifest
    finally:
        server.close()


def verify_runtime(expected, observed):
    """The server's random media marker is unused in these text-only requests.

    Preserve both full observations, but compare every other field, including
    rendered prompt hashes and token counts. No sampling/template drift is allowed.
    """
    left, right = copy.deepcopy(expected), copy.deepcopy(observed)
    for value in (left, right):
        value["properties"].pop("media_marker", None)
    if left != right:
        raise ValueError("runtime changed on resume")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8081/v1")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    plan = read_json(args.plan)
    prepare_runtime(plan, args.directory, args.endpoint)
    if not args.execute:
        return 0

    def dispatch(case, wire):
        transport = VerifiedTransport(wire)
        with client_for(plan, args.endpoint, transport, case=case) as client:
            result = client.generate(case["messages"])
        if transport.calls != 1:
            raise ValueError("no verified dispatch; preserve unknown start")
        return result.raw_response, result.error

    state = run(plan, args.directory, dispatch)
    return 0 if len(state["successful"]) == len(plan["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
