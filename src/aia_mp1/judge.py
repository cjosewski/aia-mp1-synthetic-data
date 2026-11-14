"""Independent local judge calls with bounded, resumable attempt evidence."""

import json
from pathlib import Path
from typing import Literal

from pydantic import Field

from .assessment import (
    exclusive,
    item_identity,
    load_assessment,
    read_json,
    read_text,
    save_new,
)
from .config import RunConfig
from .evaluation_schemas import Judgment
from .generate import implementation_identity
from .schemas import NonBlank
from .tracing import (
    append_record,
    artifact_hashes,
    digest,
    now,
    read_records,
    run_directory,
    write_checkpoint,
)


class JudgeConfig(RunConfig):
    temperature: float = Field(default=0.1, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1, le=8192)
    max_attempts: int = Field(default=2, ge=1, le=5)
    prompt_path: NonBlank = "prompts/judge-v1.md"
    prompt_variant: NonBlank = "judge-v1"
    stronger_model_basis: NonBlank | None = None
    qualification_path: NonBlank | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


def judge_directory(assessment_dir: Path, judge_run_id: str) -> Path:
    root = assessment_dir / "judges"
    if root.is_symlink():
        raise ValueError("symlink judge root is not supported")
    return run_directory(root, judge_run_id)


def messages_for(prompt: str, rubric: dict, record: dict) -> list[dict]:
    content = {"untrusted_item": record["item"]}
    if record.get("reference_context"):
        content["untrusted_reference_context"] = record["reference_context"]
    return [
        {"role": "system", "content": prompt + "\nRubric:\n" + json.dumps(rubric)},
        {
            "role": "user",
            "content": json.dumps(content, ensure_ascii=False),
        },
    ]


def validate_judge(directory: Path, assessment: dict, records: list[dict], rubric: dict):
    manifest = read_json(directory / "manifest.json")
    if manifest["assessment_sha256"] != assessment["manifest_sha256"]:
        raise ValueError("judge belongs to a different assessment")
    if manifest["judge_run_id"] != directory.name:
        raise ValueError("judge run identity differs")
    if manifest["fingerprint"] != digest(manifest["identity"]):
        raise ValueError("judge settings identity changed")
    if assessment["assessment_eligible"]:
        from .human_reference import load_reference

        reference = load_reference(directory.parent.parent, assessment, records)
        if manifest["identity"].get("human_reference_sha256") != reference["sha256"]:
            raise ValueError("judge independent human reference differs")
    if manifest["identity"]["assessment_sha256"] != assessment["manifest_sha256"]:
        raise ValueError("judge fingerprint has a different assessment")
    prompt = read_text(directory / "prompt.md")
    if digest(prompt) != manifest["identity"]["prompt_sha256"]:
        raise ValueError("judge prompt changed")
    for name in ("events.jsonl", "attempts.jsonl"):
        read_text(directory / name)
        if artifact_hashes(directory).get(name) != manifest["artifacts_sha256"].get(name):
            raise ValueError("judge ledger differs from its checkpoint; preserve for inspection")
    records_by_id = {r["item_id"]: r for r in records}
    events = read_records(directory / "events.jsonl")
    attempts = read_records(directory / "attempts.jsonl")
    event_ids, item_events, successful = {}, {}, {}
    for event in events:
        item_id = event["item_id"]
        if item_id not in records_by_id or event["attempt_id"] in event_ids:
            raise ValueError("foreign or duplicate judge request")
        record = records_by_id[item_id]
        previous = item_events.get(item_id, [])
        number = len(previous) + 1
        if (
            event["attempt_number"] != number
            or number > manifest["identity"]["settings"]["max_attempts"]
            or event["attempt_id"] != f"{directory.name}:{item_id}:{number}"
            or event["parent_attempt_id"] != (previous[-1]["attempt_id"] if previous else None)
            or event["judge_run_id"] != directory.name
            or event["messages_sha256"]
            != digest({"messages": messages_for(prompt, rubric, record)})
            or any(event[k] != v for k, v in item_identity(assessment, record).items())
        ):
            raise ValueError("judge request lineage, budget or input differs")
        event_ids[event["attempt_id"]] = event
        item_events.setdefault(item_id, []).append(event)
    completed = set()
    for attempt in attempts:
        attempt_id = attempt["attempt_id"]
        event = event_ids.get(attempt_id)
        if event is None or attempt_id in completed:
            raise ValueError("judge completion needs a unique request start")
        if any(attempt[k] != v for k, v in event.items()):
            raise ValueError("judge completion differs from its request")
        completed.add(attempt_id)
        if type(attempt["valid"]) is not bool:
            raise ValueError("judge validity must be boolean")
        item_id = attempt["item_id"]
        if attempt["valid"]:
            Judgment.model_validate(attempt["judgment"])
            if item_id in successful or attempt["error"] is not None:
                raise ValueError("duplicate or inconsistent successful judge result")
            if item_events[item_id][-1]["attempt_id"] != attempt_id:
                raise ValueError("judge retried after success")
            successful[item_id] = attempt
        elif attempt["judgment"] is not None or not attempt["error_type"]:
            raise ValueError("failed judge attempt has inconsistent result")
    complete = len(successful) == len(records)
    if manifest["status"] == "complete" and not complete:
        raise ValueError("judge completion claim differs from its ledger")
    return manifest, events, attempts, successful


def judge_run(
    root: Path,
    assessment_id: str,
    judge_run_id: str,
    config: JudgeConfig,
    client,
    *,
    resume: bool = False,
) -> dict:
    parent, assessment, records, rubric = load_assessment(root, assessment_id)
    if config.temperature >= assessment["generator_temperature"]:
        raise ValueError("judge temperature must be lower than the generator temperature")
    if assessment["assessment_eligible"] and (
        config.model == assessment["generator_model"] or not config.stronger_model_basis
    ):
        raise ValueError("assessed judging needs a distinct stronger model and selection basis")
    prompt = read_text(Path(config.prompt_path))
    if not prompt.strip():
        raise ValueError("judge prompt cannot be empty")
    settings = config.public_settings()
    identity = {
        "assessment_sha256": assessment["manifest_sha256"],
        "settings": settings,
        "prompt_sha256": digest(prompt),
        "implementation": implementation_identity(),
    }
    if assessment["assessment_eligible"]:
        from .human_reference import load_reference
        from .qualification import validate_qualification

        reference = load_reference(parent, assessment, records)
        qualification = validate_qualification(config, assessment)
        if config.max_attempts != 2:
            raise ValueError("assessed judge budget is two attempts per item")
        identity |= {"human_reference_sha256": reference["sha256"], "qualification": qualification}
    directory = judge_directory(parent, judge_run_id)
    if not resume:
        with exclusive(parent):
            if (
                assessment["assessment_eligible"]
                and (parent / "judges").exists()
                and len(list((parent / "judges").iterdir())) >= 3
            ):
                raise ValueError("assessed judge budget is three run versions")
            directory.mkdir(parents=True, exist_ok=False)
            for name in ("events.jsonl", "attempts.jsonl"):
                (directory / name).touch(exist_ok=False)
            with (directory / "prompt.md").open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(prompt)
            manifest = {
                "schema_version": "1",
                "judge_run_id": judge_run_id,
                "assessment_sha256": assessment["manifest_sha256"],
                "created_at": now(),
                "status": "running",
                "identity": identity,
                "fingerprint": digest(identity),
                "artifacts_sha256": artifact_hashes(directory),
            }
            save_new(directory / "manifest.json", manifest)
    with exclusive(directory):
        manifest, events, attempts, successful = validate_judge(
            directory, assessment, records, rubric
        )
        if manifest["fingerprint"] != digest(identity):
            raise ValueError(
                "resume requires identical judge settings, prompt, code and assessment"
            )
        if manifest["status"] == "complete":
            raise ValueError("completed judge runs are immutable")
        try:
            for record in records:
                item_id = record["item_id"]
                if item_id in successful:
                    continue
                previous = [e for e in events if e["item_id"] == item_id]
                for number in range(len(previous) + 1, config.max_attempts + 1):
                    messages = messages_for(prompt, rubric, record)
                    event = item_identity(assessment, record) | {
                        "judge_run_id": judge_run_id,
                        "attempt_id": f"{judge_run_id}:{item_id}:{number}",
                        "attempt_number": number,
                        "parent_attempt_id": previous[-1]["attempt_id"] if previous else None,
                        "started_at": now(),
                        "messages_sha256": digest({"messages": messages}),
                    }
                    append_record(directory / "events.jsonl", event)
                    events.append(event)
                    previous.append(event)
                    manifest["artifacts_sha256"] = artifact_hashes(directory)
                    write_checkpoint(directory / "manifest.json", manifest)
                    result = client.generate(messages)
                    judgment = None
                    model_matches = (
                        not assessment["assessment_eligible"]
                        or result.response_model == config.model
                    )
                    if result.item is not None and model_matches:
                        judgment = Judgment.model_validate(
                            result.item.model_dump(mode="json")
                        ).model_dump(mode="json")
                    attempt = event | {
                        "completed_at": now(),
                        "valid": judgment is not None,
                        "judgment": judgment,
                        "raw_response": result.raw_response,
                        "error": result.error
                        if model_matches
                        else "reported judge model differs from selected model",
                        "error_type": result.error_type
                        if model_matches
                        else "ModelIdentityMismatch",
                        "response_model": result.response_model,
                    }
                    append_record(directory / "attempts.jsonl", attempt)
                    attempts.append(attempt)
                    manifest["artifacts_sha256"] = artifact_hashes(directory)
                    write_checkpoint(directory / "manifest.json", manifest)
                    if judgment is not None:
                        successful[item_id] = attempt
                        break
            manifest["status"] = "complete" if len(successful) == len(records) else "incomplete"
        except KeyboardInterrupt:
            manifest["status"] = "interrupted"
            raise
        finally:
            manifest["artifacts_sha256"] = artifact_hashes(directory)
            manifest["updated_at"] = now()
            write_checkpoint(directory / "manifest.json", manifest)
    return judge_status(root, assessment_id, judge_run_id)


def judge_status(root: Path, assessment_id: str, judge_run_id: str) -> dict:
    parent, assessment, records, rubric = load_assessment(root, assessment_id)
    directory = judge_directory(parent, judge_run_id)
    with exclusive(directory):
        manifest, events, attempts, successful = validate_judge(
            directory, assessment, records, rubric
        )
        completed = {a["attempt_id"] for a in attempts}
        generator_models = {r["model"] for r in records} | {assessment["generator_model"]}
        reported_models = {a["response_model"] for a in successful.values()}
        settings = manifest["identity"]["settings"]
        return {
            "judge_run_id": judge_run_id,
            "assessment_id": assessment_id,
            "status": manifest["status"],
            "assessment_eligible": assessment["assessment_eligible"],
            "population": len(records),
            "resolved": len(successful),
            "started_attempts": len(events),
            "completed_attempts": len(attempts),
            "unresolved_request_ids": [
                e["attempt_id"] for e in events if e["attempt_id"] not in completed
            ],
            "unresolved_item_ids": [
                r["item_id"] for r in records if r["item_id"] not in successful
            ],
            "same_model_diagnostic": settings["model"] in generator_models
            or bool(generator_models & reported_models),
            "stronger_model_basis": settings.get("stronger_model_basis"),
            "reported_models": sorted(m for m in reported_models if m is not None),
        }
