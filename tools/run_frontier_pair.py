"""Run the approved, source-free GPT-6.2 Astra arm once per frozen item."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from openai import OpenAI

from aia_mp1.assessment import load_assessment
from aia_mp1.frontier_dispatch import (
    CAP_USD,
    INPUT_RATE_PER_MILLION,
    MAX_STARTS,
    MODEL,
    OUTPUT_RATE_PER_MILLION,
    request_once,
    upper_bound_usd,
)
from aia_mp1.frontier_inputs import validate_paired_message
from aia_mp1.human_reference import load_reference
from aia_mp1.tracing import append_record, digest, now, read_records


def load_inputs(bundle: Path, artifact_root: Path, prompt_path: Path) -> tuple[dict, list[dict]]:
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    if manifest["protocol"] != "paired-source-free-v1":
        raise ValueError("wrong paired-input protocol")
    assessment_dir, assessment, records, rubric = load_assessment(
        artifact_root, manifest["assessment_id"]
    )
    reference = load_reference(assessment_dir, assessment, records)
    prompt = prompt_path.read_text("utf-8")
    rows = read_records(bundle / "inputs.jsonl")
    if (
        manifest["assessment_sha256"] != assessment["manifest_sha256"]
        or manifest["rubric_sha256"] != digest(rubric)
        or manifest["prompt_sha256"] != digest(prompt)
        or manifest["input_sha256"] != digest(rows)
        or manifest["human_reference_sha256"] != reference["sha256"]
        or manifest["population_ids"] != [r["item_id"] for r in rows]
        or manifest["population_ids"] != assessment["population_ids"]
        or len(rows) != MAX_STARTS
        or manifest["model_starts"] != 0
        or manifest["label_values_exported"] is not False
        or manifest["source_excerpts_exported"] is not False
    ):
        raise ValueError("paired-input provenance or population differs")
    for row in rows:
        validate_paired_message(row, prompt, rubric)
        if len(json.dumps(row["messages"], ensure_ascii=False).encode("utf-8")) > 10_000:
            raise ValueError("paired input exceeds the budgeted input envelope")
    return manifest, rows


def redact(value, secret: str):
    if isinstance(value, str):
        return value.replace(secret, "[REDACTED]")
    if isinstance(value, dict):
        return {redact(k, secret): redact(v, secret) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secret) for v in value]
    return value


def credential_from_file(path: Path) -> str:
    """Read the owner-provided AIA_GPT entry as data, never as shell code."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("credential file is missing or is a symlink")
    candidates = []
    for line in path.read_text("utf-8").splitlines():
        if line.lstrip().startswith("AIA_GPT="):
            value = line.split("=", 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            candidates.append(value)
    if len(candidates) != 1 or not candidates[0].startswith("sk-"):
        raise ValueError("credential file needs one valid AIA_GPT entry")
    return candidates[0]


def run(bundle: Path, artifact_root: Path, prompt_path: Path, output: Path, key: str) -> dict:
    manifest, rows = load_inputs(bundle, artifact_root, prompt_path)
    if not key.strip():
        raise ValueError("OPENAI_API_KEY must be set in the process environment")
    if upper_bound_usd(MAX_STARTS) > CAP_USD:
        raise ValueError("worst-case token charge exceeds the approved cap")
    if output.exists() or output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("frontier result must be a new external directory")
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("symlink output path is not supported")
    output.mkdir(parents=True, exist_ok=False)
    run_manifest = {
        "protocol": "paired-frontier-v1",
        "model": MODEL,
        "reasoning_effort": "medium",
        "service_tier": "default",
        "max_completion_tokens": 8192,
        "max_starts": MAX_STARTS,
        "approved_cap_usd": CAP_USD,
        "worst_case_usd_at_listed_rates": upper_bound_usd(MAX_STARTS),
        "input_rate_usd_per_million": INPUT_RATE_PER_MILLION,
        "output_rate_usd_per_million": OUTPUT_RATE_PER_MILLION,
        "input_sha256": manifest["input_sha256"],
        "assessment_sha256": manifest["assessment_sha256"],
        "human_reference_sha256": manifest["human_reference_sha256"],
        "dispatch_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "created_at": now(),
        "status": "running",
    }
    (output / "manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n", "utf-8")
    (output / "starts.jsonl").touch(exist_ok=False)
    (output / "results.jsonl").touch(exist_ok=False)
    spent = 0.0
    with OpenAI(api_key=key, max_retries=0, timeout=180) as client:
        for index, row in enumerate(rows):
            if spent + upper_bound_usd(1) > CAP_USD:
                run_manifest["status"] = "cost_stop"
                break
            start = {
                "index": index,
                "item_id": row["item_id"],
                "messages_sha256": row["messages_sha256"],
                "started_at": now(),
            }
            append_record(output / "starts.jsonl", start)
            result = request_once(client, row["messages"])
            if result.input_tokens is not None and result.output_tokens is not None:
                spent += (
                    result.input_tokens * INPUT_RATE_PER_MILLION
                    + result.output_tokens * OUTPUT_RATE_PER_MILLION
                ) / 1_000_000
            append_record(
                output / "results.jsonl",
                start
                | {
                    "completed_at": now(),
                    "valid": result.judgment is not None,
                    "judgment": result.judgment.model_dump(mode="json")
                    if result.judgment
                    else None,
                    "raw_response": redact(result.raw, key),
                    "error_type": result.error_type,
                    "error": result.error,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "estimated_cost_usd": spent,
                },
            )
            if result.judgment is None:
                run_manifest["status"] = "failed_stop"
                break
        else:
            run_manifest["status"] = "complete"
    run_manifest["estimated_cost_usd"] = spent
    run_manifest["started"] = len(read_records(output / "starts.jsonl"))
    run_manifest["completed"] = len(read_records(output / "results.jsonl"))
    (output / "manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n", "utf-8")
    return {
        "status": run_manifest["status"],
        "started": run_manifest["started"],
        "completed": run_manifest["completed"],
        "estimated_cost_usd": spent,
        "output": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, default=Path("prompts/judge-v15-task-contract.md"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--check-access", action="store_true")
    parser.add_argument("--credential-file", type=Path)
    args = parser.parse_args()
    if args.check_access:
        load_inputs(args.bundle, args.artifact_root, args.prompt)
        key = (
            credential_from_file(args.credential_file)
            if args.credential_file
            else os.environ.get("OPENAI_API_KEY", "")
        )
        if not key:
            parser.error("a credential source is required for access check")
        try:
            with OpenAI(api_key=key, max_retries=0, timeout=20) as client:
                response = client.models.retrieve(MODEL)
            print(
                json.dumps(
                    {
                        "model_access": response.id == MODEL,
                        "model": response.id,
                        "inference_starts": 0,
                    }
                )
            )
        except Exception as exc:
            print(
                json.dumps(
                    {"model_access": False, "error_type": type(exc).__name__, "inference_starts": 0}
                )
            )
        return
    if args.preflight:
        manifest, rows = load_inputs(args.bundle, args.artifact_root, args.prompt)
        print(
            json.dumps(
                {
                    "validated": len(rows),
                    "input_sha256": manifest["input_sha256"],
                    "worst_case_usd_at_listed_rates": upper_bound_usd(MAX_STARTS),
                    "cap_usd": CAP_USD,
                    "credential_present": bool(os.environ.get("OPENAI_API_KEY"))
                    or bool(args.credential_file and credential_from_file(args.credential_file)),
                }
            )
        )
        return
    if args.output is None:
        parser.error("--output is required for live dispatch")
    if args.credential_file and os.environ.get("OPENAI_API_KEY"):
        parser.error("use exactly one credential source")
    key = (
        credential_from_file(args.credential_file)
        if args.credential_file
        else os.environ.get("OPENAI_API_KEY", "")
    )
    print(
        json.dumps(
            run(
                args.bundle,
                args.artifact_root,
                args.prompt,
                args.output,
                key,
            )
        )
    )


if __name__ == "__main__":
    main()
