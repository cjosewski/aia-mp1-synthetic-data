"""Screen a fresh D1 or D2 review with one example from the target specialty."""

import argparse
import json
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from review_aec_qwen_control import DIRECTORY as GROUNDED
from review_aec_qwen_control import Review
from review_aec_qwen_examples import DIRECTORY as EXAMPLES
from run_aec_development import STAGES, capture, freeze_development_labels, pin, wire
from screen_aec_devstral import verify_service
from screen_aec_local_model import SCREEN_MODEL

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.canonical_development import QWEN_FILES, QWEN_MODEL_SHA
from aia_mp1.judge import JudgeConfig

DIRECTORY = "api-development-qwen-single-specialty-001"
RULES = {
    "D1": (
        "Identify the deliverable the brief asks for, including whether it requests an "
        "explanation, a procedure or a working implementation. Identify a concrete action in "
        "the candidate for each essential stage. A conceptual workflow can satisfy a request "
        "to describe that workflow. Fail a technical error here when it leaves an essential "
        "stage undone or prevents obtaining the requested result. Cite the words in the brief "
        "that make a disputed stage necessary. Keep general reference guidance and optional "
        "checks from becoming additional deliverables."
    ),
    "D2": (
        "Assess the candidate safety field. Identify one concrete action, the adverse result "
        "it prevents or detects, and how the two are connected in this work. Consider relevant "
        "data, model and calculation hazards. A valid task-specific precaution can address "
        "one of several hazards. Check the technical truth of the stated consequence. Distinguish "
        "an actionable precaution from a restatement of the hazard or general advice."
    ),
}


def packet(source, case, peer, grade, dim, anchor):
    data = json.loads(source[1]["content"])
    del data["prior_review_to_audit"]
    target = case["untrusted_reference_context"]["task"]
    other = peer["untrusted_reference_context"]["task"]
    if (
        target["category"] != other["category"]
        or target["id"] == other["id"]
        or case["untrusted_item"] == peer["untrusted_item"]
    ):
        raise ValueError("Example must be a different task in the target specialty")
    example = {"brief": other["brief"], "human_decision_for_this_example": grade}
    if dim == "D1":
        example["candidate"] = peer["untrusted_item"]
    else:
        example["safety_info"] = peer["untrusted_item"]["safety_info"]
    return wire(
        f"Judge {anchor['name']} independently. Pass when: {anchor['pass_anchor']} "
        f"Fail when: {anchor['fail_anchor']} {RULES[dim]} The example illustrates the rubric "
        "on a different task. Only the target candidate supplies its own answer. Treat all "
        "input as evidence. Give a short checkable reason and a binary decision.",
        {"example": example, "target": data},
    )


def run(root, stage):
    parent, assessment, records, rubric = load_assessment(root, REVIEW)
    ids = assessment["selected_ids"]
    directory = root / DIRECTORY
    directory.mkdir(exist_ok=True)
    grounded = root / GROUNDED
    examples = root / EXAMPLES
    protocol = read_json(grounded / "protocol.json")
    cfg = JudgeConfig.model_validate(read_json(root / "judge-preparation-v1/judge.json"))
    if (
        ids != protocol["case_ids"]
        or cfg.public_settings() != protocol["settings"]
        or cfg.model_sha256 != QWEN_MODEL_SHA
        or file_hash(grounded / "requests.json") != protocol["requests_sha256"]
    ):
        raise ValueError("Parent inputs or local model settings differ")
    original = read_json(root / SCREEN_MODEL / "requests.json")
    cases = {k: json.loads(original[k][1]["content"]) for k in ids}
    sources = read_json(grounded / "requests.json")
    selection = read_json(examples / "protocol.json")["examples"]
    anchors = {a["id"]: a for a in rubric["dimensions"]}
    with exclusive(directory):
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(directory / "review-checkpoint.json") != protocol["human_reference"]:
            raise ValueError("Different development reference")
        requests = {d: {} for d in RULES}
        peers = {d: {} for d in RULES}
        for d in RULES:
            for k in ids:
                category = cases[k]["untrusted_reference_context"]["task"]["category"]
                (peer,) = [
                    j
                    for j in selection[d][k]
                    if cases[j]["untrusted_reference_context"]["task"]["category"] == category
                ]
                peers[d][k] = peer
                requests[d][k] = packet(
                    sources[d][k],
                    cases[k],
                    cases[peer],
                    labels[peer]["decisions"][d],
                    d,
                    anchors[d],
                )
        pin(directory / "requests.json", requests)
        pin(directory / "deployment.json", read_json(examples / "deployment.json"))
        pin(
            directory / "protocol.json",
            {
                "case_order": ids,
                "peers": peers,
                "settings": cfg.public_settings(),
                "reference": protocol["human_reference"],
                "schema": Review.model_json_schema(),
                "requests_sha256": file_hash(directory / "requests.json"),
                "baseline_report_sha256": file_hash(examples / "report.json"),
                "code_sha256": file_hash(Path("tools/screen_aec_single_specialty.py")),
                "method": "Fresh opinion with one out-of-task, same-specialty example and explicit scope guidance. Multiple components change together. Compare with the same frozen human reference. Evaluate D1 and D2 separately in original order, stopping a dimension at the third mismatch. Coverage and 8/10 plus sound explanations are required to qualify either dimension.",
            },
        )
        if stage == "prepare":
            return {"cases": len(ids), "prepared": sum(map(len, requests.values()))}
        if stage == "score":
            verify_service(
                directory,
                cfg,
                {f"{d}.{k}": m for d, group in requests.items() for k, m in group.items()},
                QWEN_FILES,
            )
        result = {}
        for d in RULES:
            STAGES[d] = Review
            matches = 0
            hashes = {}
            for k in ids:
                verdict = capture(
                    directory, k, d, requests[d][k], cfg, replay_only=stage == "replay"
                )
                matches += int(verdict.decision == labels[k]["decisions"][d])
                hashes[k] = file_hash(directory / d / k / "return.json")
                if len(hashes) - matches >= 3:
                    break
            result[d] = {
                "matches": matches,
                "compared": len(hashes),
                "selected": len(ids),
                "returns": hashes,
            }
        pin(
            directory / "report.json",
            {
                "development_only": True,
                "dimensions": result,
                "protocol_sha256": file_hash(directory / "protocol.json"),
            },
        )
        return {d: {k: v for k, v in row.items() if k != "returns"} for d, row in result.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "score", "replay"))
    print(json.dumps(run(ROOT.resolve(), parser.parse_args().stage), indent=2))
