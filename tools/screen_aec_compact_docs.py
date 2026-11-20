"""Separate frozen follow-up with a compact, evidence-preserving page display."""

import argparse
import json
from pathlib import Path

from aec_grounded_docs import PAGES, ROOTS, Lookup
from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from run_aec_development import DIRECTORY as CONTROL
from run_aec_development import STAGES, capture, freeze_development_labels, pin, wire
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
from aia_mp1.tracing import digest, run_directory

DIRECTORY = "api-development-qwen-compact-docs-001"
PREDECESSOR = "api-development-qwen-grounded-docs-001"
PROJECTION = {
    "remove_page": ["normalized_text_sha256", "normalized_text_chars"],
    "remove_search": ["match_start", "match_end"],
    "remove_excerpt": ["start", "end", "anchors"],
}


def project_pages(pages):
    """Remove diagnostic metadata from display only; never mutate retained evidence."""
    shown = []
    for index, page in enumerate(pages, 1):
        value = {
            "id": f"P{index}",
            **{
                key: item
                for key, item in page.items()
                if key not in {"opened_at", "body_sha256", "start", *PROJECTION["remove_page"]}
            },
        }
        value["search_results"] = [
            {key: item for key, item in search.items() if key not in PROJECTION["remove_search"]}
            for search in page["search_results"]
        ]
        value["excerpts"] = [
            {key: item for key, item in excerpt.items() if key not in PROJECTION["remove_excerpt"]}
            for excerpt in page["excerpts"]
        ]
        shown.append(value)
    return shown


def build_judgment_messages(original, pages, *, compact_json=True):
    return [
        original[0] | {"content": original[0]["content"] + "\n\n" + FINAL},
        original[1]
        | {
            "content": json.dumps(
                json.loads(original[1]["content"])
                | {
                    "online_documentation": project_pages(pages),
                    "candidate_field_ids": list(
                        candidate_catalog(json.loads(original[1]["content"]))
                    ),
                },
                ensure_ascii=False,
                separators=(",", ":") if compact_json else None,
            )
        },
    ]


def retained_lookup(prior, key, messages, cfg):
    """Read the diagnostic lookup directly, without a capture directory or attempt allocation."""
    target = prior / "grounded_lookup" / key
    start = read_json(target / "start.json")
    body = read_json(target / "return.json")
    identity = {
        "item_id": key,
        "stage": "grounded_lookup",
        "protocol_sha256": file_hash(prior / "protocol.json"),
        "messages_sha256": digest({"messages": messages}),
        "model": cfg.model,
    }
    if (
        start["identity"] != identity
        or start["messages"] != messages
        or body["sha256"] != digest({k: v for k, v in body.items() if k != "sha256"})
        or body["start_sha256"] != file_hash(target / "start.json")
        or body["model"] != cfg.model
        or body["error_type"]
        or body["error"]
        or body["raw"]["model"] != cfg.model
    ):
        raise ValueError("Invalid diagnostic lookup history")
    lookup = Lookup.model_validate(completion_json(body["raw"]))
    if lookup.model_dump() != body["parsed"]:
        raise ValueError("Diagnostic lookup raw and parsed values differ")
    return lookup


def readonly_preflight(directory, prior, protocol, originals, cfg, requests, receipt_path):
    """Tokenize lookup inputs and one retained-page diagnostic; never dispatch or write."""
    if (
        read_json(directory / "protocol.json") != protocol
        or file_hash(directory / "lookup-requests.json") != protocol["lookup_inputs"]
        or file_hash(directory / "review-checkpoint.json") != protocol["reference"]
    ):
        raise ValueError("Prepared compact inputs differ")
    if receipt_path is None:
        raise ValueError("Read-only preflight requires a fresh runtime receipt path")
    deployment = read_json(Path(receipt_path))
    verify_deployment(deployment, directory, cfg, live=True)
    key = protocol["cases"][0]
    lookup = retained_lookup(prior, key, requests[key], cfg)
    category = json.loads(originals[key][1]["content"])["untrusted_reference_context"]["task"][
        "category"
    ]
    pages = read_pages(prior, key, category, lookup, replay=True)
    diagnostic = build_judgment_messages(originals[key], pages)
    lookup_wires = {key: schema_wire(messages, cfg, Lookup) for key, messages in requests.items()}
    judgment_wire = schema_wire(diagnostic, cfg, GroundedJudgment)
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
    if snapshot(directory) != before or snapshot(prior) != protocol["predecessor"]["files_sha256"]:
        raise ValueError("Run evidence changed during read-only preflight")
    return {
        "inference_requests": 0,
        "protocol_sha256": file_hash(directory / "protocol.json"),
        "runtime_receipt_sha256": file_hash(Path(receipt_path)),
        "lookup_fits": fits,
        "diagnostic_judgment": {
            "item_id": key,
            "retained_pages_sha256": file_hash(prior / f"{key}-pages.json"),
            "fit": diagnostic_fit,
        },
        "measured_requests_fit": all(value["fits"] for value in fits.values())
        and diagnostic_fit["fits"],
        "scope": "Ten lookup requests and only the first retained-parent-page judgment diagnostic. No new lookup or judgment attempts; other judgment inputs remain unmeasured.",
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
    if prior:
        old = read_json(prior / "protocol.json")
        if (
            {
                key: value
                for key, value in old.items()
                if key not in {"source", "run_id", "predecessor"}
            }
            != {key: value for key, value in protocol.items() if key != "source"}
            or old["source"] != {key: protocol["source"][key] for key in old["source"]}
            or file_hash(prior / "review-checkpoint.json") != old["reference"]
            or file_hash(prior / "lookup-requests.json") != old["lookup_inputs"]
            or read_json(prior / "lookup-requests.json") != requests
        ):
            raise ValueError("Stopped predecessor inputs or frozen sources differ")
        baseline = run_directory(root, old["predecessor"]["run_id"])
        if snapshot(baseline) != old["predecessor"]["files_sha256"]:
            raise ValueError("Completed comparison baseline differs from predecessor lineage")
        previous = previous_scores(baseline, ids, cfg)
        protocol.update(
            display_projection=PROJECTION,
            judgment_json_separators=[",", ":"],
            completed_baseline=old["predecessor"],
        )
        protocol.update(run_id=run_id, predecessor=lineage)
        if snapshot(prior) != lineage["files_sha256"]:
            raise ValueError("Predecessor changed during preparation")
    for key in ids:
        candidate_catalog(json.loads(originals[key][1]["content"]))
    if stage == "preflight":
        return readonly_preflight(
            directory, prior, protocol, originals, cfg, requests, preflight_receipt
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
                if server and not (directory / active_stage / k / "start.json").exists():
                    fit_request(directory, k, active_stage, messages, cfg, server)
                    verify_deployment(deployment, directory, cfg, live=True)
                result = capture(directory, k, active_stage, messages, cfg, replay_only=replay)
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
        parser.exit(1, f"Incomplete compact comparison: {error}\n")
    print(json.dumps(result, indent=2))
