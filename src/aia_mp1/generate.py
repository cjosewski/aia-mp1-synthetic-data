"""Bounded generation with immutable attempts, resumable slots and honest denominators."""

import importlib.metadata
import json
import platform
import uuid
from pathlib import Path
from typing import Protocol

from .config import RunConfig
from .model_client import AttemptResult
from .schemas import CATEGORIES, GeneratedItem
from .tracing import (
    append_record,
    artifact_hashes,
    digest,
    now,
    read_records,
    run_directory,
    write_checkpoint,
)


class ModelClient(Protocol):
    def generate(self, messages: list[dict[str, str]]) -> AttemptResult: ...


def implementation_identity() -> dict:
    root = Path(__file__).resolve().parents[2]
    files = sorted((root / "src" / "aia_mp1").glob("*.py"))
    files += [root / "pyproject.toml", root / "uv.lock"]
    hashes = {
        str(path.relative_to(root)): digest(path.read_text()) for path in files if path.exists()
    }
    return {"source_files": hashes, "source_tree_sha256": digest(hashes)}


def generation_metrics(
    count: int, starts: list[dict], attempts: list[dict], records: list[dict]
) -> dict:
    first = [attempt for attempt in attempts if attempt["attempt_number"] == 1]
    successes = sum(attempt["schema_valid"] for attempt in attempts)
    completed_ids = {attempt["attempt_id"] for attempt in attempts}
    unknown = [event["attempt_id"] for event in starts if event["attempt_id"] not in completed_ids]
    return {
        "planned_slots": count,
        "attempted_slots": len({event["slot"] for event in starts}),
        "started_attempts": len(starts),
        "completed_attempts": len(attempts),
        "unresolved_attempt_ids": unknown,
        "initial_attempt_valid_count": sum(attempt["schema_valid"] for attempt in first),
        "initial_attempt_schema_pass_rate": sum(attempt["schema_valid"] for attempt in first)
        / count,
        "initial_attempt_denominator": "all planned generation slots; unobserved responses are not passes",
        "all_completed_attempts_schema_pass_rate": successes / len(attempts) if attempts else None,
        "successful_retries": sum(
            attempt["schema_valid"] and attempt["attempt_number"] > 1 for attempt in attempts
        ),
        "schema_valid_items": len(records),
        "unresolved_slots": count - len(records),
        "quality_status": "pending",
        "course_acceptance": "not_evaluated",
    }


def validate_evidence(manifest, directory, starts, attempts, records):
    """Require unchanged checkpoints and data that agrees with successful attempts."""
    expected = manifest.get("artifacts_sha256", {})
    actual = artifact_hashes(directory)
    for name in ("events.jsonl", "attempts.jsonl", "data.jsonl"):
        if name not in expected or actual.get(name) != expected[name]:
            raise ValueError(f"changed or missing {name}; preserve the run for inspection")
    event_ids = {}
    slots = {}
    for event in starts:
        slot = event["slot"]
        if type(slot) is not int or not 0 <= slot < manifest["count"]:
            raise ValueError("invalid persisted generation slot")
        previous = slots.get(slot, [])
        if event["attempt_id"] in event_ids or event["run_id"] != manifest["run_id"]:
            raise ValueError("invalid or duplicate attempt identity")
        if (
            event["category"] != CATEGORIES[slot % len(CATEGORIES)]
            or event["item_id"] != f"{manifest['run_id']}-item-{slot + 1:04d}"
        ):
            raise ValueError("persisted slot provenance differs from its plan")
        if (
            event["attempt_number"] != len(previous) + 1
            or event["attempt_number"] > manifest["settings"]["max_attempts"]
        ):
            raise ValueError("persisted retry budget is inconsistent")
        if event["parent_attempt_id"] != (previous[-1]["attempt_id"] if previous else None):
            raise ValueError("persisted retry lineage is inconsistent")
        if previous and event["trace_id"] != previous[0]["trace_id"]:
            raise ValueError("trace identity changed within a slot")
        event_ids[event["attempt_id"]] = event
        slots.setdefault(slot, []).append(event)
        if manifest["purpose"] != "smoke":
            from .sources import context_for, validate_pack

            pack = validate_pack(manifest["source_manifest"])
            context = context_for(pack, event["category"], slot // len(CATEGORIES))
            if event.get("reference_context") != context:
                raise ValueError("assessed request reference context differs")
            if event["input"][-1]["content"] != json.dumps(
                {"request": event["request"], "untrusted_reference_context": context},
                ensure_ascii=False,
            ):
                raise ValueError("assessed request does not contain its frozen context")
    completed_ids = set()
    successful = {}
    for attempt in attempts:
        start = event_ids.get(attempt["attempt_id"])
        if start is None or attempt["attempt_id"] in completed_ids:
            raise ValueError("completion is missing its unique request-start event")
        for key in (
            "run_id",
            "slot",
            "trace_id",
            "item_id",
            "parent_attempt_id",
            "attempt_number",
            "category",
        ):
            if attempt[key] != start[key]:
                raise ValueError("completion differs from its request-start provenance")
        completed_ids.add(attempt["attempt_id"])
        if attempt["schema_valid"]:
            record = GeneratedItem.model_validate(attempt["record"]).model_dump(mode="json")
            if record["item_id"] in successful:
                raise ValueError("multiple successful completions for one slot")
            for key in (
                "run_id",
                "trace_id",
                "item_id",
                "attempt_id",
                "parent_attempt_id",
                "category",
            ):
                if record[key] != attempt[key]:
                    raise ValueError("successful payload provenance differs from its attempt")
            successful[record["item_id"]] = record
            if manifest["purpose"] != "smoke" and (
                record.get("reference_context") != start["reference_context"]
                or record["source_refs"] != start["reference_context"]["task"]["source_refs"]
            ):
                raise ValueError("generated reference provenance differs from request")
        elif attempt.get("record") is not None:
            raise ValueError("failed attempt contains a successful payload")
    for record in records:
        validated = GeneratedItem.model_validate(record).model_dump(mode="json")
        if successful.get(validated["item_id"]) != validated:
            raise ValueError("data payload differs from its successful attempt")


def generate_run(
    config: RunConfig,
    prompt: str,
    sources: dict,
    *,
    count: int,
    run_id: str,
    client: ModelClient,
    resume: bool = False,
) -> dict:
    if type(count) is not int or count < 5 or count > 500 or count % 5:
        raise ValueError("count must be a multiple of five between 5 and 500")
    if config.purpose != "smoke":
        from .sources import validate_pack

        validate_pack(sources)
        if not config.model_identity or not config.model_sha256:
            raise ValueError("assessed generation requires pinned model identity")
    directory = run_directory(Path(config.artifact_root), run_id)
    identity = implementation_identity()
    fingerprint = digest(
        {
            "settings": config.public_settings(),
            "prompt": prompt,
            "sources": sources,
            "count": count,
            "implementation": identity["source_tree_sha256"],
        }
    )
    if resume:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("fingerprint") != fingerprint or manifest.get("run_id") != run_id:
            raise ValueError(
                "resume requires the original settings, prompt, sources, code and count"
            )
        if manifest.get("status") == "complete":
            raise ValueError("completed runs are immutable; choose a new run ID")
        if (directory / "gate-report.json").exists() or (directory / "gate-items.jsonl").exists():
            raise ValueError("gated runs are frozen; choose a new run ID")
    else:
        directory.mkdir(parents=True, exist_ok=False)
        for name in ("attempts.jsonl", "events.jsonl", "data.jsonl"):
            (directory / name).touch(exist_ok=False)
        manifest = {
            "schema_version": "1",
            "run_id": run_id,
            "purpose": config.purpose,
            "status": "running",
            "created_at": now(),
            "count": count,
            "fingerprint": fingerprint,
            "settings": config.public_settings(),
            "prompt_sha256": digest(prompt),
            "source_manifest": sources,
            "sources_sha256": digest(sources),
            "implementation": identity,
            "python_version": platform.python_version(),
            "dependencies": {
                name: importlib.metadata.version(name)
                for name in ("pydantic", "instructor", "openai", "httpx")
            },
            "course_acceptance": "not_evaluated",
            "artifacts_sha256": artifact_hashes(directory),
        }
        write_checkpoint(directory / "manifest.json", manifest)
        if config.purpose != "smoke":
            with (directory / "prompt.md").open("x", encoding="utf-8") as stream:
                stream.write(prompt)

    # Exclusive lock prevents interleaved append records from concurrent resumes.
    lock = directory / ".generation.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(now())
    validated = False
    try:
        if resume and (
            (directory / "gate-report.json").exists() or (directory / "gate-items.jsonl").exists()
        ):
            raise ValueError("gated runs are frozen; choose a new run ID")
        starts = read_records(directory / "events.jsonl")
        attempts = read_records(directory / "attempts.jsonl")
        records = read_records(directory / "data.jsonl")
        validate_evidence(manifest, directory, starts, attempts, records)
        existing_ids = {record["item_id"] for record in records}
        if len(existing_ids) != len(records):
            raise ValueError("duplicate data identity; preserve this run for inspection")
        validated = True
        # A completed audit event can survive a process interruption before data was appended.
        for attempt in attempts:
            if attempt["schema_valid"] and attempt["record"]["item_id"] not in existing_ids:
                recovered = GeneratedItem.model_validate(attempt["record"]).model_dump(mode="json")
                append_record(directory / "data.jsonl", recovered)
                records.append(recovered)
                existing_ids.add(recovered["item_id"])
        manifest["status"] = "running"
        manifest["updated_at"] = now()
        write_checkpoint(directory / "manifest.json", manifest)
        for slot in range(count):
            item_id = f"{run_id}-item-{slot + 1:04d}"
            if item_id in existing_ids:
                continue
            previous = [event for event in starts if event["slot"] == slot]
            trace_id = previous[0]["trace_id"] if previous else str(uuid.uuid4())
            parent_attempt_id = previous[-1]["attempt_id"] if previous else None
            category = CATEGORIES[slot % len(CATEGORIES)]
            for number in range(len(previous) + 1, config.max_attempts + 1):
                attempt_id = str(uuid.uuid4())
                messages = [
                    {"role": "system", "content": prompt.replace("{category}", category)},
                    {
                        "role": "user",
                        "content": (
                            f"Generate one new, distinct {category} task for slot {slot + 1}. "
                            f"Variant: {config.prompt_variant}. Attempt: {number}. "
                            "Return the seven-field JSON object. Do not claim that the result has been verified."
                        ),
                    },
                ]
                context = None
                request = messages[-1]["content"]
                if config.purpose != "smoke":
                    from .sources import context_for

                    context = context_for(sources, category, slot // len(CATEGORIES))
                    messages[-1]["content"] = json.dumps(
                        {"request": request, "untrusted_reference_context": context},
                        ensure_ascii=False,
                    )
                start = {
                    "event": "attempt_started",
                    "timestamp": now(),
                    "run_id": run_id,
                    "slot": slot,
                    "trace_id": trace_id,
                    "item_id": item_id,
                    "attempt_id": attempt_id,
                    "parent_attempt_id": parent_attempt_id,
                    "attempt_number": number,
                    "category": category,
                    "step": "generate",
                    "model": config.model,
                    "prompt_variant": config.prompt_variant,
                    "prompt_hash": digest(prompt),
                    "input": messages,
                }
                if context is not None:
                    start |= {"reference_context": context, "request": request}
                append_record(directory / "events.jsonl", start)
                starts.append(start)
                manifest["artifacts_sha256"] = artifact_hashes(directory)
                write_checkpoint(directory / "manifest.json", manifest)
                result = client.generate(messages)
                record = None
                model_matches = config.purpose == "smoke" or result.response_model == config.model
                if result.item is not None and model_matches:
                    record = GeneratedItem(
                        run_id=run_id,
                        trace_id=trace_id,
                        item_id=item_id,
                        attempt_id=attempt_id,
                        parent_attempt_id=parent_attempt_id,
                        category=category,
                        prompt_variant=config.prompt_variant,
                        prompt_hash=digest(prompt),
                        model=result.response_model or config.model,
                        source_refs=context["task"]["source_refs"]
                        if context
                        else config.source_refs,
                        reference_context=context,
                        item=result.item,
                    ).model_dump(mode="json")
                attempt = start | {
                    "event": "attempt_completed",
                    "completed_at": now(),
                    "raw_response": result.raw_response,
                    "error": result.error
                    if model_matches
                    else "reported generator model differs from selected model",
                    "error_type": result.error_type if model_matches else "ModelIdentityMismatch",
                    "response_model": result.response_model,
                    "schema_valid": record is not None,
                    "record": record,
                    "verdict": "schema_valid" if record is not None else "generation_failed",
                }
                append_record(directory / "attempts.jsonl", attempt)
                attempts.append(attempt)
                parent_attempt_id = attempt_id
                if record is not None:
                    append_record(directory / "data.jsonl", record)
                    records.append(record)
                    existing_ids.add(item_id)
                    manifest["artifacts_sha256"] = artifact_hashes(directory)
                    write_checkpoint(directory / "manifest.json", manifest)
                    break
                manifest["artifacts_sha256"] = artifact_hashes(directory)
                write_checkpoint(directory / "manifest.json", manifest)
        manifest["metrics"] = generation_metrics(count, starts, attempts, records)
        manifest["status"] = "complete" if len(records) == count else "incomplete"
        manifest["updated_at"] = now()
        manifest["artifacts_sha256"] = artifact_hashes(directory)
        write_checkpoint(directory / "manifest.json", manifest)
        return manifest
    except BaseException:
        if validated:
            manifest["status"] = "interrupted"
            manifest["updated_at"] = now()
            manifest["artifacts_sha256"] = artifact_hashes(directory)
            write_checkpoint(directory / "manifest.json", manifest)
        raise
    finally:
        lock.unlink()
