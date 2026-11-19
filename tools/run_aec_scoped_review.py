"""Run a bounded local AEC judge screen and retain every original start and completion."""

import argparse
import json
import os
import re
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW, prepare_review
from run_aec_development import DIRECTORY, freeze_development_labels, pin, wire
from run_aec_task_notes import SCREEN

from aia_mp1.aec_scoped_judge import ScopedJudgment, project
from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json, read_text, save_new
from aia_mp1.calibration import agreement
from aia_mp1.evidence_judge import completion_json
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.judge import JudgeConfig, messages_for
from aia_mp1.model_client import InstructorClient
from aia_mp1.passage_evidence import passage_input
from aia_mp1.tracing import digest, now

SCOPED = "api-development-scoped-001"
CATALOG_HASH = "d7128a802cf604dc41e0aad1978a83473ca895e3392770eec10fc0da11004a96"
# One-based sentence numbers in the prewritten, immutable task notes.
# These are explanations or permitted choices, not additional deliverables.
SCOPE = {
    "gis_scripting-01": [2],
    "gis_scripting-02": [4, 5],
    "gis_scripting-03": [4],
    "gis_scripting-04": [3],
    "gis_scripting-05": [4],
    "gis_scripting-06": [4],
    "aec_automation-03": [3],
    "aec_automation-06": [3],
    "aec_automation-07": [3],
    "aec_automation-08": [3],
    "aec_automation-10": [2, 3],
    "structural_analysis-01": [3],
    "structural_analysis-02": [3],
    "structural_analysis-04": [3],
    "structural_analysis-05": [3],
    "structural_analysis-06": [4],
    "structural_analysis-09": [3],
    "cad_apis-01": [3],
    "cad_apis-03": [2, 3, 4],
    "cad_apis-05": [3],
    "cad_apis-07": [3],
    "cad_apis-10": [3],
    "simulation-01": [4, 5],
    "simulation-06": [3],
    "simulation-09": [3, 4],
    "simulation-10": [3],
}


def requirements(task, catalog):
    entry = catalog[task["id"]]
    if digest(task["brief"]) != entry["brief_sha256"] or task["category"] != entry["category"]:
        raise ValueError("Task differs from the frozen source brief")
    rows = re.split(r"(?<=[.!?])\s+(?=[A-Z])", entry["notes"])
    optional = set(SCOPE.get(task["id"], []))
    if not optional <= set(range(1, len(rows) + 1)):
        raise ValueError("Scope annotation falls outside the task notes")
    required = [text for i, text in enumerate(rows, 1) if i not in optional]
    return [{"id": f"T{i}", "text": text} for i, text in enumerate(required, 1)], [
        text for i, text in enumerate(rows, 1) if i in optional
    ]


def score_case(directory, key, packet, config):
    target = directory / "judgments" / key
    target.mkdir(parents=True, exist_ok=True)
    start, returned = target / "start.json", target / "return.json"
    identity = {
        "protocol": file_hash(directory / "protocol.json"),
        "request_sha256": digest(packet),
        "item_id": key,
    }
    if not start.exists():
        if returned.exists():
            raise ValueError("Return without a start")
        key_value = os.environ.get(config.api_key_env) or "local-only-placeholder"
        server = LocalServer(config.base_url, key_value)
        try:
            if server.json("/health").get("status") != "ok" or [
                m["id"] for m in server.json("/v1/models")["data"]
            ] != [config.model]:
                raise ValueError("Unexpected endpoint or model")
        finally:
            server.close()
        with InstructorClient(
            base_url=config.base_url,
            api_key=key_value,
            model=config.model,
            mode=config.mode,
            temperature=config.temperature,
            timeout_seconds=config.timeout_seconds,
            reasoning_effort=config.reasoning_effort,
            max_tokens=config.max_tokens,
            response_model=ScopedJudgment,
        ) as client:
            save_new(start, {"identity": identity, "started_at": now()})
            result = client.generate(packet["messages"])
            body = {
                "start_sha256": file_hash(start),
                "completed_at": now(),
                "model": result.response_model,
                "raw": result.raw_response,
                "parsed": result.item.model_dump() if result.item else None,
                "error": result.error,
                "error_type": result.error_type,
            }
            save_new(returned, body | {"sha256": digest(body)})
    if read_json(start)["identity"] != identity or not returned.exists():
        raise ValueError("Changed start or unknown outcome consumes this slot")
    body = read_json(returned)
    if (
        body["sha256"] != digest({k: v for k, v in body.items() if k != "sha256"})
        or body["start_sha256"] != file_hash(start)
        or body["model"] != config.model
        or body["error_type"]
        or body["parsed"] is None
    ):
        raise ValueError("Recorded return is invalid")
    parsed = ScopedJudgment.model_validate(completion_json(body["raw"]))
    if parsed.model_dump() != body["parsed"] or body["raw"]["model"] != config.model:
        raise ValueError("Parsed judgment differs from original model output")
    return parsed


def run(root, score):
    selection = prepare_review(root)
    prior = root / DIRECTORY
    base_protocol = read_json(prior / "protocol.json")
    if selection != base_protocol["review"]:
        raise ValueError("Different development sample")
    catalog = read_json(root / SCREEN / "task-catalog.json")
    if (
        catalog["sha256"] != CATALOG_HASH
        or digest({k: v for k, v in catalog.items() if k != "sha256"}) != CATALOG_HASH
    ):
        raise ValueError("Task catalog changed")
    parent, assessment, records, rubric = load_assessment(root, REVIEW)
    cases = {r["item_id"]: r for r in records}
    ids = selection["selected_ids"]
    prompt = read_text(Path("prompts/aec-development-scoped.md"))
    cfg = JudgeConfig.model_validate(read_json(root / "judge-preparation-v1/judge.json"))
    if (
        cfg.public_settings() != base_protocol["judge"]
        or cfg.base_url != "http://127.0.0.1:18082/v1"
    ):
        raise ValueError("Different judge")
    directory = root / SCOPED
    directory.mkdir(exist_ok=True)
    with exclusive(directory):
        pin(
            directory / "protocol.json",
            {
                "purpose": "Development only",
                "prior_control_sha256": file_hash(prior / "control-report.json"),
                "review": selection,
                "catalog": CATALOG_HASH,
                "scope_annotations": SCOPE,
                "judge": cfg.public_settings(),
                "prompt": prompt,
                "schema": ScopedJudgment.model_json_schema(),
                "max_starts": 10,
                "attempts_per_case": 1,
                "advance_rule": base_protocol["advance_rule"],
                "code": {
                    str(p): file_hash(p)
                    for p in [
                        Path(__file__),
                        Path("src/aia_mp1/aec_scoped_judge.py"),
                        Path("src/aia_mp1/aec_development.py"),
                        Path("src/aia_mp1/model_client.py"),
                        Path("src/aia_mp1/passage_evidence.py"),
                        Path("tools/run_aec_development.py"),
                    ]
                },
            },
        )
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(directory / "review-checkpoint.json") != file_hash(
            prior / "review-checkpoint.json"
        ):
            raise ValueError("Development human reference differs")
        packets = {}
        for key in ids:
            messages = messages_for(prompt, rubric, cases[key])
            content = passage_input(json.loads(messages[1]["content"]), rubric)
            req, scope = requirements(cases[key]["reference_context"]["task"], catalog["tasks"])
            packets[key] = {
                "messages": wire(
                    messages[0]["content"], content | {"required_checks": req, "scope_notes": scope}
                ),
                "content": content,
                "required": req,
            }
        pin(directory / "requests.json", packets)
        if not score:
            return {"cases": len(ids), "requests_sha256": file_hash(directory / "requests.json")}
        results = {}
        for key, packet in packets.items():
            raw = score_case(directory, key, packet, cfg)
            results[key] = project(raw, packet["content"], rubric, packet["required"]).model_dump()
        summary = agreement([cases[k] for k in ids], ids, labels, results)
        report = pin(
            directory / "report.json",
            {
                "summary": summary,
                "human_reference": file_hash(directory / "review-checkpoint.json"),
                "development_only": True,
                "requests_sha256": file_hash(directory / "requests.json"),
                "returns": {k: file_hash(directory / "judgments" / k / "return.json") for k in ids},
            },
        )
        return {
            "sha256": digest(report),
            "matches": {d: v["matching"] for d, v in summary["dimensions"].items()},
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "score"))
    print(json.dumps(run(ROOT.resolve(), parser.parse_args().stage == "score"), indent=2))
