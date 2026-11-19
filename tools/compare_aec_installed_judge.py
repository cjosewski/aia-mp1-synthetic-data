"""Screen an installed model against the frozen local AEC development control."""

import argparse
import json
import re
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW, prepare_review
from run_aec_development import capture, freeze_development_labels, pin
from screen_aec_local_model import SCREEN_MODEL, screen

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.calibration import agreement
from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.judge import JudgeConfig
from aia_mp1.tracing import digest

NEMOTRON = "NVIDIA-Nemotron-3.5-Super-VL-120B-A12B"
CANDIDATES = {
    "nemotron": [f"{NEMOTRON}-Q4_K_M-0000{i}-of-00002.gguf" for i in (1, 2)],
    "gptoss20b": ["gpt-oss-20b-MXFP4.gguf"],
    "llama70b": ["Llama-3.3-70B-Instruct-Q4_K_M.gguf"],
}
HISTORICAL = {
    "gptoss20b": ("MP1-GPTOSS-V7-MAC", "gptoss-v7-return-review-20261113"),
    "llama70b": ("MP1-LLAMA-V7-MAC", "llama-v7-return-review-20261113"),
}


def configuration(root, name, deployment):
    parts = deployment["parts"]
    model = deployment["model"]
    if (
        [Path(part["path"]).name for part in parts] != CANDIDATES[name]
        or any(not re.fullmatch("[0-9a-f]{64}", part["sha256"]) for part in parts)
        or model != parts[0]["path"]
        or deployment["build"] != "b12110-cd959bae9"
        or deployment["context"] != 16384
        or deployment["slots"] != 1
    ):
        raise ValueError("Model parts, runtime or served model differ")
    identity = parts[0]["sha256"] if len(parts) == 1 else digest(parts)
    basis = "Distinct locally installed 120B Nemotron family. Its AEC calibration is unmeasured."
    if name in HISTORICAL:
        plan, audit = HISTORICAL[name]
        archive = root.parent / "qualification"
        if read_json(archive / plan / "development-plan.json")["weight_sha256"] != identity:
            raise ValueError("Model differs from earlier local screen")
        data = read_json(archive / audit / "audit.json")["summary"]
        basis = f"Matched {data['matches']}/{data['criterion_comparisons']} decisions on earlier engineering examples. This screen tests the AEC rubric."
    return JudgeConfig.model_validate(
        read_json(root / "judge-preparation-v1/judge.json")
        | {
            "model": model,
            "model_sha256": identity,
            "model_identity": f"{name}@{identity}",
            "stronger_model_basis": basis,
            "qualification_path": None,
            "max_attempts": 1,
            "prompt_variant": "aec-api-correctness-v3",
            "prompt_path": "prompts/aec-api-correctness-judge-v3.md",
            "reasoning_effort": "high" if name == "gptoss20b" else None,
        }
    )


def run(root, name, score):
    ids = prepare_review(root)["selected_ids"]
    frozen = screen(root, False)
    prior = root / SCREEN_MODEL
    packets = read_json(prior / "requests.json")
    parent, assessment, records, _ = load_assessment(root, REVIEW)
    directory = root / f"api-development-{name}-001"
    deployment_path = directory / "deployment.json"
    with exclusive(directory):
        cfg = configuration(root, name, read_json(deployment_path))
        if (
            cfg.base_url != "http://127.0.0.1:18082/v1"
            or cfg.temperature >= assessment["generator_temperature"]
        ):
            raise ValueError("Unexpected local endpoint or temperature")
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(directory / "review-checkpoint.json") != file_hash(
            prior / "review-checkpoint.json"
        ):
            raise ValueError("Development reference differs")
        pin(
            directory / "protocol.json",
            {
                "development_only": True,
                "model": cfg.public_settings(),
                "deployment": file_hash(deployment_path),
                "case_ids": ids,
                "matched_inputs": frozen["requests_sha256"],
                "matched_control": file_hash(prior / "report.json"),
                "attempts_per_case": 1,
                "max_starts": 10,
                "rule": "Use the original v3 requests. Stop on an unresolved return or three disagreements in any dimension. All six require at least eight matches and an explanation audit to advance.",
                "code": {
                    str(p): file_hash(p)
                    for p in [
                        Path(__file__),
                        Path("tools/screen_aec_local_model.py"),
                        Path("tools/run_aec_development.py"),
                        Path("src/aia_mp1/model_client.py"),
                    ]
                },
            },
        )
        if not score:
            return frozen
        results, reason = {}, None
        for key in ids:
            try:
                results[key] = capture(directory, key, "control", packets[key], cfg).model_dump()
            except ValueError as exc:
                reason = f"{key}: {exc}"
                break
            missed = [
                d
                for d in DIMENSIONS
                if sum(r[d]["decision"] != labels[k]["decisions"][d] for k, r in results.items())
                > 2
            ]
            if missed:
                reason = "Cannot reach 8/10 on " + ", ".join(missed)
                break
        summary = agreement([r for r in records if r["item_id"] in ids], ids, labels, results)
        pin(
            directory / "report.json",
            {
                "development_only": True,
                "halt": reason,
                "summary": summary,
                "human_reference": file_hash(directory / "review-checkpoint.json"),
                "returns": {
                    p.parent.name: file_hash(p)
                    for p in sorted((directory / "control").glob("*/return.json"))
                },
            },
        )
        return {
            "valid": len(results),
            "halt": reason,
            "matches": {d: v["matching"] for d, v in summary["dimensions"].items()},
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=CANDIDATES)
    parser.add_argument("stage", choices=("prepare", "score"))
    args = parser.parse_args()
    print(json.dumps(run(ROOT.resolve(), args.model, args.stage == "score"), indent=2))
