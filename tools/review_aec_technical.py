"""Recheck API correctness, context and tips against task-selected primary excerpts."""

import argparse
import json
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from pydantic import BaseModel, ConfigDict
from review_aec_qwen_control import DIRECTORY as SECOND
from review_aec_qwen_control import Review
from run_aec_development import DIRECTORY as CONTROL
from run_aec_development import STAGES, capture, freeze_development_labels, pin, wire
from screen_aec_devstral import verify_service
from screen_aec_local_model import SCREEN_MODEL
from screen_aec_sources import task_sources

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.calibration import agreement
from aia_mp1.canonical_development import QWEN_FILES, QWEN_MODEL_SHA
from aia_mp1.judge import JudgeConfig

DIRECTORY = "api-development-qwen-technical-review-001"
DIMS = ("D3", "D5", "D6")
PROMPT = """Review the previous judge's three decisions for one software exercise. Separate the original brief, reference excerpts, candidate and earlier opinion. The candidate is the only proposed answer. Source excerpts establish facts about the specified version but may be incomplete. Read the task before comparing the proposal with it.

For D3 identify the decisive operation and trace the receiver, input or state, call, result and claimed behavior. A real method on the wrong object or a runnable solution to a different problem can fail. An optional improvement, missing insurance or an undocumented detail alone does not establish failure. Use the exact code and numerical values where they decide the question. Inspect API recommendations in all candidate fields.

For D5 reconstruct the problem actually described by the question, equipment problem and answer. Compare its symptom, relevant state and intended result with the brief. Identify any substitution or ambiguity. An API defect by itself does not make a clear problem unclear.

For D6 inspect each numbered tip against the existing steps and the versioned facts. In the justification account for every tip by number. Identify an actionable addition and why it helps, a repetition, a tangential suggestion or a misleading recommendation. Distinguish harmless repetition alongside a useful tip from technical advice that would mislead the user.

For each dimension give a short factual justification before the binary decision. Acknowledge a material flaw in the previous opinion when warranted. Apply the provided anchors independently. Never claim execution."""


class TechnicalReview(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    D3: Review
    D5: Review
    D6: Review


def technical_packet(messages, previous, anchors, cards):
    case = json.loads(messages[1]["content"])
    context = case["untrusted_reference_context"]
    task = context["task"]
    card = cards[task["id"]]
    if card["brief"] != task["brief"]:
        raise ValueError("Task evidence differs")
    return wire(
        PROMPT,
        {
            "rubric": [
                {
                    k: v
                    for k, v in anchors[d].items()
                    if k in {"name", "id", "pass_anchor", "fail_anchor"}
                }
                for d in DIMS
            ],
            "brief": task["brief"],
            "source_profiles": [
                {"version": s["version"], "summary": s["text"]} for s in context["sources"]
            ],
            "primary_excerpts": [
                {
                    "path": s["path"],
                    "first_line": s["first"],
                    "last_line": s["last"],
                    "text": s["text"],
                }
                for s in card["excerpts"]
            ],
            "candidate": case["untrusted_item"],
            "previous_opinion": {d: previous[d] for d in DIMS},
        },
    )


def run(root, stage):
    directory = root / DIRECTORY
    directory.mkdir(exist_ok=True)
    parent, assessment, records, rubric = load_assessment(root, REVIEW)
    previous = read_json(root / SECOND / "protocol.json")
    cfg = JudgeConfig.model_validate(read_json(root / "judge-preparation-v1/judge.json"))
    if cfg.public_settings() != previous["settings"] or cfg.model_sha256 != QWEN_MODEL_SHA:
        raise ValueError("Different judge configuration")
    ids = assessment["selected_ids"]
    original = read_json(root / SCREEN_MODEL / "requests.json")
    before = {
        k: capture(root / CONTROL, k, "control", original[k], cfg, replay_only=True).model_dump()
        for k in ids
    }
    cards = task_sources(root)
    anchors = {a["id"]: a for a in rubric["dimensions"]}
    with exclusive(directory):
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(directory / "review-checkpoint.json") != previous["human_reference"]:
            raise ValueError("Different human reference")
        requests = {k: technical_packet(original[k], before[k], anchors, cards) for k in ids}
        pin(directory / "requests.json", requests)
        pin(
            directory / "protocol.json",
            {
                "development_only": True,
                "case_ids": ids,
                "dimensions": list(DIMS),
                "model": cfg.public_settings(),
                "schema": TechnicalReview.model_json_schema(),
                "reference": previous["human_reference"],
                "control_sha256": file_hash(root / CONTROL / "control-report.json"),
                "max_starts": 10,
                "requests_sha256": file_hash(directory / "requests.json"),
                "code": {
                    str(p): file_hash(p)
                    for p in (
                        Path("tools/review_aec_technical.py"),
                        Path("tools/review_aec_qwen_control.py"),
                        Path("tools/screen_aec_sources.py"),
                        Path("tools/run_aec_development.py"),
                    )
                },
                "method": "Re-evaluate D3/D5/D6 on all ten answers. Use task-only retrieval from pinned primary sources and the previous public opinion. Report each dimension separately; this component alone cannot qualify the complete judge.",
            },
        )
        if stage == "prepare":
            return {"requests": len(requests), "dimensions": list(DIMS)}
        dep = read_json(directory / "deployment.json")
        if dep["parts"] != QWEN_FILES or dep["reasoning_budget"] != 4096:
            raise ValueError("Different deployment")
        if stage == "score":
            verify_service(directory, cfg, requests, QWEN_FILES)
        STAGES["technical"] = TechnicalReview
        results = {k: dict(v) for k, v in before.items()}
        paired = {d: {"fixed": 0, "broken": 0} for d in DIMS}
        returns = {}
        for k in ids:
            reviewed = capture(
                directory, k, "technical", requests[k], cfg, replay_only=stage == "replay"
            ).model_dump()
            results[k].update(reviewed)
            returns[k] = file_hash(directory / "technical" / k / "return.json")
            for d in DIMS:
                decision = reviewed[d]["decision"]
                if decision != before[k][d]["decision"]:
                    paired[d]["fixed" if labels[k]["decisions"][d] == decision else "broken"] += 1
        s = agreement([r for r in records if r["item_id"] in ids], ids, labels, results)
        metrics = {d: s["dimensions"][d] for d in DIMS}
        pin(
            directory / "report.json",
            {
                "development_only": True,
                "dimensions": metrics,
                "compared": len(ids),
                "paired": paired,
                "returns": returns,
                "protocol_sha256": file_hash(directory / "protocol.json"),
                "deployment_sha256": file_hash(directory / "deployment.json"),
                "token_fit_sha256": file_hash(directory / "token-fit.json"),
            },
        )
        return {"matches": {d: m["matching"] for d, m in metrics.items()}, "changes": paired}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("prepare", "score", "replay"))
    print(json.dumps(run(ROOT.resolve(), p.parse_args().stage), indent=2))
