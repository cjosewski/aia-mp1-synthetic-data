"""Run a source-free Qwen control against the same frozen paired inputs."""

import argparse
import json
import os
from pathlib import Path

from run_frontier_pair import load_inputs, redact

from aia_mp1.evaluation_schemas import Judgment
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.model_client import InstructorClient
from aia_mp1.tracing import append_record, now, read_records


def run(
    bundle: Path,
    artifact_root: Path,
    prompt: Path,
    output: Path,
    endpoint: str,
    model: str,
    key: str,
) -> dict:
    manifest, rows = load_inputs(bundle, artifact_root, prompt)
    if not endpoint.startswith("http://127.0.0.1:"):
        raise ValueError("local control requires an owned loopback tunnel")
    if not model.strip() or not key.strip():
        raise ValueError("local model and key are required")
    with_server = LocalServer(endpoint, key)
    try:
        props = with_server.json("/props")
        served = with_server.json("/v1/models")["data"]
        context = props["default_generation_settings"]["n_ctx"]
        if (
            with_server.json("/health").get("status") != "ok"
            or len(served) != 1
            or served[0]["id"] != model
            or props["model_path"] != model
            or props["total_slots"] != 1
            or context != 16384
        ):
            raise ValueError("local server identity or settings differ")
        fits = [
            with_server.token_fit(
                {"messages": row["messages"], "max_tokens": 8192}, context, reserve=2048
            )
            for row in rows
        ]
        if not all(row["fits"] for row in fits):
            raise ValueError("one or more paired requests exceed local context")
    finally:
        with_server.close()
    if output.exists() or output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("control result must be a new external directory")
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("symlink output path is not supported")
    output.mkdir(parents=True, exist_ok=False)
    run_manifest = {
        "protocol": "paired-local-v1",
        "model": model,
        "endpoint": endpoint,
        "temperature": 0.1,
        "max_tokens": 8192,
        "max_starts": 50,
        "input_sha256": manifest["input_sha256"],
        "assessment_sha256": manifest["assessment_sha256"],
        "human_reference_sha256": manifest["human_reference_sha256"],
        "created_at": now(),
        "status": "running",
        "max_preflight_prompt_tokens": max(row["prompt_tokens"] for row in fits),
    }
    (output / "manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n", "utf-8")
    (output / "starts.jsonl").touch(exist_ok=False)
    (output / "results.jsonl").touch(exist_ok=False)
    with InstructorClient(
        base_url=endpoint,
        model=model,
        api_key=key,
        response_model=Judgment,
        mode="json",
        temperature=0.1,
        max_tokens=8192,
        timeout_seconds=300,
    ) as client:
        for index, row in enumerate(rows):
            start = {
                "index": index,
                "item_id": row["item_id"],
                "messages_sha256": row["messages_sha256"],
                "started_at": now(),
            }
            append_record(output / "starts.jsonl", start)
            result = client.generate(row["messages"])
            valid = result.item is not None and result.response_model == model
            append_record(
                output / "results.jsonl",
                start
                | {
                    "completed_at": now(),
                    "valid": valid,
                    "judgment": result.item.model_dump(mode="json") if valid else None,
                    "raw_response": redact(result.raw_response, key),
                    "response_model": result.response_model,
                    "error_type": (result.error_type or "ModelMismatch") if not valid else None,
                    "error": (result.error or "served model differs") if not valid else None,
                },
            )
            if not valid:
                run_manifest["status"] = "failed_stop"
                break
        else:
            run_manifest["status"] = "complete"
    run_manifest["started"] = len(read_records(output / "starts.jsonl"))
    run_manifest["completed"] = len(read_records(output / "results.jsonl"))
    (output / "manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n", "utf-8")
    return {
        "status": run_manifest["status"],
        "started": run_manifest["started"],
        "completed": run_manifest["completed"],
        "output": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, default=Path("prompts/judge-v15-task-contract.md"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.bundle,
                args.artifact_root,
                args.prompt,
                args.output,
                args.endpoint,
                args.model,
                os.environ.get("AIA_MP1_LOCAL_API_KEY", "local-only-placeholder"),
            )
        )
    )


if __name__ == "__main__":
    main()
