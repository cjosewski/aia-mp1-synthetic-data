"""Independent generation, gating, human review, judge and calibration commands."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from . import collection_cli
from .config import load_config, load_inputs
from .evaluation_cli import add_commands, run_command
from .gate import evaluate_gate
from .generate import generate_run, generation_metrics, validate_evidence
from .model_client import InstructorClient
from .schemas import GeneratedItem
from .tracing import append_record, digest, now, read_records, run_directory


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="MP1 generation, human review and local judge calibration"
    )
    commands = result.add_subparsers(dest="command", required=True)
    generate = commands.add_parser(
        "generate", help="generate a bounded batch; smoke is the default"
    )
    generate.add_argument("--config", type=Path, required=True)
    generate.add_argument("--count", type=int, default=5)
    generate.add_argument("--run-id", required=True)
    generate.add_argument(
        "--resume", action="store_true", help="append only to an incomplete original run"
    )
    gate = commands.add_parser("gate", help="screen persisted data without model requests")
    gate.add_argument("--run-id", required=True)
    gate.add_argument("--artifact-root", type=Path, default=Path("../artifacts/evidence/P1-03"))
    add_commands(commands)
    collection_cli.add_commands(commands)
    return result


def gate_run(root: Path, run_id: str) -> dict:
    directory = run_directory(root, run_id)
    lock = directory / ".generation.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write("gate " + now())
    try:
        return _gate_run(directory, run_id)
    finally:
        lock.unlink()


def _gate_run(directory: Path, run_id: str) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("run_id") != run_id:
        raise ValueError("manifest run identity does not match requested run")
    data_path = directory / "data.jsonl"
    data_hash = digest(data_path.read_text(encoding="utf-8"))
    expected_hash = manifest.get("artifacts_sha256", {}).get("data.jsonl")
    if expected_hash is None or data_hash != expected_hash:
        raise ValueError(
            "data has changed or generation has not checkpointed; preserve and inspect the run"
        )
    raw_records = read_records(data_path)
    starts = read_records(directory / "events.jsonl")
    attempts = read_records(directory / "attempts.jsonl")
    validate_evidence(manifest, directory, starts, attempts, raw_records)
    metrics = generation_metrics(manifest["count"], starts, attempts, raw_records)
    if manifest.get("metrics") != metrics:
        raise ValueError(
            "generation metrics differ from retained attempt evidence; resume or inspect the run"
        )
    records = [GeneratedItem.model_validate(record) for record in raw_records]
    if any(record.run_id != run_id for record in records):
        raise ValueError("data contains a different run identity")
    report = evaluate_gate(records, expected_count=manifest["count"])
    report.update(
        {
            "run_id": run_id,
            "generated_at": now(),
            "input_sha256": data_hash,
            "generation_status": manifest["status"],
            "purpose": manifest["purpose"],
            "generation_metrics": manifest.get("metrics", {}),
        }
    )
    # A repeat is safe only for the same immutable input and same gate implementation.
    report_path = directory / "gate-report.json"
    gate_version = digest(
        {
            name: digest(Path(__file__).with_name(name).read_text(encoding="utf-8"))
            for name in ("gate.py", "schemas.py", "cli.py")
        }
    )
    report["gate_implementation_sha256"] = gate_version
    items_path = directory / "gate-items.jsonl"
    if report_path.exists():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
        if (
            existing.get("input_sha256") != data_hash
            or existing.get("gate_implementation_sha256") != gate_version
        ):
            raise ValueError("existing gate evidence differs; do not overwrite it")
        if not items_path.exists() or read_records(items_path) != existing["items"]:
            raise ValueError("cached gate result has missing or changed item evidence")
        if existing != report | {"generated_at": existing.get("generated_at")}:
            raise ValueError("cached gate report differs from recomputed results")
        return existing
    if items_path.exists():
        if read_records(items_path) != report["items"]:
            raise ValueError("incomplete gate item evidence; preserve it for inspection")
    else:
        with items_path.open("x", encoding="utf-8"):
            pass
        for item in report["items"]:
            append_record(items_path, item)
    # Commit the summary only after the complete per-item evidence is durable.
    with report_path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in collection_cli.COMMANDS:
            result, exit_code = collection_cli.run_command(args)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return exit_code
        if args.command not in {"generate", "gate"}:
            result, exit_code = run_command(args)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return exit_code
        if args.command == "generate":
            config = load_config(args.config)
            prompt, sources = load_inputs(config)
            with InstructorClient(
                base_url=config.base_url,
                model=config.model,
                api_key=config.api_key(),
                mode=config.mode,
                timeout_seconds=config.timeout_seconds,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
            ) as client:
                result = generate_run(
                    config,
                    prompt,
                    sources,
                    count=args.count,
                    run_id=args.run_id,
                    client=client,
                    resume=args.resume,
                )
            print(
                json.dumps(
                    {
                        "run_id": args.run_id,
                        "status": result["status"],
                        "artifact_directory": str(
                            run_directory(Path(config.artifact_root), args.run_id)
                        ),
                        "metrics": result["metrics"],
                    },
                    indent=2,
                )
            )
            return 0 if result["status"] == "complete" else 1
        report = gate_run(args.artifact_root, args.run_id)
        print(
            json.dumps(
                {
                    key: report[key]
                    for key in (
                        "run_id",
                        "status",
                        "status_scope",
                        "quality_status",
                        "course_acceptance",
                        "counts",
                    )
                },
                indent=2,
            )
        )
        return 0 if report["status"] == "passed" else 1
    except ValidationError as exc:
        # Do not echo arbitrary config/model input values in validation errors.
        details = [
            {"location": list(error["loc"]), "type": error["type"]} for error in exc.errors()
        ]
        print(json.dumps({"status": "error", "validation_errors": details}), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(
            json.dumps({"status": "interrupted", "error": "run retained; use --resume"}),
            file=sys.stderr,
        )
        return 130
