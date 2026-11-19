"""Test the pre-inference task notes on ten development cases against the frozen control."""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW, prepare_review
from run_aec_development import DIRECTORY, PROMPTS, capture, freeze_development_labels, pin, wire

from aia_mp1.aec_development import checked_judgment
from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json, read_text
from aia_mp1.calibration import agreement
from aia_mp1.judge import JudgeConfig, messages_for
from aia_mp1.passage_evidence import passage_input
from aia_mp1.tracing import digest

NOTES_HASH = "0c35dbc0e9e8c7786ea842c115c66d152b096ba4ac3646c5a1a8506150b480dc"
ORIGINAL_PROTOCOL = "717cff011212faf45fb3358085afd08df5e20fa97cc2459b75879c34f8791e65"
SCREEN = "api-development-task-notes-001"


def run(root, *, score):
    prior = root / DIRECTORY
    notes = read_json(prior / "task-audit-criteria.json")
    selection = prepare_review(root)
    ids = selection["selected_ids"]
    first_start = read_json(prior / "reference" / ids[0] / "start.json")
    if (
        file_hash(prior / "protocol.json") != ORIGINAL_PROTOCOL
        or file_hash(prior / "task-audit-criteria.json") != NOTES_HASH
        or set(notes["cases"]) != set(ids)
        or notes["inputs_sha256"].lower() != file_hash(prior / "reference-inputs.json")
        or datetime.fromisoformat(notes["timestamp"])
        >= datetime.fromisoformat(first_start["started_at"])
    ):
        raise ValueError("Task notes or their pre-inference provenance differ")
    original = read_json(prior / "protocol.json")
    if any(file_hash(Path(path)) != expected for path, expected in original["code"].items()):
        raise ValueError("Original scoring code differs")
    cfg = JudgeConfig.model_validate(read_json(root / "judge-preparation-v1/judge.json"))
    if cfg.public_settings() != original["judge"] or cfg.base_url != "http://127.0.0.1:18082/v1":
        raise ValueError("Development judge differs from the control")
    parent, assessment, records, rubric = load_assessment(root, REVIEW)
    prompt = read_text(PROMPTS["comparison"])
    if prompt != original["prompts"]["comparison"] or selection != original["review"]:
        raise ValueError("Comparison rubric, selected items or instruction changed")
    by_id = {r["item_id"]: r for r in records}
    directory = root / SCREEN
    directory.mkdir(exist_ok=True)
    with exclusive(directory):
        pin(
            directory / "protocol.json",
            {
                "original_protocol_sha256": ORIGINAL_PROTOCOL,
                "task_notes_sha256": NOTES_HASH,
                "selection": selection,
                "code_sha256": file_hash(Path(__file__)),
                "judge": cfg.public_settings(),
                "method": "Use each sentence from the task-only technical notes recorded before the first reference request. Scope qualifications describe acceptable alternatives. The scorer must examine the original task and may challenge a note.",
                "max_starts": 10,
                "attempts_per_case": 1,
                "control": "Reuse unchanged v3 development arm.",
                "advance_rule": original["advance_rule"],
                "assessed": False,
            },
        )
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(prior / "review-checkpoint.json") != file_hash(
            directory / "review-checkpoint.json"
        ):
            raise ValueError("Development arms differ on human reference")
        packets, judgments = {}, {}
        for key in ids:
            messages = messages_for(prompt, rubric, by_id[key])
            content = passage_input(json.loads(messages[1]["content"]), rubric)
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", notes["cases"][key])
            checks = [{"id": f"T{n}", "text": sentence} for n, sentence in enumerate(sentences, 1)]
            packets[key] = {
                "messages": wire(messages[0]["content"], content | {"task_checklist": checks}),
                "content": content,
                "checks": checks,
            }
        pin(directory / "requests.json", packets)
        if not score:
            return {
                "sealed": len(packets),
                "request_sha256": file_hash(directory / "requests.json"),
            }
        for key, p in packets.items():
            result = capture(directory, key, "comparison", p["messages"], cfg)
            judgments[key] = checked_judgment(
                result, p["content"], rubric, p["checks"]
            ).model_dump()
        summary = agreement([by_id[k] for k in ids], ids, labels, judgments)
        receipt = pin(
            directory / "report.json",
            {
                "development_only": True,
                "summary": summary,
                "requests_sha256": file_hash(directory / "requests.json"),
                "human_reference_checkpoint": file_hash(directory / "review-checkpoint.json"),
                "returns": {
                    k: file_hash(directory / "comparison" / k / "return.json") for k in ids
                },
            },
        )
        return {
            "sha256": digest(receipt),
            "matches": {d: v["matching"] for d, v in summary["dimensions"].items()},
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "score"))
    print(json.dumps(run(ROOT.resolve(), score=parser.parse_args().stage == "score"), indent=2))
