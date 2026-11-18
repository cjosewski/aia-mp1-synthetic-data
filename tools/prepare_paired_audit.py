"""Prepare a local-only explanation audit packet from a complete paired arm."""

import argparse
import json
from pathlib import Path

from report_paired_judges import arm
from run_frontier_pair import load_inputs

from aia_mp1.assessment import load_assessment
from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.human_reference import load_reference


def prepare(
    bundle: Path, artifact_root: Path, prompt: Path, arm_dir: Path, protocol: str, output: Path
) -> dict:
    inputs, rows = load_inputs(bundle, artifact_root, prompt)
    assessment_dir, assessment, records, _ = load_assessment(artifact_root, inputs["assessment_id"])
    reference = load_reference(assessment_dir, assessment, records)
    manifest, judgments = arm(arm_dir, rows, inputs["input_sha256"], protocol)
    if manifest["human_reference_sha256"] != reference["sha256"]:
        raise ValueError("human reference differs")
    by_id = {record["item_id"]: record for record in records}
    sections = [
        "# Paired judge explanation audit",
        "",
        "Local-only review packet. Compare each justification with the task,",
        "candidate and human notes. This packet is not sent to either model.",
        "",
    ]
    for number, item_id in enumerate(assessment["selected_ids"], 1):
        record = by_id[item_id]
        label = reference["labels"][item_id]
        sections += [
            f"## {number}. {item_id}",
            "",
            f"**Task:** {record['reference_context']['task']['brief']}",
            "",
            f"**Candidate:** `{json.dumps(record['item'], ensure_ascii=False)}`",
            "",
            f"**Human notes:** {label['notes']}",
            "",
            "| Dimension | Human | Judge | Justification |",
            "| --- | ---: | ---: | --- |",
        ]
        for dimension in DIMENSIONS:
            human = label["decisions"][dimension]
            judge = judgments[item_id][dimension]
            justification = judge["justification"].replace("|", "\\|").replace("\n", " ")
            sections.append(f"| {dimension} | {human} | {judge['decision']} | {justification} |")
        sections.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write("\n".join(sections) + "\n")
    return {
        "output": str(output),
        "items": len(assessment["selected_ids"]),
        "justifications": len(assessment["selected_ids"]) * len(DIMENSIONS),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, default=Path("prompts/judge-v15-task-contract.md"))
    parser.add_argument("--arm", type=Path, required=True)
    parser.add_argument(
        "--protocol", choices=("paired-frontier-v1", "paired-local-v1"), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            prepare(
                args.bundle, args.artifact_root, args.prompt, args.arm, args.protocol, args.output
            )
        )
    )


if __name__ == "__main__":
    main()
