"""Recheck Qwen's original completeness and safety ratings against their source evidence."""

import argparse
import json
from pathlib import Path
from typing import Literal

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from pydantic import BaseModel, ConfigDict
from run_aec_development import DIRECTORY as CONTROL
from run_aec_development import STAGES, capture, freeze_development_labels, pin, wire
from run_aec_scoped_review import CATALOG_HASH, requirements
from screen_aec_local_model import SCREEN_MODEL, screen

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.calibration import agreement
from aia_mp1.canonical_development import QWEN_FILES, QWEN_MODEL_SHA, QWEN_SETTINGS
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.judge import JudgeConfig
from aia_mp1.schemas import NonBlank
from aia_mp1.tracing import digest

DIRECTORY = "api-development-qwen-grounded-review-001"
FOCUS = {
    "D1": "Check the prior review against the specified deliverables one at a time. Identify the decisive completed or omitted action and what the candidate actually supplies. A statement of the goal does not execute it. When the proposed method cannot reach a requested output, identify why. Accept equivalent working routes and respect givens, optional checks and the requested level of detail.",
    "D2": "Check what the safety field itself tells the user to do and which concrete adverse outcome that action prevents. Test the causal connection and technical correctness against this task. When a warning describes a failure, distinguish that warning from an instruction which the user can actually follow to prevent or detect it. Explain any general, unrelated or technically faulty precaution.",
}


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    justification: NonBlank
    decision: Literal[0, 1]


def packet(source, prior, anchor, catalog):
    case = json.loads(source[1]["content"])
    task = case["untrusted_reference_context"]["task"]
    item = case["untrusted_item"]
    dim = anchor["id"]
    data = {
        "task": task["brief"],
        "software": [
            {"version": s["version"], "reference": s["text"]}
            for s in case["untrusted_reference_context"]["sources"]
        ],
    }
    if dim == "D1":
        data["task_checks"], data["optional_scope"] = requirements(task, catalog)
        data["candidate"] = item
    else:
        data["candidate_safety_info"] = item["safety_info"]
    data["prior_review_to_audit"] = prior[dim]
    return wire(
        f"Independently re-evaluate {anchor['name']}. The previous review is a fallible opinion. "
        f"Use the source and candidate to test its claims. Pass: {anchor['pass_anchor']} "
        f"Fail: {anchor['fail_anchor']} {FOCUS[dim]} Give a concise checkable justification, "
        "then a fresh binary decision. Only the candidate supplies the proposed solution. "
        "A reference or an earlier review supplies no missing candidate action.",
        data,
    )


def run(root, stage):
    screen(root, False)
    parent, assessment, records, rubric = load_assessment(root, REVIEW)
    ids = assessment["selected_ids"]
    originals = read_json(root / SCREEN_MODEL / "requests.json")
    cfg = JudgeConfig.model_validate(read_json(root / "judge-preparation-v1/judge.json"))
    if (
        cfg.model_sha256 != QWEN_MODEL_SHA
        or cfg.temperature >= assessment["generator_temperature"]
        or cfg.base_url != "http://127.0.0.1:18082/v1"
        or any(getattr(cfg, k) != v for k, v in QWEN_SETTINGS.items())
    ):
        raise ValueError("Unexpected Qwen settings")
    catalog = read_json(root / "api-development-task-notes-001/task-catalog.json")
    if digest({k: v for k, v in catalog.items() if k != "sha256"}) != CATALOG_HASH:
        raise ValueError("Frozen task catalog differs")
    control = root / CONTROL
    prior = {
        k: capture(control, k, "control", originals[k], cfg, replay_only=True).model_dump()
        for k in ids
    }
    anchors = {a["id"]: a for a in rubric["dimensions"]}
    requests = {
        dim: {k: packet(originals[k], prior[k], anchors[dim], catalog["tasks"]) for k in ids}
        for dim in FOCUS
    }
    directory = root / DIRECTORY
    directory.mkdir(exist_ok=True)
    with exclusive(directory):
        labels = freeze_development_labels(directory, parent, assessment, records)
        reference = file_hash(directory / "review-checkpoint.json")
        if reference != file_hash(control / "review-checkpoint.json"):
            raise ValueError("Original human reference differs")
        pin(directory / "requests.json", requests)
        pin(
            directory / "protocol.json",
            {
                "development_only": True,
                "case_ids": ids,
                "human_reference": reference,
                "settings": cfg.public_settings(),
                "response_schema": Review.model_json_schema(),
                "control_sha256": file_hash(control / "control-report.json"),
                "task_catalog": CATALOG_HASH,
                "requests_sha256": file_hash(directory / "requests.json"),
                "code": {
                    str(p): file_hash(p)
                    for p in (
                        Path("tools/review_aec_qwen_control.py"),
                        Path("tools/run_aec_development.py"),
                        Path("tools/run_aec_scoped_review.py"),
                        Path("src/aia_mp1/model_client.py"),
                    )
                },
                "max_starts": 20,
                "attempts_per_case_per_dimension": 1,
                "rule": "Replace D1 and D2 for every case with an independent second review. Preserve the original D3-D6. Require ten complete judgments, at least eight matches in every dimension and a satisfactory explanation audit before assessment.",
            },
        )
        if stage == "prepare":
            return {"cases": len(ids), "second_reviews": sum(map(len, requests.values()))}
        deployment = read_json(directory / "deployment.json")
        if (
            deployment["model"] != cfg.model
            or deployment["shards"] != QWEN_FILES
            or deployment["reasoning_budget"] != 4096
        ):
            raise ValueError("Qwen deployment differs")
        if stage == "score":
            server = LocalServer(cfg.base_url, "local-only-placeholder")
            try:
                props = server.json("/props")
                if (
                    props["model_path"] != cfg.model
                    or props["total_slots"] != 1
                    or props["build_info"] != deployment["build"]
                    or props["default_generation_settings"]["n_ctx"] != 16384
                ):
                    raise ValueError("Unexpected model service")
                fits = {
                    f"{k}.{dim}": server.token_fit(
                        {"messages": m, "max_tokens": cfg.max_tokens}, 16384, 2048
                    )
                    for dim, batch in requests.items()
                    for k, m in batch.items()
                }
                if not all(v["fits"] for v in fits.values()):
                    raise ValueError("Context exceeds reservation")
                pin(directory / "token-fit.json", fits)
            finally:
                server.close()
        results = {k: dict(prior[k]) for k in ids}
        changes = {dim: {"fixed": 0, "broken": 0} for dim in FOCUS}
        returns = {}
        for dim, batch in requests.items():
            STAGES[dim] = Review
            for k, m in batch.items():
                reviewed = capture(
                    directory, k, dim, m, cfg, replay_only=stage == "replay"
                ).model_dump()
                returns[f"{dim}.{k}"] = file_hash(directory / dim / k / "return.json")
                previous = prior[k][dim]["decision"]
                if previous != reviewed["decision"]:
                    direction = "broken" if labels[k]["decisions"][dim] == previous else "fixed"
                    changes[dim][direction] += 1
                results[k][dim] = reviewed
        summary = agreement([r for r in records if r["item_id"] in ids], ids, labels, results)
        pin(
            directory / "report.json",
            {
                "development_only": True,
                "summary": summary,
                "paired": changes,
                "returns": returns,
                "protocol_sha256": file_hash(directory / "protocol.json"),
                "deployment_sha256": file_hash(directory / "deployment.json"),
                "token_fit_sha256": file_hash(directory / "token-fit.json"),
            },
        )
        return {
            "matches": {d: v["matching"] for d, v in summary["dimensions"].items()},
            "changes": changes,
        }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("prepare", "score", "replay"))
    print(json.dumps(run(ROOT.resolve(), p.parse_args().stage), indent=2))
