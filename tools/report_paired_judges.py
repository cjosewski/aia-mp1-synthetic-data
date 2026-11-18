"""Compare complete paired judge arms against the frozen human reference."""

import argparse
import json
from pathlib import Path

from run_frontier_pair import load_inputs

from aia_mp1.assessment import load_assessment
from aia_mp1.calibration import agreement
from aia_mp1.evaluation_schemas import DIMENSIONS, Judgment
from aia_mp1.human_reference import load_reference
from aia_mp1.tracing import read_records


def arm(directory: Path, rows: list[dict], input_sha256: str, protocol: str) -> tuple[dict, dict]:
    manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
    starts = read_records(directory / "starts.jsonl")
    results = read_records(directory / "results.jsonl")
    ids = [row["item_id"] for row in rows]
    if (
        manifest["input_sha256"] != input_sha256
        or manifest["protocol"] != protocol
        or manifest["status"] != "complete"
        or len(starts) != 50
        or len(results) != 50
        or [s["item_id"] for s in starts] != ids
        or [r["item_id"] for r in results] != ids
    ):
        raise ValueError(f"incomplete or mismatched paired arm: {directory}")
    judgments = {}
    for row, start, result in zip(rows, starts, results, strict=True):
        if (
            any(start[key] != result[key] for key in start)
            or start["messages_sha256"] != row["messages_sha256"]
            or result["valid"] is not True
            or result["judgment"] is None
        ):
            raise ValueError(f"invalid paired arm entry: {directory}")
        judgments[start["item_id"]] = Judgment.model_validate(result["judgment"]).model_dump()
    return manifest, judgments


def report(
    bundle: Path, artifact_root: Path, prompt: Path, local_dir: Path, frontier_dir: Path
) -> dict:
    inputs, rows = load_inputs(bundle, artifact_root, prompt)
    assessment_dir, assessment, records, _ = load_assessment(artifact_root, inputs["assessment_id"])
    reference = load_reference(assessment_dir, assessment, records)
    results = {}
    for name, directory, protocol in (
        ("local", local_dir, "paired-local-v1"),
        ("frontier", frontier_dir, "paired-frontier-v1"),
    ):
        manifest, judgments = arm(directory, rows, inputs["input_sha256"], protocol)
        if manifest["human_reference_sha256"] != reference["sha256"]:
            raise ValueError("paired arm used a different human reference")
        summary = agreement(records, assessment["selected_ids"], reference["labels"], judgments)
        results[name] = {
            "model": manifest["model"],
            "coverage_complete": summary["coverage_complete"],
            "all_six_passes_50": sum(
                all(judgments[item_id][dimension]["decision"] == 1 for dimension in DIMENSIONS)
                for item_id in judgments
            ),
            "dimensions": summary["dimensions"],
            "disagreements": summary["disagreements"],
            "all_dimensions_80": all(
                summary["dimensions"][dimension]["matching"] >= 16 for dimension in DIMENSIONS
            ),
        }
    return {
        "protocol": "paired-comparison-v1",
        "input_sha256": inputs["input_sha256"],
        "human_reference_sha256": reference["sha256"],
        "arms": results,
        "explanation_audit_pending": True,
        "m4_qualified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, default=Path("prompts/judge-v15-task-contract.md"))
    parser.add_argument("--local", type=Path, required=True)
    parser.add_argument("--frontier", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = report(args.bundle, args.artifact_root, args.prompt, args.local, args.frontier)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "qualified": False}))


if __name__ == "__main__":
    main()
