"""Test paired human-reviewed examples using leave-one-category-out AEC development data."""

import argparse
import json
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from run_aec_development import capture, freeze_development_labels, pin
from screen_aec_devstral import DIRECTORY as CONTROL
from screen_aec_devstral import run as verify_control
from screen_aec_devstral import verify_service
from screen_aec_local_model import SCREEN_MODEL

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.calibration import agreement
from aia_mp1.judge import JudgeConfig

DIRECTORY = "api-development-devstral-examples-001"


def with_examples(messages, training, labels):
    target = json.loads(messages[1]["content"])["untrusted_reference_context"]["task"]
    eligible = [
        k
        for k in sorted(training)
        if training[k]["reference_context"]["task"]["category"] != target["category"]
    ]
    examples, ids = [], []
    for decision in (0, 1):
        key = next(
            k
            for k in eligible
            if labels[k]["decisions"]["D1"] == labels[k]["decisions"]["D2"] == decision
        )
        row, label = training[key], labels[key]
        if row["reference_context"]["task"]["id"] == target["id"]:
            raise ValueError("Example overlaps the target task")
        examples.append(
            {
                "brief": row["reference_context"]["task"]["brief"],
                "candidate": row["item"],
                "ratings": label["decisions"],
                "reviewer_note": label["notes"],
            }
        )
        ids.append(key)
    instruction = "\n\nThe two completed reviews below illustrate the rubric. Apply the same criteria independently to the new case in the user message. Each example's data and ratings apply only to that example.\n"
    system = messages[0] | {
        "content": messages[0]["content"] + instruction + json.dumps(examples, ensure_ascii=False)
    }
    return [system, messages[1]], ids


def run(root, stage):
    verify_control(root, "prepare")
    parent, assessment, records, _ = load_assessment(root, REVIEW)
    control = root / CONTROL
    protocol = read_json(control / "protocol.json")
    directory = root / DIRECTORY
    directory.mkdir(exist_ok=True)
    ids = assessment["selected_ids"]
    training = {r["item_id"]: r for r in records if r["item_id"] in ids}
    source = read_json(root / SCREEN_MODEL / "requests.json")
    with exclusive(directory):
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(directory / "review-checkpoint.json") != protocol["human_reference"]:
            raise ValueError("Unmatched development references")
        requests, examples = {}, {}
        for key in ids:
            requests[key], examples[key] = with_examples(source[key], training, labels)
        pin(directory / "requests.json", requests)
        pin(
            directory / "protocol.json",
            {
                "development_only": True,
                "control_protocol_sha256": file_hash(control / "protocol.json"),
                "requests_sha256": file_hash(directory / "requests.json"),
                "examples": examples,
                "code_sha256": file_hash(Path("tools/screen_aec_examples.py")),
                "human_reference": protocol["human_reference"],
                "model": protocol["model"],
                "case_ids": ids,
                "attempts_per_case": 1,
                "advance_rule": protocol["advance_rule"],
                "selection": "For the target category, exclude all reviews in that category. Among the other categories, select the first item ID with D1=D2=0 and then the first with D1=D2=1. Supply their briefs, candidates, original ratings and notes. Use this same fixed development library and selection rule on any later assessment.",
            },
        )
        if stage == "prepare":
            return {"cases": len(ids), "requests_sha256": file_hash(directory / "requests.json")}
        config_data = dict(protocol["model"])
        del config_data["authentication"]
        config = JudgeConfig.model_validate(
            read_json(root / "judge-preparation-v1/judge.json") | config_data
        )
        deploy = pin(directory / "deployment.json", read_json(control / "deployment.json"))
        if stage == "score":
            verify_service(directory, config, requests, deploy["parts"])
        results = {
            k: capture(
                directory, k, "control", requests[k], config, replay_only=stage == "replay"
            ).model_dump()
            for k in ids
        }
        summary = agreement(list(training.values()), ids, labels, results)
        pin(
            directory / "report.json",
            {
                "development_only": True,
                "summary": summary,
                "protocol_sha256": file_hash(directory / "protocol.json"),
                "deployment_sha256": file_hash(directory / "deployment.json"),
                "token_fit_sha256": file_hash(directory / "token-fit.json"),
                "returns": {k: file_hash(directory / "control" / k / "return.json") for k in ids},
            },
        )
        return {
            "valid": len(results),
            "matches": {d: v["matching"] for d, v in summary["dimensions"].items()},
            "report_sha256": file_hash(directory / "report.json"),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "score", "replay"))
    print(json.dumps(run(ROOT.resolve(), parser.parse_args().stage), indent=2))
