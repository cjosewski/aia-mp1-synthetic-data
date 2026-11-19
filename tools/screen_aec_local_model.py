"""Compare the pinned GPT-OSS candidate with the ten-case Qwen control on identical inputs."""

import argparse
import json
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW, prepare_review
from run_aec_development import DIRECTORY, capture, freeze_development_labels, pin

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.calibration import agreement
from aia_mp1.judge import JudgeConfig
from aia_mp1.tracing import digest

SCREEN_MODEL = "api-development-gptoss120b-001"
WEIGHTS = "582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d"


def screen(root, score):
    selection = prepare_review(root)
    parent, assessment, records, _ = load_assessment(root, REVIEW)
    prior = root / DIRECTORY
    control = read_json(prior / "control-report.json")
    if not control["summary"]["coverage_complete"] or control["summary"]["selected"] != 10:
        raise ValueError("Complete matched development control required")
    earlier = root.parent / "qualification"
    historical = read_json(earlier / "MP1-GPTOSS120B-V9R1-MAC/plan.json")
    audit_path = earlier / "mp1-gptoss120b-v9r1-return-audit/audit.json"
    prior_measurement = read_json(audit_path)["all_ten"]
    if (
        historical["model_sha256"] != WEIGHTS
        or prior_measurement["matches"] != 56
        or prior_measurement["selected_decisions"] != 60
    ):
        raise ValueError("Historical model fingerprint differs")
    cfg_data = read_json(root / "judge-preparation-v1/judge.json") | {
        "model": historical["model"],
        "model_sha256": WEIGHTS,
        "model_identity": f"gpt-oss-120b-MXFP4@sha256:{WEIGHTS}",
        **historical["settings"],
        "max_attempts": 1,
        "qualification_path": None,
        "stronger_model_basis": "Development nominee with 56/60 on a separate historical engineering screen. This new comparison measures fit to the AEC rubric.",
        "prompt_variant": "aec-api-correctness-v3",
        "prompt_path": "prompts/aec-api-correctness-judge-v3.md",
    }
    cfg = JudgeConfig.model_validate(cfg_data)
    if (
        cfg.base_url != "http://127.0.0.1:18082/v1"
        or cfg.temperature != 0.1
        or cfg.reasoning_effort != "high"
    ):
        raise ValueError("Unexpected development settings")
    directory = root / SCREEN_MODEL
    directory.mkdir(exist_ok=True)
    ids = selection["selected_ids"]
    with exclusive(directory):
        pin(
            directory / "protocol.json",
            {
                "development_only": True,
                "case_ids": ids,
                "model": cfg.public_settings(),
                "selection": selection,
                "historical_evidence": file_hash(audit_path),
                "matched_control": file_hash(prior / "control-report.json"),
                "max_starts": 10,
                "attempts_per_case": 1,
                "prompt": "Identical original Qwen v3 control messages.",
                "advance_rule": "Full coverage, at least 8/10 in each dimension, equal or better D1 and D6 than the matched control, and no material fault in the explanation audit.",
                "code": {
                    str(p): file_hash(p)
                    for p in [
                        Path(__file__),
                        Path("tools/run_aec_development.py"),
                        Path("src/aia_mp1/model_client.py"),
                        Path("src/aia_mp1/evaluation_schemas.py"),
                    ]
                },
            },
        )
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(directory / "review-checkpoint.json") != file_hash(
            prior / "review-checkpoint.json"
        ):
            raise ValueError("Different human reference")
        requests = {}
        for key in ids:
            q = prior / "control" / key
            if control["returns"][key] != file_hash(q / "return.json") or read_json(
                q / "return.json"
            )["start_sha256"] != file_hash(q / "start.json"):
                raise ValueError("Control return or original request differs")
            start = read_json(q / "start.json")
            if digest({"messages": start["messages"]}) != start["identity"]["messages_sha256"]:
                raise ValueError("Control input differs")
            requests[key] = start["messages"]
        pin(directory / "requests.json", requests)
        if not score:
            return {
                "cases": len(requests),
                "requests_sha256": file_hash(directory / "requests.json"),
            }
        if read_json(directory / "model-preflight.json").get("observed_model_sha256") != WEIGHTS:
            raise ValueError("Live machine weight verification required")
        results = {k: capture(directory, k, "control", requests[k], cfg).model_dump() for k in ids}
        summary = agreement([r for r in records if r["item_id"] in ids], ids, labels, results)
        report = pin(
            directory / "report.json",
            {
                "development_only": True,
                "summary": summary,
                "human_reference": file_hash(directory / "review-checkpoint.json"),
                "requests_sha256": file_hash(directory / "requests.json"),
                "returns": {
                    k: file_hash(directory / "control" / k / "return.json") for k in results
                },
            },
        )
        return {
            "sha256": digest(report),
            "matches": {d: v["matching"] for d, v in summary["dimensions"].items()},
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "score"))
    print(json.dumps(screen(ROOT.resolve(), parser.parse_args().stage == "score"), indent=2))
