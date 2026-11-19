"""Run the ten-case, local-only AEC development comparison one stage at a time."""

import argparse
import json
import os
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW, prepare_review

from aia_mp1.aec_development import (
    DevelopmentJudgment,
    TaskChecklist,
    checked_judgment,
    checked_reference,
    reference_catalog,
)
from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json, read_text, save_new
from aia_mp1.calibration import agreement
from aia_mp1.evaluation_schemas import Judgment
from aia_mp1.evidence_judge import completion_json
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.judge import JudgeConfig, messages_for
from aia_mp1.labels import load_labels
from aia_mp1.model_client import InstructorClient
from aia_mp1.passage_evidence import passage_input
from aia_mp1.qualification import validate_qualification
from aia_mp1.tracing import digest, now

DIRECTORY = "api-development-comparison-001"
STAGES = {"reference": TaskChecklist, "control": Judgment, "comparison": DevelopmentJudgment}
PROMPTS = {
    "reference": Path("prompts/aec-development-reference.md"),
    "control": Path("prompts/aec-api-correctness-judge-v3.md"),
    "comparison": Path("prompts/aec-development-comparison.md"),
}


def pin(path, value):
    if not path.exists():
        save_new(path, value)
    if read_json(path) != value:
        raise ValueError(f"Frozen {path.name} differs")
    return value


def wire(system, user):
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def prepare(root):
    selection = prepare_review(root)
    parent, assessment, records, rubric = load_assessment(root, REVIEW)
    by_id = {r["item_id"]: r for r in records}
    cases = [by_id[i] for i in selection["selected_ids"]]
    prompts = {s: read_text(path) for s, path in PROMPTS.items()}
    cfg = JudgeConfig.model_validate(read_json(root / "judge-preparation-v1/judge.json"))
    # The original assessed selection identifies this model and generator.
    _, original, _, _ = load_assessment(root, "aec-course-baseline-review")
    qualification = validate_qualification(cfg, original)
    if (
        cfg.base_url != "http://127.0.0.1:18082/v1"
        or cfg.temperature >= original["generator_temperature"]
    ):
        raise ValueError("Unexpected judge endpoint or temperature")
    directory = root / DIRECTORY
    directory.mkdir(exist_ok=True)
    if directory.is_symlink():
        raise ValueError("Symlink development output")
    with exclusive(directory):
        pin(
            directory / "protocol.json",
            {
                "review": selection,
                "purpose": "Development only",
                "max_starts": 30,
                "stages": list(STAGES),
                "attempts_per_case_per_stage": 1,
                "qualification_sha256": qualification["sha256"],
                "judge": cfg.public_settings(),
                "prompts": prompts,
                "schemas": {k: v.model_json_schema() for k, v in STAGES.items()},
                "code": {
                    str(p): file_hash(p)
                    for p in (
                        Path("src/aia_mp1/aec_development.py"),
                        Path("src/aia_mp1/passage_evidence.py"),
                        Path("src/aia_mp1/evidence_judge.py"),
                        Path("src/aia_mp1/model_client.py"),
                        Path("tools/prepare_aec_development_review.py"),
                        Path("tools/run_aec_development.py"),
                    )
                },
                "minimum_matches_per_dimension": 8,
                "advance_rule": "Complete ten cases per arm, 8/10 in every dimension for the comparison, no worse D1/D6 agreement than control and an accepted independent explanation audit.",
            },
        )
        pin(
            directory / "reference-inputs.json",
            {
                r["item_id"]: wire(prompts["reference"], reference_catalog(r["reference_context"]))
                for r in cases
            },
        )
    return directory, parent, assessment, cases, records, rubric, cfg, prompts


def capture(directory, item_id, stage, messages, config, *, replay_only=False):
    target = directory / stage / item_id
    target.mkdir(parents=True, exist_ok=True)
    start, returned = target / "start.json", target / "return.json"
    identity = {
        "item_id": item_id,
        "stage": stage,
        "protocol_sha256": file_hash(directory / "protocol.json"),
        "messages_sha256": digest({"messages": messages}),
        "model": config.model,
    }
    if not start.exists():
        if replay_only:
            raise ValueError("Expected a retained request for offline replay")
        if returned.exists():
            raise ValueError("Return without a durable start")
        key = os.environ.get(config.api_key_env) or "local-only-placeholder"
        server = LocalServer(config.base_url, key)
        try:
            if server.json("/health").get("status") != "ok" or [
                m["id"] for m in server.json("/v1/models")["data"]
            ] != [config.model]:
                raise ValueError("Endpoint health or served weights differ")
        finally:
            server.close()
        with InstructorClient(
            base_url=config.base_url,
            model=config.model,
            api_key=key,
            mode=config.mode,
            temperature=config.temperature,
            timeout_seconds=config.timeout_seconds,
            max_tokens=config.max_tokens,
            reasoning_effort=config.reasoning_effort,
            response_model=STAGES[stage],
        ) as client:
            save_new(start, {"identity": identity, "started_at": now(), "messages": messages})
            result = client.generate(messages)
            body = {
                "start_sha256": file_hash(start),
                "completed_at": now(),
                "raw": result.raw_response,
                "model": result.response_model,
                "error_type": result.error_type,
                "error": result.error,
                "parsed": result.item.model_dump() if result.item else None,
            }
            save_new(returned, body | {"sha256": digest(body)})
    if read_json(start)["identity"] != identity or read_json(start)["messages"] != messages:
        raise ValueError("Started with different inputs")
    if not returned.exists():
        raise ValueError("Unknown outcome consumes this case/stage allocation")
    body = read_json(returned)
    if (
        body["sha256"] != digest({k: v for k, v in body.items() if k != "sha256"})
        or body["start_sha256"] != file_hash(start)
        or body["model"] != config.model
        or body["parsed"] is None
        or body["error_type"]
    ):
        raise ValueError("Recorded return failed integrity, model or response checks")
    parsed = STAGES[stage].model_validate(completion_json(body["raw"]))
    if parsed.model_dump() != body["parsed"] or body["raw"]["model"] != config.model:
        raise ValueError("Raw response differs from parsed return")
    return parsed


def freeze_development_labels(directory, parent, assessment, records):
    with exclusive(parent):
        labels = load_labels(parent, assessment, records)
        if set(labels) != set(assessment["selected_ids"]) or any(
            r.get("review_stage") != "blind"
            or r.get("consulted_report_ids")
            or r["supersedes_label_id"]
            or r["reviewer"] != "Chad Josewski"
            for r in labels.values()
        ):
            raise ValueError("Ten independently completed development reviews are needed")
        if len(read_text(parent / "human-labels.jsonl").splitlines()) != 10:
            raise ValueError("Review history needs inspection")
        pin(
            directory / "review-checkpoint.json",
            {
                "assessment": assessment["manifest_sha256"],
                "ledger": file_hash(parent / "human-labels.jsonl"),
                "labels": {k: v["label_id"] for k, v in labels.items()},
            },
        )
        return labels


def main(stage):
    directory, parent, assessment, cases, records, rubric, cfg, prompts = prepare(ROOT.resolve())
    if stage == "prepare":
        return {"protocol_sha256": file_hash(directory / "protocol.json"), "cases": len(cases)}
    with exclusive(directory):
        if stage in {"reference", "comparison"}:
            inputs = read_json(directory / "reference-inputs.json")
            resolved = {}
            for r in cases:
                key = r["item_id"]
                plan = capture(
                    directory, key, "reference", inputs[key], cfg, replay_only=stage != "reference"
                )
                resolved[key] = checked_reference(plan, reference_catalog(r["reference_context"]))
            pin(directory / "checklists.json", resolved)
            if stage == "reference":
                return {
                    "checklists": len(resolved),
                    "sha256": file_hash(directory / "checklists.json"),
                }
        labels = freeze_development_labels(directory, parent, assessment, records)
        if stage == "comparison":
            checks = read_json(directory / "checklists.json")
            audit = read_json(directory / "reference-audit.json")
            if (
                audit.get("checklists_sha256") != file_hash(directory / "checklists.json")
                or not audit.get("auditor")
                or set(audit.get("cases", {})) != set(assessment["selected_ids"])
                or any(
                    row.get("accepted") is not True or not row.get("basis")
                    for row in audit["cases"].values()
                )
            ):
                raise ValueError(
                    "An attributed technical audit must accept each independent task checklist"
                )
        judgments = {}
        for r in cases:
            key = r["item_id"]
            messages = messages_for(prompts[stage], rubric, r)
            if stage == "comparison":
                content = passage_input(json.loads(messages[1]["content"]), rubric)
                messages = wire(messages[0]["content"], content | {"task_checklist": checks[key]})
                result = capture(directory, key, stage, messages, cfg)
                judgment = checked_judgment(result, content, rubric, checks[key])
            else:
                judgment = capture(directory, key, stage, messages, cfg)
            judgments[key] = judgment.model_dump()
        summary = agreement(cases, assessment["selected_ids"], labels, judgments)
        pin(
            directory / f"{stage}-report.json",
            {
                "development_only": True,
                "review_sha256": file_hash(directory / "review-checkpoint.json"),
                "returns": {k: file_hash(directory / stage / k / "return.json") for k in judgments},
                "summary": summary,
            },
        )
        return {
            "stage": stage,
            "matches": {d: v["matching"] for d, v in summary["dimensions"].items()},
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", *STAGES))
    print(json.dumps(main(parser.parse_args().stage), indent=2))
