"""Case-specific native-schema judgment contract after the stopped wire comparison."""

import argparse
import json
import os
from pathlib import Path

import httpx
from aec_conformance_docs import (
    CONTRACT_VERSION,
    SCHEMA_NAME,
    TASK_LIMIT,
    check_contract,
    conformance_wire,
    contract,
    validate_raw,
)
from aec_grounded_docs import PAGES, ROOTS, Lookup
from aec_wire_docs import OneShotWireTransport, decode_pages
from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from run_aec_development import DIRECTORY as CONTROL
from run_aec_development import STAGES, capture, freeze_development_labels, pin, wire
from screen_aec_compact_docs import PROJECTION, project_pages, retained_lookup
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
from screen_aec_wire_docs import WIRE_POLICY, build_judgment_messages

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json, save_new
from aia_mp1.calibration import agreement
from aia_mp1.canonical_development import QWEN_MODEL_SHA, QWEN_SETTINGS
from aia_mp1.evidence_judge import completion_json
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.grounded_documentation import GroundedJudgment, candidate_catalog
from aia_mp1.judge import JudgeConfig
from aia_mp1.model_client import InstructorClient
from aia_mp1.tracing import digest, now, run_directory

DIRECTORY = "api-development-qwen-conformance-docs-001"
PREDECESSOR = "api-development-qwen-wire-docs-001"
# The reviewed final state of the stopped wire parent (handoff, November 20).
PARENT_IDENTITY = {
    "files": 45,
    "protocol.json": "c1456135128ed96240325f84e000880430ddba8efc527bd9bdd62f85958efc08",
    "execution-completion.json": "40ccfbdc394b9a258c6b0afdd3902bb65914b2dcf1f5f7ec0a059aad4e10aaba",
    "manifest_sha256": "2c0549f118f3301147872e5fc26062a3f1e54448405d10294da73b4df6b46e2a",
}
STAGE = "grounded_judgment"
WIRE_SOURCES = (
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
NEW_SOURCES = ("tools/aec_conformance_docs.py", "tools/screen_aec_conformance_docs.py")
INHERITED = (
    "development_only",
    "cases",
    "judge",
    "control_report",
    "reference",
    "lookup_inputs",
    "selectors",
    "final_instruction",
    "original_requests",
    "page_menu",
    "permitted_urls",
    "stages",
    "max_model_starts",
    "max_page_requests",
    "promotion",
    "display_projection",
    "judgment_json_separators",
    "wire_policy",
)
# Owner decision, November 20: a consumed case that yields no validated judgment is
# recorded as failed and the remaining cases still run; it counts as a non-match in
# every dimension against the ten-case denominator.
FAILURE_POLICY = (
    "continue_and_count_failed: invalid or unknown consumed outcomes are failed cases; "
    "unconsumed failures (fit, native rejection, deployment, service) stop the run"
)
CONFORMANCE_POLICY = {
    "contract_version": CONTRACT_VERSION,
    "response_format": "json_schema with nested json_schema.schema; name " + SCHEMA_NAME,
    "displayed_schema": "factored native case schema replaces the canonical schema text only",
    "restrictions": [
        "closed objects as canonical",
        "task_quote const equals the complete original task brief",
        "candidate IDs enum of the original catalog; safety restricted to safety_info",
        "tip_id enum of original tip IDs",
        "passage_id enum of shown P#.E# IDs or null",
        "documentation quote null",
    ],
    "native_normalizations": [
        "DocumentationEvidence.quote: type null, const null",
        "DocumentationEvidence.passage_id: direct enum of shown IDs plus null",
    ],
    "task_character_limit": TASK_LIMIT,
    "validation_order": [
        "logical case overlay on untouched raw text",
        "unchanged canonical GroundedJudgment",
        "unchanged validate_grounding",
    ],
    "failure_policy": FAILURE_POLICY,
    "repair": None,
    "fallback": None,
}


def judgment_inputs(original, pages, item_id, cfg):
    """Messages, bound contract and both wires for one case's shown passages."""
    messages = build_judgment_messages(original, pages)
    body = json.loads(messages[1]["content"])
    shown = decode_pages(body["online_documentation"])
    if shown != project_pages(pages):
        raise ValueError("Displayed documentation differs from projected retained pages")
    case = json.loads(original[1]["content"])
    supplied = contract(item_id, case, shown)
    instructor = schema_wire(messages, cfg, GroundedJudgment)
    return (
        messages,
        case,
        shown,
        supplied,
        (instructor, conformance_wire(instructor, messages, supplied)),
    )


class CaseFailure(ValueError):
    """A consumed model outcome that yields no validated judgment (never evidence tampering)."""


def recorded_model_failure(start, returned, identity, messages):
    """True only for an intact, matching record of an unknown, failed or unparsed outcome."""
    if not start.exists():
        return False
    recorded = read_json(start)
    if recorded.get("identity") != identity or recorded.get("messages") != messages:
        return False
    if not returned.exists():
        return True
    body = read_json(returned)
    return (
        body.get("sha256") == digest({k: v for k, v in body.items() if k != "sha256"})
        and body.get("start_sha256") == file_hash(start)
        and (body.get("parsed") is None or bool(body.get("error_type")) or bool(body.get("error")))
    )


def failure_receipt(directory, ids, item_id, stage, error, consumed, *, replay=False):
    """Durable, first-write-wins account of one case that produced no validated judgment."""
    target = directory / stage / item_id
    receipt = {
        "complete": False,
        "consumed": consumed,
        "selected_denominator": len(ids),
        "item_id": item_id,
        "stage": stage,
        "error": str(error),
        "start_sha256": file_hash(target / "start.json")
        if (target / "start.json").exists()
        else None,
        "return_sha256": file_hash(target / "return.json")
        if (target / "return.json").exists()
        else None,
    }
    # Consumed failures are final; a stop receipt may later be superseded by progress.
    kind = "failed" if consumed else "incomplete"
    path = directory / f"{item_id}-{stage}-{kind}.json"
    if not path.exists():
        if replay:
            # Offline replay never writes; a missing consumed receipt is an audit gap.
            if consumed:
                raise ValueError("Replay found a consumed failure without its retained receipt")
            return receipt
        save_new(path, receipt)
    return read_json(path)


def native_fit(server, actual):
    """Template parsing builds the native grammar; a rejection is recorded, not retried."""
    try:
        return server.token_fit(actual, 16384, 1200)
    except httpx.HTTPStatusError as error:
        raise ValueError(
            f"Native server rejected the schema-bearing request: {error.response.status_code}"
        ) from error


def check_fit(path, actual, config):
    fit = read_json(path)
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
    return file_hash(path)


def capture_judgment(directory, item_id, inputs, config, *, replay_only=False):
    """One durable attempt bound to case, pages, both schemas, protocol and fit."""
    messages, case, shown, supplied, (expected, actual) = inputs
    target = directory / STAGE / item_id
    start, returned = target / "start.json", target / "return.json"
    identity = {
        "item_id": item_id,
        "stage": STAGE,
        "protocol_sha256": file_hash(directory / "protocol.json"),
        "messages_sha256": digest({"messages": messages}),
        "model": config.model,
        "contract": supplied["binding"],
        "instructor_wire_sha256": digest(expected),
        "wire_sha256": digest(actual),
        "fit_sha256": check_fit(directory / f"{item_id}-{STAGE}-fit.json", actual, config),
    }
    if not start.exists():
        if replay_only:
            raise ValueError("Expected a retained conformance judgment for offline replay")
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
                    "contract": supplied,
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
        or recorded["contract"] != supplied
        or recorded["instructor_wire"] != expected
        or recorded["wire"] != actual
    ):
        raise ValueError("Started judgment with different inputs, contract or wire")
    if not returned.exists():
        raise CaseFailure("Unknown outcome consumes this case/stage allocation")
    body = read_json(returned)
    if (
        body["sha256"] != digest({k: v for k, v in body.items() if k != "sha256"})
        or body["start_sha256"] != file_hash(start)
        or body["model"] not in (config.model, None)
        or (body["model"] is None and not body["error_type"])
        or body["transport_calls"] != 1
    ):
        raise ValueError("Recorded conformance judgment failed integrity checks")
    if not isinstance(body["raw"], dict) or body["raw"].get("model") != config.model:
        raise CaseFailure(
            "Recorded conformance judgment failed model or transport checks: "
            f"{body['error_type'] or 'no chat completion'}"
        )
    check_contract(supplied, item_id, case, shown)
    try:
        completion_json(body["raw"])
        text = body["raw"]["choices"][0]["message"]["content"]
        parsed, ratings = validate_raw(text, supplied, item_id, case, shown)
    except ValueError as error:
        raise CaseFailure(str(error)) from error
    if body["error_type"] or body["error"] or body["parsed"] != parsed.model_dump():
        raise ValueError("Recorded client outcome differs from validated raw response")
    return ratings


def lineage(root, prior):
    """Resolve the stopped wire parent and its ancestors through recorded hashes."""
    old = read_json(prior / "protocol.json")
    for path in WIRE_SOURCES:
        if old["source"].get(path) != file_hash(Path(path)):
            raise ValueError("Frozen wire source changed")
    if list(old["source"]) != list(WIRE_SOURCES):
        raise ValueError("Frozen wire source set differs")
    if old["wire_policy"] != WIRE_POLICY:
        raise ValueError("Frozen wire policy differs")
    resolved = {}
    for field in ("predecessor", "grounded_ancestor", "completed_baseline"):
        directory = run_directory(root, old[field]["run_id"])
        if snapshot(directory) != old[field]["files_sha256"]:
            raise ValueError(f"Recorded {field} lineage differs")
        resolved[field] = directory
    compact = read_json(resolved["predecessor"] / "protocol.json")
    if (
        compact["predecessor"] != old["grounded_ancestor"]
        or compact["completed_baseline"] != old["completed_baseline"]
        or read_json(resolved["grounded_ancestor"] / "protocol.json")["predecessor"]
        != old["completed_baseline"]
    ):
        raise ValueError("Completed baseline linkage differs across ancestors")
    return old, resolved


def readonly_preflight(
    directory, prior, resolved, lineage_files, protocol, originals, cfg, requests, receipt_path
):
    """Exact schema-bearing template and tokenizer checks; never dispatches or writes."""
    if (
        read_json(directory / "protocol.json") != protocol
        or file_hash(directory / "lookup-requests.json") != protocol["lookup_inputs"]
        or file_hash(directory / "review-checkpoint.json") != protocol["reference"]
    ):
        raise ValueError("Prepared conformance inputs differ")
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
    _, _, _, supplied, (instructor_wire, judgment_wire) = judgment_inputs(
        originals[key], pages, key, cfg
    )
    lookup_wires = {k: schema_wire(messages, cfg, Lookup) for k, messages in requests.items()}
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
        fits = {k: server.token_fit(value, 16384, 1200) for k, value in lookup_wires.items()}
        diagnostic_fit = native_fit(server, judgment_wire)
        if server.json("/props") != props:
            raise ValueError("Tokenizer service changed during preflight")
        verify_deployment(deployment, directory, cfg, live=True)
    finally:
        server.close()
    if snapshot(directory) != before or snapshot(prior) != protocol["predecessor"]["files_sha256"]:
        raise ValueError("Run evidence changed during read-only preflight")
    for field, files in lineage_files.items():
        if snapshot(resolved[field]) != files:
            raise ValueError("Ancestor evidence changed during read-only preflight")
    return {
        "inference_requests": 0,
        "protocol_sha256": file_hash(directory / "protocol.json"),
        "runtime_receipt_sha256": file_hash(Path(receipt_path)),
        "lookup_fits": fits,
        "diagnostic_judgment": {
            "item_id": key,
            "retained_pages_sha256": file_hash(prior / f"{key}-pages.json"),
            "contract": supplied["binding"],
            "native_template_accepted": True,
            "fit": diagnostic_fit,
            "instructor_wire_sha256": digest(instructor_wire),
        },
        "measured_requests_fit": all(v["fits"] for v in fits.values()) and diagnostic_fit["fits"],
        "scope": "Ten lookup requests and only the first case's judgment using the stopped wire parent's retained pages. Template acceptance shows the server parsed the native schema request; it is not evidence of valid generation. Other judgment inputs remain unmeasured.",
    }


def run(root, stage, *, run_id=DIRECTORY, predecessor=PREDECESSOR, preflight_receipt=None):
    if stage not in {"prepare", "score", "replay", "preflight"}:
        raise ValueError("Unknown conformance comparison stage")
    directory = run_directory(root, run_id)
    prior = run_directory(root, predecessor)
    if prior == directory:
        raise ValueError("Output and predecessor must be different runs")
    parent = {"run_id": predecessor, "files_sha256": snapshot(prior)}
    files = parent["files_sha256"]
    if (
        len(files) != PARENT_IDENTITY["files"]
        or files.get("protocol.json") != PARENT_IDENTITY["protocol.json"]
        or files.get("execution-completion.json") != PARENT_IDENTITY["execution-completion.json"]
        or digest(files) != PARENT_IDENTITY["manifest_sha256"]
    ):
        raise ValueError("Stopped parent differs from its reviewed final state")
    if directory.exists():
        files = snapshot(directory)
        if files and "protocol.json" not in files:
            raise ValueError("Populated output has no frozen protocol; preserve and inspect it")
        if (
            "protocol.json" in files
            and read_json(directory / "protocol.json").get("predecessor") != parent
        ):
            raise ValueError("Frozen predecessor linkage differs")
    old, resolved = lineage(root, prior)
    review_parent, assessment, records, _ = load_assessment(root, REVIEW)
    ids = assessment["selected_ids"]
    if len(ids) != 10 or len(set(ids)) != 10 or ids != old["cases"]:
        raise ValueError("Exactly the ten frozen development cases are required")
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
    cats, requests = {}, {}
    for k in ids:
        case = json.loads(originals[k][1]["content"])
        cats[k] = case["untrusted_reference_context"]["task"]["category"]
        requests[k] = wire(
            SELECT, {"permitted_urls": ROOTS[cats[k]], "pages": PAGES[cats[k]], "case": case}
        )
        candidate_catalog(case)
        brief = case["untrusted_reference_context"]["task"]["brief"]
        if len(brief) > TASK_LIMIT:
            raise ValueError("Task brief exceeds the unchanged 360-character field limit")
        # Every case-level contract constraint must hold before any model start.
        contract(k, case, [])
    inherited = {
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
        "stages": {
            "grounded_lookup": Lookup.model_json_schema(),
            "grounded_judgment": GroundedJudgment.model_json_schema(),
        },
        "max_model_starts": 20,
        "max_page_requests": 30,
        "promotion": "Ten complete judgments with usable online evidence, at least eight matches on each dimension, and sound explanations.",
        "display_projection": PROJECTION,
        "judgment_json_separators": [",", ":"],
        "wire_policy": WIRE_POLICY,
    }
    if {key: old[key] for key in INHERITED} != inherited:
        raise ValueError("Stopped wire parent inputs differ from current derivation")
    if (
        read_json(prior / "lookup-requests.json") != requests
        or file_hash(prior / "review-checkpoint.json") != old["reference"]
    ):
        raise ValueError("Stopped wire parent lookup or reference differs")
    lineage_files = {field: old[field]["files_sha256"] for field in resolved}
    protocol = inherited | {
        "source": {p: file_hash(Path(p)) for p in (*WIRE_SOURCES, *NEW_SOURCES)},
        "conformance_policy": CONFORMANCE_POLICY,
        "run_id": run_id,
        "predecessor": parent,
        "compact_predecessor": old["predecessor"],
        "grounded_ancestor": old["grounded_ancestor"],
        "completed_baseline": old["completed_baseline"],
    }
    previous = previous_scores(resolved["completed_baseline"], ids, cfg)
    if snapshot(prior) != parent["files_sha256"]:
        raise ValueError("Predecessor changed during preparation")
    if stage == "preflight":
        return readonly_preflight(
            directory,
            prior,
            resolved,
            lineage_files,
            protocol,
            originals,
            cfg,
            requests,
            preflight_receipt,
        )
    directory.mkdir(exist_ok=True)
    with exclusive(directory):
        labels = freeze_development_labels(directory, review_parent, assessment, records)
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
        scores, evidence, failed = {}, {}, {}
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
                stage_name = "grounded_lookup"
                try:
                    if server and not (directory / stage_name / k / "start.json").exists():
                        fit_request(directory, k, stage_name, requests[k], cfg, server)
                        verify_deployment(deployment, directory, cfg, live=True)
                    lookup = capture(directory, k, stage_name, requests[k], cfg, replay_only=replay)
                    stage_name = "pages"
                    pages = read_pages(directory, k, cats[k], lookup, replay)
                    stage_name = STAGE
                    inputs = judgment_inputs(originals[k], pages, k, cfg)
                    pin(directory / f"{k}-contract.json", inputs[3])
                    if server and not (directory / STAGE / k / "start.json").exists():
                        fit = native_fit(server, inputs[4][1])
                        pin(directory / f"{k}-{STAGE}-fit.json", fit)
                        if not fit["fits"]:
                            raise ValueError("Schema-bearing conformance request exceeds context")
                        verify_deployment(deployment, directory, cfg, live=True)
                    scores[k] = capture_judgment(
                        directory, k, inputs, cfg, replay_only=replay
                    ).model_dump()
                except (ValueError, KeyError, OSError) as error:
                    if stage_name == "pages":
                        consumed = (directory / f"{k}-pages-start.json").exists() and not (
                            directory / f"{k}-pages.json"
                        ).exists()
                    elif stage_name == STAGE:
                        consumed = isinstance(error, CaseFailure)
                    else:
                        target = directory / stage_name / k
                        expected = {
                            "item_id": k,
                            "stage": stage_name,
                            "protocol_sha256": file_hash(directory / "protocol.json"),
                            "messages_sha256": digest({"messages": requests[k]}),
                            "model": cfg.model,
                        }
                        consumed = recorded_model_failure(
                            target / "start.json", target / "return.json", expected, requests[k]
                        )
                    receipt = failure_receipt(
                        directory, ids, k, stage_name, error, consumed, replay=replay
                    )
                    if not consumed:
                        # Nothing was spent: stop for inspection rather than lose the case.
                        raise
                    failed[k] = receipt
                    continue
                evidence[k] = {
                    "pages": file_hash(directory / f"{k}-pages.json"),
                    "contract": file_hash(directory / f"{k}-contract.json"),
                    "lookup": file_hash(directory / "grounded_lookup" / k / "return.json"),
                    "judgment": file_hash(directory / STAGE / k / "return.json"),
                    "opened": sum("http_status" in p and p["http_status"] == 200 for p in pages),
                    "requested": len(pages),
                }
        finally:
            if server:
                server.close()
        summary = agreement([r for r in records if r["item_id"] in ids], ids, labels, scores)
        pin(
            directory / "report.json",
            {
                "summary": summary,
                "evidence": evidence,
                "failed_cases": failed,
                "complete": len(scores) == len(ids),
                "paired_control": paired(scores, before, labels),
                "paired_previous": paired(scores, previous, labels),
                "selected_denominator": len(ids),
                "validated_judgments": len(scores),
                "failure_policy": FAILURE_POLICY,
                "protocol_sha256": file_hash(directory / "protocol.json"),
                "deployment_sha256": file_hash(directory / "deployment.json"),
            },
        )
        return {
            "matches": {d: v["matching"] for d, v in summary["dimensions"].items()},
            "validated_judgments": len(scores),
            "failed_cases": sorted(failed),
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
        parser.exit(1, f"Incomplete conformance comparison: {error}\n")
    print(json.dumps(result, indent=2))
