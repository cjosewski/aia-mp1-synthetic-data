"""Freeze label-free, source-free paired inputs for local/frontier judge comparison."""

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from aia_mp1.assessment import load_assessment
from aia_mp1.factcheck_stages import new_json
from aia_mp1.frontier_inputs import paired_messages, paired_rubric
from aia_mp1.human_reference import load_reference
from aia_mp1.schemas import CATEGORIES
from aia_mp1.tracing import digest


def prepare(artifact_root: Path, assessment_id: str, output: Path, prompt_path: Path) -> dict:
    project = Path(__file__).resolve().parents[1]
    if any(
        path.is_symlink() for path in (output, *output.parents)
    ) or output.resolve().is_relative_to(project):
        raise ValueError("paired evidence must be a new, external, non-symlink directory")
    assessment_dir, assessment, records, rubric = load_assessment(artifact_root, assessment_id)
    reference = load_reference(assessment_dir, assessment, records)
    prompt = prompt_path.read_text("utf-8")
    if (
        not prompt.strip()
        or digest(prompt) != "0ff6b3170ff6a412d5c7846dc936e5ff699820c1f212d5592419eba2abe8b28d"
    ):
        raise ValueError("frozen V15 prompt differs")
    messages = [paired_messages(prompt, rubric, row) for row in records]
    counts = Counter(row["category"] for row in messages)
    if (
        len(messages) != 50
        or [row["item_id"] for row in messages] != assessment["population_ids"]
        or len(set(row["item_id"] for row in messages)) != 50
        or counts != Counter({category: 10 for category in CATEGORIES})
        or len(reference["labels"]) != 20
    ):
        raise ValueError("paired population, categories or human reference changed")
    output.mkdir(parents=True, exist_ok=False)
    with (output / "inputs.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for row in messages:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    manifest = {
        "protocol": "paired-source-free-v1",
        "assessment_id": assessment_id,
        "assessment_sha256": assessment["manifest_sha256"],
        "human_reference_sha256": reference["sha256"],
        "prompt_sha256": digest(prompt),
        "rubric_sha256": digest(rubric),
        "public_rubric_sha256": digest(paired_rubric(rubric)),
        "population_ids": assessment["population_ids"],
        "categories": dict(counts),
        "input_sha256": digest(messages),
        "label_values_exported": False,
        "source_excerpts_exported": False,
        "model_starts": 0,
        "calibration_eligible": False,
    }
    new_json(output / "manifest.json", manifest)
    return {"output": str(output), "items": len(messages), "input_sha256": manifest["input_sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--assessment-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, default=Path("prompts/judge-v15-task-contract.md"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.artifact_root, args.assessment_id, args.output, args.prompt)))


if __name__ == "__main__":
    main()
