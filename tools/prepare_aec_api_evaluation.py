"""Freeze label-free requests for the AEC API-correctness comparison."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from aia_mp1.assessment import exclusive, load_assessment, read_json, read_text, save_new
from aia_mp1.human_reference import load_reference
from aia_mp1.judge import messages_for
from aia_mp1.schemas import DOMAIN
from aia_mp1.tracing import digest

ROOT = Path("../artifacts/evidence/P1-03/aec-course")
REVISIONS = ("v1", "v2", "v3")
ANCHOR = Path("config/aec-course/api-correctness-d3.json")
SOURCES = {
    "aec-course-baseline-review": "16ba09926caa42b2cf6bebf3a5ee6e0422a2454b8883c6f89a7aa2bfcfc1b2e3",
    "aec-course-baseline-d3-review": "45e2dc3d149660ec322f00264f6b3fc2a5184a01d4adb01cfc72c195a2d027d4",
}


def prepare(root=ROOT, revision="v1"):
    if DOMAIN != "aec-course":
        raise ValueError("Set AIA_MP1_DOMAIN=aec-course")
    if revision not in REVISIONS:
        raise ValueError("Unknown AEC judge prompt revision")
    reviews = []
    for source, expected in SOURCES.items():
        parent, assessment, records, rubric = load_assessment(root, source)
        reference = load_reference(parent, assessment, records)
        notice = read_json(parent / "human-reference-withdrawal.json")
        if reference["sha256"] != expected or notice["human_reference_sha256"] != expected:
            raise ValueError("Source review or its course-scoring withdrawal differs")
        reviews.append((assessment, reference))
    original, first = reviews[0]
    for key in (
        "data_sha256",
        "cohort_sha256",
        "reference_pack_sha256",
        "rubric_sha256",
        "selected_ids",
    ):
        if original[key] != assessment[key]:
            raise ValueError(f"Source reviews differ on {key}")
    for item_id, label in reference["labels"].items():
        if label["decisions"] != first["labels"][item_id]["decisions"]:
            raise ValueError("The two frozen reviews have different decisions")

    d3 = read_json(ANCHOR)
    if d3["id"] != "D3" or d3["pass_rate_minimum"] != rubric["dimensions"][2]["pass_rate_minimum"]:
        raise ValueError("The API anchor must preserve the D3 quality threshold")
    adapted = rubric | {
        "version": "aec-api-correctness-v1",
        "status": "owner_defined_aec_d3",
        "dimensions": [d3 if row["id"] == "D3" else row for row in rubric["dimensions"]],
    }
    prompt = read_text(Path(f"prompts/aec-api-correctness-judge-{revision}.md"))
    requests = []
    for item in records:
        messages = messages_for(prompt, adapted, item)
        requests.append(
            {
                "item_id": item["item_id"],
                "trace_id": item["trace_id"],
                "messages_sha256": digest({"messages": messages}),
                "messages": messages,
            }
        )
    wire = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in requests)
    manifest = {
        "protocol": adapted["version"],
        "source_assessment": assessment["assessment_id"],
        "source_assessment_sha256": assessment["manifest_sha256"],
        "source_references": SOURCES,
        "reviewer_clarification_sha256": digest(notice),
        "selected_ids": assessment["selected_ids"],
        "population": len(records),
        "prompt_sha256": digest(prompt),
        "rubric_sha256": digest(adapted),
        "requests_sha256": digest(wire),
    }
    if revision != "v1":
        manifest["judge_prompt_revision"] = revision
    target = root.resolve() / f"api-correctness-{revision}-inputs"
    with exclusive(root.resolve()):
        if not target.exists():
            with TemporaryDirectory(dir=root) as temporary:
                staging = Path(temporary) / target.name
                staging.mkdir()
                save_new(staging / "rubric.json", adapted)
                save_new(staging / "manifest.json", manifest)
                (staging / "prompt.md").write_text(prompt, encoding="utf-8", newline="\n")
                (staging / "requests.jsonl").write_text(wire, encoding="utf-8", newline="\n")
                staging.rename(target)
        if (
            target.is_symlink()
            or read_json(target / "manifest.json") != manifest
            or read_json(target / "rubric.json") != adapted
            or read_text(target / "prompt.md") != prompt
            or read_text(target / "requests.jsonl") != wire
        ):
            raise ValueError("Frozen API-correctness input packet differs")
    return target, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", choices=REVISIONS, default="v1")
    target, manifest = prepare(revision=parser.parse_args().revision)
    print(
        f"{target}: {manifest['population']} requests, {len(manifest['selected_ids'])} reviewed items"
    )
