"""Run or replay the ten-item local comparison on the frozen source-free AEC inputs."""

import argparse
import json
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from prepare_aec_source_free import build
from run_aec_development import capture, freeze_development_labels, pin

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json, read_text
from aia_mp1.calibration import agreement
from aia_mp1.canonical_development import QWEN_FILES, QWEN_MODEL_SHA, QWEN_SETTINGS, wire_for
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.judge import JudgeConfig
from aia_mp1.tracing import digest

DIRECTORY = "api-development-qwen-source-free-001"


def run(root, replay):
    packet = build(root)
    bundle = root / "api-source-free-preparation-001"
    rows = json.loads(read_text(bundle / "development-requests.json"))
    directory = root / DIRECTORY
    config = JudgeConfig.model_validate(read_json(root / "judge-preparation-v1/judge.json"))
    parent, assessment, records, _ = load_assessment(root, REVIEW)
    ids = [r["item_id"] for r in rows]
    deployment = read_json(directory / "deployment.json")
    if (
        ids != assessment["selected_ids"]
        or len(ids) != 10
        or config.model != deployment["model"]
        or config.model_sha256 != QWEN_MODEL_SHA
        or deployment["shards"] != QWEN_FILES
        or config.base_url != "http://127.0.0.1:18082/v1"
        or config.temperature >= assessment["generator_temperature"]
        or any(getattr(config, k) != v for k, v in QWEN_SETTINGS.items())
    ):
        raise ValueError("Unexpected selection, model, endpoint or settings")
    with exclusive(directory):
        pin(
            directory / "protocol.json",
            {
                "development_only": True,
                "case_ids": ids,
                "model": config.public_settings(),
                "deployment_sha256": file_hash(directory / "deployment.json"),
                "packet": packet["inputs"]["development"],
                "max_starts": 10,
                "attempts_per_case": 1,
                "hypothesis": "Measure the same local Qwen judge on the ten source-free application messages prepared for the possible hosted comparison.",
                "advance_rule": "All ten valid, at least 8/10 in each dimension and an independent explanation audit. Collect every available matched case once to measure the difference from the earlier control.",
                "code": {
                    str(p): file_hash(p)
                    for p in [
                        Path(__file__),
                        Path("tools/run_aec_development.py"),
                        Path("src/aia_mp1/model_client.py"),
                    ]
                },
            },
        )
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(directory / "review-checkpoint.json") != packet["development_reference"]:
            raise ValueError("Frozen development reviews differ")
        if not replay:
            server = LocalServer(config.base_url, "local-only-placeholder")
            try:
                props = server.json("/props")
                if (
                    props["build_info"] != deployment["build"]
                    or props["model_path"] != config.model
                    or props["total_slots"] != 1
                    or props["default_generation_settings"]["n_ctx"] != 16384
                ):
                    raise ValueError("Dedicated model service differs")
                plan = {
                    "protocol": "qwen35-canonical-development",
                    "model": config.model,
                    "settings": QWEN_SETTINGS,
                }
                fits = {r["item_id"]: server.token_fit(wire_for(plan, r), 16384, 64) for r in rows}
                if not all(r["fits"] for r in fits.values()):
                    raise ValueError("Context budget exceeded")
                pin(directory / "token-fit.json", fits)
            finally:
                server.close()
        results, failures = {}, {}
        for row in rows:
            k = row["item_id"]
            if digest({"messages": row["messages"]}) != row["messages_sha256"]:
                raise ValueError("Frozen application messages differ")
            try:
                results[k] = capture(
                    directory, k, "control", row["messages"], config, replay_only=replay
                ).model_dump()
            except ValueError as error:
                slot = directory / "control" / k
                if not (slot / "return.json").is_file():
                    raise
                returned = read_json(slot / "return.json")
                if (
                    not returned.get("error_type")
                    or returned.get("parsed") is not None
                    or returned.get("start_sha256") != file_hash(slot / "start.json")
                    or returned.get("sha256")
                    != digest({key: value for key, value in returned.items() if key != "sha256"})
                ):
                    raise
                failures[k] = str(error)
        summary = agreement([r for r in records if r["item_id"] in ids], ids, labels, results)
        report = pin(
            directory / "report.json",
            {
                "development_only": True,
                "summary": summary,
                "failures": failures,
                "human_reference": file_hash(directory / "review-checkpoint.json"),
                "returns": {k: file_hash(directory / "control" / k / "return.json") for k in ids},
            },
        )
        return {
            "valid": len(results),
            "matches": [v["matching"] for v in summary["dimensions"].values()],
            "digest": digest(report),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("score", "replay"))
    print(json.dumps(run(ROOT.resolve(), parser.parse_args().stage == "replay"), indent=2))
