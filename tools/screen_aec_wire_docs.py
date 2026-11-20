"""Frozen reversible page tables and lossless measured Instructor-wire compaction."""

import argparse
import json
import os
from pathlib import Path

from aec_grounded_docs import PAGES, ROOTS, Lookup
from aec_wire_docs import (
    LEGEND,
    OneShotWireTransport,
    compact_rubric_messages,
    compact_schema_wire,
    encode_pages,
)
from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from run_aec_development import DIRECTORY as CONTROL
from run_aec_development import STAGES, capture, freeze_development_labels, pin, wire
from screen_aec_compact_docs import PROJECTION, project_pages, retained_lookup
from screen_aec_compact_docs import build_judgment_messages as compact_messages
from screen_aec_grounded_docs import (
    FINAL,
    SELECT,
    fit_request,
    paired,
    previous_scores,
    read_pages,
    schema_wire,
    snapshot,
    verify_deployment,
)
from screen_aec_local_model import SCREEN_MODEL

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json, save_new
from aia_mp1.calibration import agreement
from aia_mp1.canonical_development import QWEN_MODEL_SHA, QWEN_SETTINGS
from aia_mp1.evidence_judge import completion_json
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.grounded_documentation import GroundedJudgment, candidate_catalog, validate_grounding
from aia_mp1.judge import JudgeConfig
from aia_mp1.model_client import InstructorClient
from aia_mp1.tracing import digest, now, run_directory

DIRECTORY = "api-development-qwen-wire-docs-001"
PREDECESSOR = "api-development-qwen-compact-docs-001"
WIRE_POLICY = {
    "page_encoding": "reversible_page_tables_v1",
    "schema": ["json_whitespace", "identical_property_schema_refs", "short_local_definition_names"],
    "schema_annotations": "all_preserved",
    "rubric": "json_whitespace_only",
    "json_separators": [",", ":"],
    "page_legend": LEGEND,
}


def build_judgment_messages(original, pages):
    messages = compact_messages(original, pages)
    body = json.loads(messages[1]["content"])
    body["online_documentation"] = encode_pages(body["online_documentation"])
    messages[1]["content"] = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    messages[0]["content"] += "\n\n" + LEGEND
    marker = "\n\nRubric:\n"
    if original[0]["content"].count(marker) != 1:
        raise ValueError("Expected one frozen original rubric")
    rubric, _ = json.JSONDecoder().raw_decode(original[0]["content"].split(marker, 1)[1])
    return compact_rubric_messages(messages, rubric)


def judgment_wires(messages, cfg):
    original = schema_wire(messages, cfg, GroundedJudgment)
    actual = compact_schema_wire(
        original, messages, GroundedJudgment.model_json_schema(), factor=True
    )
    return original, actual


def capture_judgment(directory, item_id, messages, config, wires, *, replay_only=False):
    """One durable attempt binds both Instructor input and the measured transmitted wire."""
    expected, actual = wires
    target = directory / "grounded_judgment" / item_id
    start, returned = target / "start.json", target / "return.json"
    identity = {
        "item_id": item_id,
        "stage": "grounded_judgment",
        "protocol_sha256": file_hash(directory / "protocol.json"),
        "messages_sha256": digest({"messages": messages}),
        "model": config.model,
        "instructor_wire_sha256": digest(expected),
        "wire_sha256": digest(actual),
    }
    fit_path = directory / f"{item_id}-grounded_judgment-fit.json"
    fit = read_json(fit_path)
    if (
        fit.get("wire_sha256") != digest(actual)
        or fit.get("fits") is not True
        or type(fit.get("prompt_tokens")) is not int
        or fit["prompt_tokens"] < 0
        or type(fit.get("required_tokens")) is not int
        or any(
            type(fit.get(k)) is not int or fit[k] != value
            for k, value in {
                "output_tokens": config.max_tokens,
                "reserve_tokens": 1200,
                "context_size": 16384,
            }.items()
        )
        or fit["required_tokens"] != fit["prompt_tokens"] + config.max_tokens + 1200
        or fit["required_tokens"] > 16384
    ):
        raise ValueError("Judgment wire differs from successful measured fit")
    identity["fit_sha256"] = file_hash(fit_path)
    if not start.exists():
        if replay_only:
            raise ValueError("Expected a retained wire judgment for offline replay")
        if returned.exists():
            raise ValueError("Return without a durable start")
        target.mkdir(parents=True, exist_ok=True)
        key = os.environ.get(config.api_key_env) or "local-only-placeholder"
        server = LocalServer(config.base_url, key)
        try:
            if server.json("/health").get("status") != "ok" or [
                m["id"] for m in server.json("/v1/models")["data"]
            ] != [config.model]:
                raise ValueError("Endpoint health or served weights differ")
        finally:
            server.close()
        transport = OneShotWireTransport(expected, actual)
        with InstructorClient(
            base_url=config.base_url,
            model=config.model,
            api_key=key,
            mode=config.mode,
            temperature=config.temperature,
            timeout_seconds=config.timeout_seconds,
            max_tokens=config.max_tokens,
            reasoning_effort=config.reasoning_effort,
            response_model=GroundedJudgment,
            _transport=transport,
        ) as client:
            save_new(
                start,
                {
                    "identity": identity,
                    "started_at": now(),
                    "messages": messages,
                    "instructor_wire": expected,
                    "wire": actual,
                },
            )
            result = client.generate(messages)
            body = {
                "start_sha256": file_hash(start),
                "completed_at": now(),
                "raw": result.raw_response,
                "model": result.response_model,
                "error_type": result.error_type,
                "error": result.error,
                "parsed": result.item.model_dump() if result.item else None,
                "transport_calls": transport.calls,
            }
            save_new(returned, body | {"sha256": digest(body)})
    recorded = read_json(start)
    if (
        recorded["identity"] != identity
        or recorded["messages"] != messages
        or recorded["instructor_wire"] != expected
        or recorded["wire"] != actual
    ):
        raise ValueError("Started judgment with different inputs or wire")
    if not returned.exists():
        raise ValueError("Unknown outcome consumes this case/stage allocation")
    body = read_json(returned)
    if (
        body["sha256"] != digest({k: v for k, v in body.items() if k != "sha256"})
        or body["start_sha256"] != file_hash(start)
        or body["model"] != config.model
        or body["parsed"] is None
        or body["error_type"]
        or body["error"]
        or body["transport_calls"] != 1
    ):
        raise ValueError("Recorded wire judgment failed integrity, model or response checks")
    parsed = GroundedJudgment.model_validate(completion_json(body["raw"]))
    if parsed.model_dump() != body["parsed"] or body["raw"]["model"] != config.model:
        raise ValueError("Raw response differs from parsed return")
    return parsed


def readonly_preflight(
    directory, prior, ancestor, baseline, protocol, originals, cfg, requests, receipt_path
):
    """Tokenize lookup inputs and one retained-page diagnostic; never dispatch or write."""
    if (
        read_json(directory / "protocol.json") != protocol
        or file_hash(directory / "lookup-requests.json") != protocol["lookup_inputs"]
        or file_hash(directory / "review-checkpoint.json") != protocol["reference"]
    ):
        raise ValueError("Prepared wire inputs differ")
    if receipt_path is None:
        raise ValueError("Read-only preflight requires a fresh runtime receipt path")
    deployment = read_json(Path(receipt_path))
    verify_deployment(deployment, directory, cfg, live=True)
    key = protocol["cases"][0]
    lookup = retained_lookup(ancestor, key, requests[key], cfg)
    category = json.loads(originals[key][1]["content"])["untrusted_reference_context"]["task"][
        "category"
    ]
    pages = read_pages(ancestor, key, category, lookup, replay=True)
    diagnostic = build_judgment_messages(originals[key], pages)
    lookup_wires = {key: schema_wire(messages, cfg, Lookup) for key, messages in requests.items()}
    instructor_wire, judgment_wire = judgment_wires(diagnostic, cfg)
    before = snapshot(directory)
    server = LocalServer(cfg.base_url, "local-only-placeholder")
    try:
        props = server.json("/props")
        if (
            props["model_path"] != cfg.model
            or props["build_info"] != deployment["build"]
            or props["total_slots"] != 1
            or props["default_generation_settings"]["n_ctx"] != 16384
        ):
            raise ValueError("Local tokenizer service differs")
        fits = {key: server.token_fit(value, 16384, 1200) for key, value in lookup_wires.items()}
        diagnostic_fit = server.token_fit(judgment_wire, 16384, 1200)
        if server.json("/props") != props:
            raise ValueError("Tokenizer service changed during preflight")
        verify_deployment(deployment, directory, cfg, live=True)
    finally:
        server.close()
    if (
        snapshot(directory) != before
        or snapshot(prior) != protocol["predecessor"]["files_sha256"]
        or snapshot(ancestor) != protocol["grounded_ancestor"]["files_sha256"]
        or snapshot(baseline) != protocol["completed_baseline"]["files_sha256"]
    ):
        raise ValueError("Run evidence changed during read-only preflight")
    return {
        "inference_requests": 0,
        "protocol_sha256": file_hash(directory / "protocol.json"),
        "runtime_receipt_sha256": file_hash(Path(receipt_path)),
        "lookup_fits": fits,
        "diagnostic_judgment": {
            "item_id": key,
            "retained_pages_sha256": file_hash(ancestor / f"{key}-pages.json"),
            "fit": diagnostic_fit,
            "instructor_wire_sha256": digest(instructor_wire),
        },
        "measured_requests_fit": all(value["fits"] for value in fits.values())
        and diagnostic_fit["fits"],
        "scope": "Ten lookup requests and only the first retained-grounded-ancestor-page judgment diagnostic. No new lookup or judgment attempts; other judgment inputs remain unmeasured.",
    }


def run(root, stage, *, run_id=DIRECTORY, predecessor=PREDECESSOR, preflight_receipt=None):
    if stage not in {"prepare", "score", "replay", "preflight"}:
        raise ValueError("Unknown documentation comparison stage")
    directory = run_directory(root, run_id)
    prior = run_directory(root, predecessor) if predecessor is not None else None
    if prior == directory:
        raise ValueError("Output and predecessor must be different runs")
    if prior is None:
        raise ValueError("A follow-up run requires its predecessor")
    lineage = {"run_id": predecessor, "files_sha256": snapshot(prior)} if prior else None
    if directory.exists():
        files = snapshot(directory)
        if files and "protocol.json" not in files:
            raise ValueError("Populated output has no frozen protocol; preserve and inspect it")
        if (
            "protocol.json" in files
            and read_json(directory / "protocol.json").get("predecessor") != lineage
        ):
            raise ValueError("Frozen predecessor linkage differs")
    parent, assessment, records, _ = load_assessment(root, REVIEW)
    ids = assessment["selected_ids"]
    if len(ids) != 10 or len(set(ids)) != 10:
        raise ValueError("Exactly ten distinct development cases are required")
    cfg = JudgeConfig.model_validate(read_json(root / "judge-preparation-v1/judge.json"))
    if (
        cfg.model_sha256 != QWEN_MODEL_SHA
        or cfg.base_url != "http://127.0.0.1:18082/v1"
        or any(getattr(cfg, k) != v for k, v in QWEN_SETTINGS.items())
    ):
        raise ValueError("Unexpected local judge")
    originals = read_json(root / SCREEN_MODEL / "requests.json")
    STAGES.update(grounded_lookup=Lookup, grounded_judgment=GroundedJudgment)
    control = root / CONTROL
    for k in ids:
        target = control / "control" / k
        for path in (
            control,
            control / "control",
            target,
            target / "start.json",
            target / "return.json",
        ):
            if path.is_symlink() or not path.exists():
                raise ValueError("Missing or symlink matched control evidence")
    before = {
        k: capture(control, k, "control", originals[k], cfg, replay_only=True).model_dump()
        for k in ids
    }
    cats = {}
    requests = {}
    for k in ids:
        case = json.loads(originals[k][1]["content"])
        cat = case["untrusted_reference_context"]["task"]["category"]
        cats[k] = cat
        requests[k] = wire(
            SELECT, {"permitted_urls": ROOTS[cat], "pages": PAGES[cat], "case": case}
        )
    protocol = {
        "development_only": True,
        "cases": ids,
        "judge": cfg.public_settings(),
        "control_report": file_hash(control / "control-report.json"),
        "reference": file_hash(control / "review-checkpoint.json"),
        "lookup_inputs": digest(
            json.dumps(requests, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        ),
        "selectors": SELECT,
        "final_instruction": FINAL,
        "original_requests": file_hash(root / SCREEN_MODEL / "requests.json"),
        "page_menu": json.loads(json.dumps(PAGES)),
        "permitted_urls": json.loads(json.dumps(ROOTS)),
        "source": {
            p: file_hash(Path(p))
            for p in (
                "tools/aec_grounded_docs.py",
                "src/aia_mp1/grounded_documentation.py",
                "src/aia_mp1/evidence_judge.py",
                "src/aia_mp1/analysis.py",
                "src/aia_mp1/schemas.py",
                "tools/prepare_aec_api_evaluation.py",
                "tools/prepare_aec_development_review.py",
                "tools/screen_aec_local_model.py",
                "src/aia_mp1/factcheck_transport.py",
                "src/aia_mp1/evaluation_schemas.py",
                "src/aia_mp1/assessment.py",
                "src/aia_mp1/calibration.py",
                "src/aia_mp1/tracing.py",
                "src/aia_mp1/judge.py",
                "src/aia_mp1/canonical_development.py",
                "tools/screen_aec_grounded_docs.py",
                "tools/screen_aec_compact_docs.py",
                "tools/aec_wire_docs.py",
                "tools/screen_aec_wire_docs.py",
                "tools/run_aec_development.py",
                "src/aia_mp1/model_client.py",
            )
        },
        "stages": {
            "grounded_lookup": Lookup.model_json_schema(),
            "grounded_judgment": GroundedJudgment.model_json_schema(),
        },
        "max_model_starts": 20,
        "max_page_requests": 30,
        "promotion": "Ten complete judgments with usable online evidence, at least eight matches on each dimension, and sound explanations.",
    }
    protocol.update(display_projection=PROJECTION, judgment_json_separators=[",", ":"])
    if prior:
        old = read_json(prior / "protocol.json")
        if (
            {
                key: value
                for key, value in old.items()
                if key not in {"source", "run_id", "predecessor", "completed_baseline"}
            }
            != {key: value for key, value in protocol.items() if key != "source"}
            or old["source"] != {key: protocol["source"][key] for key in old["source"]}
            or file_hash(prior / "review-checkpoint.json") != old["reference"]
            or file_hash(prior / "lookup-requests.json") != old["lookup_inputs"]
            or read_json(prior / "lookup-requests.json") != requests
        ):
            raise ValueError("Compact predecessor inputs or frozen sources differ")
        ancestor = run_directory(root, old["predecessor"]["run_id"])
        if snapshot(ancestor) != old["predecessor"]["files_sha256"]:
            raise ValueError("Grounded ancestor differs from compact predecessor lineage")
        if read_json(ancestor / "protocol.json")["predecessor"] != old["completed_baseline"]:
            raise ValueError("Completed baseline linkage differs across ancestors")
        baseline = run_directory(root, old["completed_baseline"]["run_id"])
        if snapshot(baseline) != old["completed_baseline"]["files_sha256"]:
            raise ValueError("Completed comparison baseline differs from predecessor lineage")
        previous = previous_scores(baseline, ids, cfg)
        protocol.update(
            display_projection=PROJECTION,
            judgment_json_separators=[",", ":"],
            completed_baseline=old["completed_baseline"],
            grounded_ancestor=old["predecessor"],
            wire_policy=WIRE_POLICY,
        )
        protocol.update(run_id=run_id, predecessor=lineage)
        if snapshot(prior) != lineage["files_sha256"]:
            raise ValueError("Predecessor changed during preparation")
    for key in ids:
        candidate_catalog(json.loads(originals[key][1]["content"]))
    if stage == "preflight":
        return readonly_preflight(
            directory,
            prior,
            ancestor,
            baseline,
            protocol,
            originals,
            cfg,
            requests,
            preflight_receipt,
        )
    directory.mkdir(exist_ok=True)
    with exclusive(directory):
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(directory / "review-checkpoint.json") != protocol["reference"]:
            raise ValueError("Human reference differs from matched control")
        pin(directory / "lookup-requests.json", requests)
        if file_hash(directory / "lookup-requests.json") != protocol["lookup_inputs"]:
            raise ValueError("Lookup input serialization differs")
        pin(directory / "protocol.json", protocol)
        if stage == "prepare":
            return {"prepared": len(ids)}
        replay = stage == "replay"
        deployment = read_json(directory / "deployment.json")
        verify_deployment(deployment, directory, cfg, live=not replay)
        scores, evidence = {}, {}
        active_key, active_stage = None, None
        server = None if replay else LocalServer(cfg.base_url, "local-only-placeholder")
        try:
            if server:
                props = server.json("/props")
                if (
                    props["model_path"] != cfg.model
                    or props["build_info"] != deployment["build"]
                    or props["total_slots"] != 1
                    or props["default_generation_settings"]["n_ctx"] != 16384
                ):
                    raise ValueError("Local service differs")
            for k in ids:
                active_key, active_stage = k, "grounded_lookup"
                if server and not (directory / active_stage / k / "start.json").exists():
                    fit_request(directory, k, active_stage, requests[k], cfg, server)
                    verify_deployment(deployment, directory, cfg, live=True)
                lookup = capture(directory, k, active_stage, requests[k], cfg, replay_only=replay)
                pages = read_pages(directory, k, cats[k], lookup, replay)
                shown = project_pages(pages)
                messages = build_judgment_messages(originals[k], pages)
                active_stage = "grounded_judgment"
                wires = judgment_wires(messages, cfg)
                if server and not (directory / active_stage / k / "start.json").exists():
                    fit = server.token_fit(wires[1], 16384, 1200)
                    pin(directory / f"{k}-{active_stage}-fit.json", fit)
                    if not fit["fits"]:
                        raise ValueError(
                            "Schema-bearing wire documentation request exceeds context"
                        )
                    verify_deployment(deployment, directory, cfg, live=True)
                result = capture_judgment(directory, k, messages, cfg, wires, replay_only=replay)
                scores[k] = validate_grounding(
                    result, json.loads(originals[k][1]["content"]), shown
                ).model_dump()
                evidence[k] = {
                    "pages": file_hash(directory / f"{k}-pages.json"),
                    "lookup": file_hash(directory / "grounded_lookup" / k / "return.json"),
                    "judgment": file_hash(directory / "grounded_judgment" / k / "return.json"),
                    "opened": sum("http_status" in p and p["http_status"] == 200 for p in pages),
                    "requested": len(pages),
                }
        except (ValueError, KeyError, OSError) as error:
            if active_key is not None:
                target = directory / active_stage / active_key
                receipt = {
                    "complete": False,
                    "selected_denominator": len(ids),
                    "validated_judgments": len(scores),
                    "item_id": active_key,
                    "stage": active_stage,
                    "error": str(error),
                    "start_sha256": file_hash(target / "start.json")
                    if (target / "start.json").exists()
                    else None,
                    "return_sha256": file_hash(target / "return.json")
                    if (target / "return.json").exists()
                    else None,
                }
                incomplete = directory / f"{active_key}-{active_stage}-incomplete.json"
                if not incomplete.exists():
                    save_new(incomplete, receipt)
            raise
        finally:
            if server:
                server.close()
        summary = agreement([r for r in records if r["item_id"] in ids], ids, labels, scores)
        pin(
            directory / "report.json",
            {
                "summary": summary,
                "evidence": evidence,
                "paired_control": paired(scores, before, labels),
                "paired_previous": paired(scores, previous, labels),
                "selected_denominator": len(ids),
                "validated_judgments": len(scores),
                "protocol_sha256": file_hash(directory / "protocol.json"),
                "deployment_sha256": file_hash(directory / "deployment.json"),
            },
        )
        return {
            "matches": {d: v["matching"] for d, v in summary["dimensions"].items()},
            "opened": sum(v["opened"] for v in evidence.values()),
            "report": file_hash(directory / "report.json"),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "score", "replay", "preflight"))
    parser.add_argument("--run-id", default=DIRECTORY)
    parser.add_argument("--predecessor", default=PREDECESSOR)
    parser.add_argument("--preflight-receipt", type=Path)
    args = parser.parse_args()
    try:
        result = run(
            ROOT.resolve(),
            args.stage,
            run_id=args.run_id,
            predecessor=args.predecessor,
            preflight_receipt=args.preflight_receipt,
        )
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f"Incomplete wire comparison: {error}\n")
    print(json.dumps(result, indent=2))
