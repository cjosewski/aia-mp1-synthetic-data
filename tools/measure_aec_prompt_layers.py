"""Complete the plain, layer-alone and cumulative AEC comparison from Unit 4."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from statistics import median

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from run_aec_development import capture, freeze_development_labels, pin
from screen_aec_devstral import DIRECTORY as CONTROL
from screen_aec_devstral import run as control_run
from screen_aec_devstral import verify_service
from screen_aec_examples import DIRECTORY as COMBINED
from screen_aec_examples import run as combined_run
from screen_aec_local_model import SCREEN_MODEL

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.calibration import agreement
from aia_mp1.judge import JudgeConfig
from aia_mp1.tracing import digest

PLAIN = "api-development-devstral-plain-001"
ALONE = "api-development-devstral-plain-examples-001"


def run(root, directory_name, stage):
    parent, assessment, records, _ = load_assessment(root, REVIEW)
    control = read_json(root / CONTROL / "protocol.json")
    examples_protocol = read_json(root / COMBINED / "protocol.json")
    if (
        file_hash(root / SCREEN_MODEL / "requests.json") != control["requests_sha256"]
        or file_hash(root / COMBINED / "requests.json") != examples_protocol["requests_sha256"]
        or file_hash(root / CONTROL / "protocol.json")
        != examples_protocol["control_protocol_sha256"]
    ):
        raise ValueError("Frozen control or example inputs differ")
    base = read_json(root / SCREEN_MODEL / "requests.json")
    combined = read_json(root / COMBINED / "requests.json")
    original = Path("prompts/aec-api-correctness-judge-v3.md").read_text().strip()
    minimal = original.split("\n\n")[0]
    directory = root / directory_name
    directory.mkdir(exist_ok=True)
    ids = assessment["selected_ids"]
    requests = {}
    for key in ids:
        messages = base[key] if directory_name == PLAIN else combined[key]
        system = messages[0]["content"]
        if (
            not system.startswith(original)
            or not combined[key][0]["content"].startswith(base[key][0]["content"])
            or combined[key][1:] != base[key][1:]
        ):
            raise ValueError("Original prompt, rubric or worked-example composition differs")
        requests[key] = [
            messages[0] | {"content": minimal + system[len(original) :]},
            *messages[1:],
        ]
    with exclusive(directory):
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(directory / "review-checkpoint.json") != control["human_reference"]:
            raise ValueError("Blind development references differ")
        pin(directory / "requests.json", requests)
        pin(
            directory / "protocol.json",
            {
                "development_only": True,
                "case_ids": ids,
                "model": control["model"],
                "human_reference": control["human_reference"],
                "requests_sha256": file_hash(directory / "requests.json"),
                "reference_protocols": {
                    name: file_hash(root / name / "protocol.json") for name in (CONTROL, COMBINED)
                },
                "code_sha256": file_hash(Path("tools/measure_aec_prompt_layers.py")),
                "attempts_per_case": 1,
                "max_starts": 10,
                "advance_rule": control["advance_rule"],
                "design": "Use the opening instruction and the entire original rubric. Remove detailed v3 guidance. Preserve the original candidate and task. In the layer-alone arm retain the identical pair of cross-category demonstrations.",
            },
        )
        if stage == "prepare":
            return {"cases": len(ids), "requests_sha256": file_hash(directory / "requests.json")}
        settings = {k: v for k, v in control["model"].items() if k != "authentication"}
        config = JudgeConfig.model_validate(
            read_json(root / "judge-preparation-v1/judge.json") | settings
        )
        deployment = pin(
            directory / "deployment.json", read_json(root / CONTROL / "deployment.json")
        )
        if stage == "score":
            verify_service(directory, config, requests, deployment["parts"])
        scores, failures = {}, {}
        for key in ids:
            try:
                scores[key] = capture(
                    directory, key, "control", requests[key], config, replay_only=stage == "replay"
                ).model_dump()
            except ValueError:
                slot = directory / "control" / key
                returned = read_json(slot / "return.json")
                if (
                    not returned.get("error_type")
                    or returned.get("parsed") is not None
                    or returned["start_sha256"] != file_hash(slot / "start.json")
                    or returned["sha256"]
                    != digest({k: v for k, v in returned.items() if k != "sha256"})
                ):
                    raise
                failures[key] = returned["error_type"]
        summary = agreement([r for r in records if r["item_id"] in ids], ids, labels, scores)
        pin(
            directory / "report.json",
            {
                "development_only": True,
                "summary": summary,
                "failures": failures,
                "protocol_sha256": file_hash(directory / "protocol.json"),
                "deployment_sha256": file_hash(directory / "deployment.json"),
                "token_fit_sha256": file_hash(directory / "token-fit.json"),
                "returns": {k: file_hash(directory / "control" / k / "return.json") for k in ids},
            },
        )
        return {
            "valid": len(scores),
            "matches": {k: v["matching"] for k, v in summary["dimensions"].items()},
        }


def scoreboard(root):
    control_run(root, "replay")
    combined_run(root, "replay")
    for name in (PLAIN, ALONE):
        run(root, name, "replay")
    rows, missed = {}, {}
    for name in (PLAIN, ALONE, CONTROL, COMBINED):
        directory = root / name
        report = read_json(directory / "report.json")
        summary = report["summary"]
        elapsed = []
        for key in report["returns"]:
            slot = directory / "control" / key
            start, end = read_json(slot / "start.json"), read_json(slot / "return.json")
            elapsed.append(
                (
                    datetime.fromisoformat(end["completed_at"])
                    - datetime.fromisoformat(start["started_at"])
                ).total_seconds()
            )
        rows[name] = {
            "starts": len(elapsed),
            "valid": summary["judge_completed"],
            "selected": summary["selected"],
            "median_seconds_per_call": round(median(elapsed), 2),
            "dimensions": summary["dimensions"],
            "report_sha256": file_hash(directory / "report.json"),
        }
        missed[name] = {(r["item_id"], r["dimension"]) for r in summary["disagreements"]}
    changes = {}
    for before, after in ((PLAIN, ALONE), (PLAIN, CONTROL), (CONTROL, COMBINED)):
        changes[f"{before} to {after}"] = (
            {
                dim: {
                    "wrong_to_right": sum(d == dim for _, d in missed[before] - missed[after]),
                    "right_to_wrong": sum(d == dim for _, d in missed[after] - missed[before]),
                }
                for dim in rows[before]["dimensions"]
            }
            if rows[before]["valid"] == rows[after]["valid"] == 10
            else None
        )
    output = root / "analysis/devstral-unit4-layer-scoreboard-001.json"
    pin(
        output,
        {
            "development_only": True,
            "rows": rows,
            "paired_changes": changes,
            "spread": "One start per case and prompt. Run-to-run spread was not measured.",
        },
    )
    return {"scoreboard_sha256": file_hash(output), "paired_changes": changes}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("prepare", "score", "replay", "scoreboard"))
    p.add_argument("arm", choices=("plain", "examples"), nargs="?")
    args = p.parse_args()
    if (args.stage == "scoreboard") != (args.arm is None):
        p.error("Supply an arm for prepare, score or replay only.")
    result = (
        scoreboard(ROOT.resolve())
        if args.stage == "scoreboard"
        else run(ROOT.resolve(), PLAIN if args.arm == "plain" else ALONE, args.stage)
    )
    print(json.dumps(result, indent=2))
