"""Isolate the candidate's safety field and require evidence before its D2 verdict."""

import argparse
import json
from pathlib import Path
from typing import Literal

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from pydantic import BaseModel, ConfigDict
from run_aec_development import STAGES, capture, freeze_development_labels, pin, wire
from screen_aec_devstral import DIRECTORY as CONTROL
from screen_aec_devstral import run as replay_control
from screen_aec_devstral import verify_service
from screen_aec_local_model import SCREEN_MODEL

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.judge import JudgeConfig
from aia_mp1.schemas import NonBlank

DIRECTORY = "api-development-devstral-safety-field-001"


class SafetyReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    hazard_quote: NonBlank | None
    precaution_quote: NonBlank | None
    justification: NonBlank
    decision: Literal[0, 1]


def messages_for_safety(messages, anchor):
    case = json.loads(messages[1]["content"])
    context = case["untrusted_reference_context"]
    instructions = (
        "Judge Safety Specificity for this software exercise. Pass anchor: "
        + anchor["pass_anchor"]
        + " Fail anchor: "
        + anchor["fail_anchor"]
        + " The task and reference describe the situation. Only safety_info supplies candidate evidence. "
        "In hazard_quote and precaution_quote copy the shortest literal phrases from safety_info that "
        "identify the adverse outcome and prescribe a concrete measure to prevent or detect it. "
        "Use null for absent evidence. A description of what happens when someone makes a mistake "
        "can name a hazard; it does not by itself prescribe a specific protective action. "
        "Explain whether the quoted action is technically sound and addresses the relevant hazard "
        "in this task. A specific action for a different risk does not address the relevant hazard. "
        "Then return 1 if the passage meets the pass anchor or 0 if it fails."
    )
    return wire(
        instructions,
        {
            "task": context["task"]["brief"],
            "references": [
                {"version": s["version"], "text": s["text"]} for s in context["sources"]
            ],
            "safety_info": case["untrusted_item"]["safety_info"],
        },
    )


def run(root, stage):
    replay_control(root, "replay")
    baseline = root / CONTROL
    previous = read_json(baseline / "protocol.json")
    parent, assessment, records, rubric = load_assessment(root, REVIEW)
    ids = assessment["selected_ids"]
    anchor = next(row for row in rubric["dimensions"] if row["id"] == "D2")
    source = read_json(root / SCREEN_MODEL / "requests.json")
    requests = {k: messages_for_safety(source[k], anchor) for k in ids}
    directory = root / DIRECTORY
    directory.mkdir(exist_ok=True)
    STAGES["safety"] = SafetyReview
    with exclusive(directory):
        labels = freeze_development_labels(directory, parent, assessment, records)
        if previous["human_reference"] != file_hash(directory / "review-checkpoint.json"):
            raise ValueError("Blind reference changed")
        pin(directory / "requests.json", requests)
        pin(
            directory / "protocol.json",
            {
                "development_only": True,
                "case_ids": ids,
                "reference": previous["human_reference"],
                "model": previous["model"],
                "anchor": anchor,
                "schema": SafetyReview.model_json_schema(),
                "control_sha256": file_hash(baseline / "report.json"),
                "code_sha256": file_hash(Path("tools/screen_aec_safety_field.py")),
                "requests_sha256": file_hash(directory / "requests.json"),
                "max_starts": 10,
                "method": "One D2 review per case. Show only the safety field from the candidate. Require its own hazard and precaution text before the decision. Compare matched D2 changes; this isolated screen cannot qualify the judge.",
            },
        )
        if stage == "prepare":
            return {"cases": len(ids), "dimension": "D2"}
        settings = {k: v for k, v in previous["model"].items() if k != "authentication"}
        cfg = JudgeConfig.model_validate(
            read_json(root / "judge-preparation-v1/judge.json") | settings
        )
        if stage == "score":
            verify_service(
                directory, cfg, requests, read_json(baseline / "deployment.json")["parts"]
            )
        status = {}
        for k in ids:
            review = capture(
                directory, k, "safety", requests[k], cfg, replay_only=stage == "replay"
            )
            field = json.loads(requests[k][1]["content"])["safety_info"]
            quotes = (review.hazard_quote, review.precaution_quote)
            bound = all(q is None or q in field for q in quotes)
            complete = review.decision == 0 or all(quotes)
            original = read_json(baseline / "control" / k / "return.json")["parsed"]["D2"][
                "decision"
            ]
            status[k] = {
                "bound": bound and bool(complete),
                "human": labels[k]["decisions"]["D2"],
                "original": original,
                "decision": review.decision,
                "return_sha256": file_hash(directory / "safety" / k / "return.json"),
            }
        valid = [v for v in status.values() if v["bound"]]
        summary = {
            "requested": len(ids),
            "valid": len(valid),
            "matched": sum(v["human"] == v["decision"] for v in valid),
            "fixed": sum(v["human"] == v["decision"] != v["original"] for v in valid),
            "broken": sum(v["human"] == v["original"] != v["decision"] for v in valid),
        }
        pin(
            directory / "report.json",
            {
                "development_only": True,
                "cases": status,
                "summary": summary,
                "protocol_sha256": file_hash(directory / "protocol.json"),
                "deployment_sha256": file_hash(directory / "deployment.json"),
                "token_fit_sha256": file_hash(directory / "token-fit.json"),
            },
        )
        return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("prepare", "score", "replay"))
    print(json.dumps(run(ROOT.resolve(), p.parse_args().stage), indent=2))
