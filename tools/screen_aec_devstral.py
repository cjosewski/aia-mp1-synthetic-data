"""Measure Devstral on the ten original source-aware AEC development requests."""

import argparse
import json
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from run_aec_development import capture, freeze_development_labels, pin
from screen_aec_local_model import SCREEN_MODEL, screen

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.calibration import agreement
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.judge import JudgeConfig
from aia_mp1.tracing import digest

DIRECTORY = "api-development-devstral-001"
CANDIDATE_SHA = "38750a42167573aeff9715bdcb1aee10d87aa31ae9442deb66050b12033bbd81"
STORAGE = "/Volumes/DataDrive/MP1/Devstral-2-123B-Q4_K_M"


def verify_service(directory, config, requests, parts):
    deployment = read_json(directory / "deployment.json")
    if deployment["parts"] != parts or deployment["model"] != config.model:
        raise ValueError("Downloaded files differ from the candidate manifest")
    server = LocalServer(config.base_url, "local-only-placeholder")
    try:
        props = server.json("/props")
        if (
            props["model_path"] != config.model
            or props["build_info"] != deployment["build"]
            or props["total_slots"] != 1
            or props["default_generation_settings"]["n_ctx"] != 16384
        ):
            raise ValueError("Dedicated model service differs")
        fits = {
            k: server.token_fit(
                {"messages": messages, "max_tokens": config.max_tokens}, 16384, 2048
            )
            for k, messages in requests.items()
        }
        if not all(row["fits"] for row in fits.values()):
            raise ValueError("Input, output and schema reservation exceed the context")
        pin(directory / "token-fit.json", fits)
    finally:
        server.close()


def run(root, stage):
    candidate_path = root / "api-devstral-candidate-preparation-001/candidate.json"
    if file_hash(candidate_path) != CANDIDATE_SHA:
        raise ValueError("Devstral candidate manifest differs")
    candidate = read_json(candidate_path)
    model = f"{STORAGE}/{Path(candidate['parts'][0]['file']).name}"
    cfg = JudgeConfig.model_validate(
        read_json(root / "judge-preparation-v1/judge.json")
        | {
            "model": model,
            "model_identity": f"{candidate['distribution']}@{candidate['distribution_revision']}/Q4_K_M",
            "model_sha256": digest(candidate["parts"]),
            "max_attempts": 1,
            "qualification_path": None,
            "stronger_model_basis": "Candidate for development testing based on software engineering specialization.",
            "prompt_variant": "aec-api-correctness-v3",
            "prompt_path": "prompts/aec-api-correctness-judge-v3.md",
        }
    )
    parent, assessment, records, _ = load_assessment(root, REVIEW)
    matched = screen(root, False)
    requests = read_json(root / SCREEN_MODEL / "requests.json")
    ids = assessment["selected_ids"]
    if (
        set(requests) != set(ids)
        or len(ids) != 10
        or cfg.temperature != 0.1
        or cfg.temperature >= assessment["generator_temperature"]
        or cfg.base_url != "http://127.0.0.1:18082/v1"
    ):
        raise ValueError("Unexpected selection, settings or endpoint")
    directory = root / DIRECTORY
    directory.mkdir(exist_ok=True)
    with exclusive(directory):
        labels = freeze_development_labels(directory, parent, assessment, records)
        reference = file_hash(directory / "review-checkpoint.json")
        if reference != file_hash(root / SCREEN_MODEL / "review-checkpoint.json"):
            raise ValueError("Blind development reference differs")
        protocol = pin(
            directory / "protocol.json",
            {
                "development_only": True,
                "case_ids": ids,
                "model": cfg.public_settings(),
                "candidate_sha256": CANDIDATE_SHA,
                "requests_sha256": matched["requests_sha256"],
                "human_reference": reference,
                "max_starts": 10,
                "attempts_per_case": 1,
                "advance_rule": "All ten valid, at least eight matches in each dimension and no material explanation error.",
                "code": {
                    str(p): file_hash(p)
                    for p in (
                        Path("tools/screen_aec_devstral.py"),
                        Path("tools/run_aec_development.py"),
                        Path("src/aia_mp1/model_client.py"),
                        Path("src/aia_mp1/evaluation_schemas.py"),
                    )
                },
            },
        )
        if stage == "prepare":
            return {"cases": len(ids), "protocol_sha256": digest(protocol)}
        if stage == "score":
            verify_service(directory, cfg, requests, candidate["parts"])
        results, failures = {}, {}
        returns = {}
        for key in ids:
            slot = directory / "control" / key
            try:
                result = capture(
                    directory, key, "control", requests[key], cfg, replay_only=stage == "replay"
                )
                results[key] = result.model_dump()
            except ValueError:
                # Only a recorded transport or parse failure can count as a known failed trial.
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
            returns[key] = file_hash(slot / "return.json")
        summary = agreement([r for r in records if r["item_id"] in ids], ids, labels, results)
        report = pin(
            directory / "report.json",
            {
                "development_only": True,
                "protocol_sha256": digest(protocol),
                "summary": summary,
                "deployment_sha256": file_hash(directory / "deployment.json"),
                "returns": returns,
                "token_fit_sha256": file_hash(directory / "token-fit.json"),
                "failures": failures,
            },
        )
        return {
            "valid": len(results),
            "matches": {k: v["matching"] for k, v in summary["dimensions"].items()},
            "report_sha256": digest(report),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "score", "replay"))
    print(json.dumps(run(ROOT.resolve(), parser.parse_args().stage), indent=2))
