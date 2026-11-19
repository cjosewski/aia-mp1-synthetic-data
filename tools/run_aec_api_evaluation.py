"""Judge the frozen AEC API-correctness packet and compare real blind ratings."""

import argparse
import json
import os
from pathlib import Path

from prepare_aec_api_evaluation import REVISIONS, ROOT, prepare

from aia_mp1.analysis import segments, worst_segment
from aia_mp1.assessment import exclusive, load_assessment, read_json, read_text, save_new
from aia_mp1.calibration import agreement
from aia_mp1.evaluation_schemas import Judgment
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.human_reference import load_reference
from aia_mp1.judge import JudgeConfig
from aia_mp1.model_client import InstructorClient
from aia_mp1.qualification import validate_qualification
from aia_mp1.tracing import (
    append_record,
    artifact_hashes,
    digest,
    now,
    read_records,
    write_checkpoint,
)


def replay(directory, requests, config):
    ledger = directory / "attempts.jsonl"
    manifest = read_json(directory / "manifest.json")
    if ledger.is_symlink() or artifact_hashes(directory) != manifest["artifacts_sha256"]:
        raise ValueError("Judge ledger differs from its checkpoint")
    rows = {row["item_id"]: row for row in requests}
    starts, finished, counts, decisions = {}, set(), {}, {}
    for event in read_records(ledger):
        item_id = event["item_id"]
        if item_id not in rows or event["messages_sha256"] != rows[item_id]["messages_sha256"]:
            raise ValueError("Unexpected judge input")
        attempt = event["attempt_id"]
        if event["kind"] == "start":
            number = counts.get(item_id, 0) + 1
            if (
                attempt != f"{item_id}:{number}"
                or item_id in decisions
                or number > config.max_attempts
            ):
                raise ValueError("Judge attempt sequence or budget differs")
            starts[attempt] = item_id
            counts[item_id] = number
        elif event["kind"] == "result":
            if starts.get(attempt) != item_id or attempt in finished:
                raise ValueError("Judge result has no unique request")
            finished.add(attempt)
            if event["valid"]:
                if event["response_model"] != config.model or item_id in decisions:
                    raise ValueError("Unexpected model or duplicate valid result")
                decisions[item_id] = Judgment.model_validate(event["judgment"]).model_dump()
            elif event["judgment"] is not None:
                raise ValueError("Invalid result contains a judgment")
        else:
            raise ValueError("Unknown judge event")
    return counts, decisions, sorted(starts.keys() - finished)


def record(directory, manifest, event):
    append_record(directory / "attempts.jsonl", event)
    manifest["artifacts_sha256"] = artifact_hashes(directory)
    write_checkpoint(directory / "manifest.json", manifest)


def run(root, resume, revision="v1"):
    packet, inputs = prepare(root, revision)
    requests = read_records(packet / "requests.jsonl")
    parent, assessment, records, _ = load_assessment(root, inputs["source_assessment"])
    reference = load_reference(parent, assessment, records)
    config = JudgeConfig.model_validate(read_json(root / "judge-preparation-v1/judge.json"))
    qualification = validate_qualification(config, assessment)
    if (
        config.base_url != "http://127.0.0.1:18082/v1"
        or config.max_attempts != 2
        or config.temperature >= assessment["generator_temperature"]
    ):
        raise ValueError("Local endpoint, judge budget or temperature differs")
    settings = config.public_settings() | {
        "prompt_path": str(packet / "prompt.md"),
        "prompt_variant": inputs["protocol"]
        if revision == "v1"
        else f"aec-api-correctness-{revision}",
    }
    identity = {
        "packet_sha256": digest(inputs),
        "settings": settings,
        "qualification_sha256": qualification["sha256"],
        "runner_sha256": digest(read_text(Path(__file__))),
        "human_reference_sha256": reference["sha256"],
    }
    directory = root.resolve() / f"api-correctness-judge-{revision}"
    if directory.is_symlink():
        raise ValueError("Symlink judge directory")
    if not resume:
        directory.mkdir(exist_ok=False)
        (directory / "attempts.jsonl").touch(exist_ok=False)
        save_new(
            directory / "manifest.json",
            {
                "protocol": inputs["protocol"],
                "status": "running",
                "created_at": now(),
                "identity": identity,
                "artifacts_sha256": artifact_hashes(directory),
            },
        )
    with exclusive(directory):
        manifest = read_json(directory / "manifest.json")
        if manifest["identity"] != identity:
            raise ValueError("Resume requires identical inputs, runner and judge")
        counts, decisions, _ = replay(directory, requests, config)
        if (directory / "report.json").exists():
            raise ValueError("A report already exists for this run")
        key = os.environ.get(config.api_key_env) or "local-only-placeholder"
        server = LocalServer(config.base_url, key)
        try:
            with InstructorClient(
                base_url=config.base_url,
                model=config.model,
                api_key=key,
                mode=config.mode,
                timeout_seconds=config.timeout_seconds,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                response_model=Judgment,
                reasoning_effort=config.reasoning_effort,
            ) as client:
                for row in requests:
                    item_id = row["item_id"]
                    if item_id in decisions:
                        continue
                    for number in range(counts.get(item_id, 0) + 1, config.max_attempts + 1):
                        if server.json("/health").get("status") != "ok" or [
                            m["id"] for m in server.json("/v1/models")["data"]
                        ] != [config.model]:
                            raise RuntimeError("Endpoint health or served model differs")
                        attempt = {
                            "attempt_id": f"{item_id}:{number}",
                            "item_id": item_id,
                            "messages_sha256": row["messages_sha256"],
                        }
                        record(
                            directory, manifest, attempt | {"kind": "start", "started_at": now()}
                        )
                        result = client.generate(row["messages"])
                        valid = result.item is not None and result.response_model == config.model
                        record(
                            directory,
                            manifest,
                            attempt
                            | {
                                "kind": "result",
                                "completed_at": now(),
                                "valid": valid,
                                "judgment": result.item.model_dump(mode="json") if valid else None,
                                "response_model": result.response_model,
                                "raw_response": result.raw_response,
                                "error": result.error,
                                "error_type": result.error_type,
                            },
                        )
                        print(item_id, "attempt", number, "valid", valid, flush=True)
                        if valid:
                            break
                        if result.response_model not in (
                            None,
                            config.model,
                        ) or result.error_type in {
                            "AuthenticationError",
                            "PermissionDeniedError",
                            "APIConnectionError",
                        }:
                            raise RuntimeError("Transport, authentication or served model changed")
        except BaseException:
            manifest["status"] = "interrupted"
            write_checkpoint(directory / "manifest.json", manifest)
            raise
        finally:
            server.close()
        _, decisions, unknown = replay(directory, requests, config)
        summary = agreement(records, assessment["selected_ids"], reference["labels"], decisions)
        meets = all(row["threshold_met"] for row in summary["dimensions"].values())
        metrics = segments(
            records,
            {key: Judgment.model_validate(value).decisions() for key, value in decisions.items()},
        )
        report = {
            "rubric_version": inputs["protocol"],
            "created_at": now(),
            "identity": identity,
            "artifacts_sha256": manifest["artifacts_sha256"],
            "summary": summary,
            "unknown_outcomes": unknown,
            "segments": metrics,
            "worst_segment": worst_segment(metrics),
            "meets_per_dimension_gate": summary["coverage_complete"] and meets and not unknown,
            "agreement_basis": "Frozen blind ratings and reviewer's explicit API-correctness definition of D3.",
        }
        save_new(directory / "report.json", report)
        manifest["status"] = "complete" if len(decisions) == len(records) else "incomplete"
        manifest["report_sha256"] = digest(report)
        write_checkpoint(directory / "manifest.json", manifest)
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--revision", choices=REVISIONS, default="v1")
    args = parser.parse_args()
    report = run(ROOT, args.resume, args.revision)
    print(json.dumps(report["summary"]["dimensions"]))
