"""Synthetic conformance-run lineage, native-schema wire, validation order and accounting."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import screen_aec_compact_docs as compact
import screen_aec_conformance_docs as runner
import screen_aec_grounded_docs as grounded
import screen_aec_wire_docs as wire
from aec_wire_docs import OneShotWireTransport, decode_pages
from test_aec_grounded_judgment import response
from test_aec_grounded_runs import fake_live
from test_aec_wire_docs_runs import (  # noqa: F401
    base_inputs,
    compact_inputs,
    raw_inputs,
    synthetic_page,
)
from test_aec_wire_docs_runs import inputs as wire_inputs  # noqa: F401
from test_aec_wire_docs_runs import live as wire_live
from test_aec_wire_docs_runs import runtime as wire_runtime

from aia_mp1.assessment import read_json, save_new
from aia_mp1.factcheck_transport import LocalServer

ANCESTORS = [runner.PREDECESSOR, wire.PREDECESSOR, grounded.DIRECTORY, grounded.PREDECESSOR]


@pytest.fixture
def inputs(request, monkeypatch):
    """A wire parent stopped after one schema-invalid judgment, as in the retained run."""
    root, cfg, ids = request.getfixturevalue("wire_inputs")
    wire.run(root, "prepare")
    wire_runtime(root, cfg)
    invalid = response()
    invalid["safety"]["note_detail"] = "SYNTHETIC extra field"
    wire_live(monkeypatch, cfg, invalid)
    with pytest.raises(ValueError, match="response checks"):
        wire.run(root, "score")
    for name in ("load_assessment", "freeze_development_labels"):
        monkeypatch.setattr(runner, name, getattr(compact, name))
    files = runner.snapshot(root / runner.PREDECESSOR)
    monkeypatch.setattr(
        runner,
        "PARENT_IDENTITY",
        {
            "files": len(files),
            "protocol.json": files["protocol.json"],
            "execution-completion.json": files.get("execution-completion.json"),
            "manifest_sha256": runner.digest(files),
        },
    )
    return root, cfg, ids


def runtime(root, cfg, *, outside=False):
    now = datetime.now(timezone.utc)
    path = root / "runtime.json" if outside else root / runner.DIRECTORY / "deployment.json"
    save_new(
        path,
        {
            "parts": grounded.QWEN_FILES,
            "model": cfg.model,
            "reasoning_budget": 4096,
            "build": "synthetic",
            "protocol_sha256": runner.file_hash(root / runner.DIRECTORY / "protocol.json"),
            "launched_at": (now - timedelta(minutes=1)).isoformat(),
            "verified_at": now.isoformat(),
            "maximum_server_lifetime_seconds": 14400,
        },
    )
    return path


def conformant(body, decision=1):
    """A synthetic response satisfying the case contract carried by the sent request."""
    content = json.loads(body["messages"][1]["content"])
    task = content["untrusted_reference_context"]["task"]["brief"]
    tips = [key for key in content["candidate_field_ids"] if key.startswith("tips[")]
    shown = decode_pages(content["online_documentation"])
    note = "SYNTHETIC only"
    row = {"candidate_ids": ["answer"], "status": "uncertain", "note": note, "task_quote": task}
    return {
        "task_checks": [row],
        "safety": {"candidate_ids": ["safety_info"], "status": "uncertain", "note": note},
        "bindings": [dict(row)],
        "tips": [
            {"candidate_ids": [tip], "status": "uncertain", "note": note, "tip_id": tip}
            for tip in tips
        ],
        "documentation": [
            {
                "candidate_id": "answer",
                "passage_id": f"{shown[0]['id']}.{shown[0]['excerpts'][0]['id']}",
                "quote": None,
                "status": "uncertain",
                "note": note,
            }
        ],
        "ratings": {
            f"D{i}": {"decision": decision, "justification": "SYNTHETIC."} for i in range(1, 7)
        },
    }


def live(monkeypatch, cfg, outcome=conformant, *, reject_native=False):
    calls = fake_live(monkeypatch, cfg)
    calls["judgments"] = []

    class Server(grounded.LocalServer):
        def token_fit(self, sent, context, reserve):
            if reject_native and sent.get("response_format", {}).get("type") == "json_schema":
                request = httpx.Request("POST", "http://synthetic/apply-template")
                raise httpx.HTTPStatusError(
                    "Synthetic rejection", request=request, response=httpx.Response(400)
                )
            return super().token_fit(sent, context, reserve) | {
                "rendered_prompt_sha256": "a" * 64,
                "prompt_tokens": 100,
                "output_tokens": sent["max_tokens"],
                "reserve_tokens": reserve,
                "context_size": context,
                "required_tokens": 100 + sent["max_tokens"] + reserve,
            }

    monkeypatch.setattr(runner, "LocalServer", Server)

    def open_page(category, request):
        calls["pages"] += 1
        return synthetic_page(request.model_dump())

    monkeypatch.setattr(grounded, "open_page", open_page)

    def handler(request):
        body = json.loads(request.content)
        calls["judgments"].append(body)
        if isinstance(outcome, BaseException):
            raise outcome
        return httpx.Response(
            200,
            json={
                "id": "synthetic-completion",
                "object": "chat.completion",
                "created": 1,
                "model": cfg.model,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(outcome(body))},
                    }
                ],
            },
        )

    monkeypatch.setattr(
        runner,
        "OneShotWireTransport",
        lambda expected, actual: OneShotWireTransport(
            expected, actual, inner=httpx.MockTransport(handler)
        ),
    )
    return calls


def test_prepare_binds_stopped_parent_and_resolves_completed_baseline_through_lineage(inputs):
    root, _, _ = inputs
    parents = {name: runner.snapshot(root / name) for name in ANCESTORS}
    assert "grounded_judgment/" + inputs[2][0] + "/return.json" in parents[runner.PREDECESSOR]
    for _ in range(2):
        assert runner.run(root, "prepare") == {"prepared": 10}
    target = root / runner.DIRECTORY
    assert set(runner.snapshot(target)) == {
        "protocol.json",
        "lookup-requests.json",
        "review-checkpoint.json",
    }
    protocol = read_json(target / "protocol.json")
    old = read_json(root / runner.PREDECESSOR / "protocol.json")
    assert protocol["predecessor"] == {
        "run_id": runner.PREDECESSOR,
        "files_sha256": parents[runner.PREDECESSOR],
    }
    assert protocol["compact_predecessor"] == old["predecessor"]
    assert protocol["grounded_ancestor"] == old["grounded_ancestor"]
    assert protocol["completed_baseline"] == old["completed_baseline"]
    assert {key: protocol[key] for key in runner.INHERITED} == {
        key: old[key] for key in runner.INHERITED
    }
    assert {key: protocol["source"][key] for key in old["source"]} == old["source"]
    assert len(protocol["source"]) == 23
    assert protocol["max_model_starts"] == 20 and protocol["max_page_requests"] == 30
    assert protocol["conformance_policy"]["repair"] is None
    assert all(runner.snapshot(root / name) == parents[name] for name in ANCESTORS)


@pytest.mark.parametrize("ancestor", ANCESTORS)
def test_any_changed_ancestor_stops_without_new_run_changes(inputs, ancestor):
    root, _, _ = inputs
    runner.run(root, "prepare")
    before = runner.snapshot(root / runner.DIRECTORY)
    (root / ancestor / "synthetic-tamper").write_text("Synthetic mutation")
    with pytest.raises(ValueError, match="lineage|predecessor linkage|reviewed final state"):
        runner.run(root, "prepare")
    assert runner.snapshot(root / runner.DIRECTORY) == before


def test_changed_frozen_wire_source_set_is_rejected(inputs, monkeypatch):
    root, _, _ = inputs
    monkeypatch.setattr(runner, "WIRE_SOURCES", runner.WIRE_SOURCES[::-1])
    with pytest.raises(ValueError, match="source set differs"):
        runner.run(root, "prepare")
    assert not (root / runner.DIRECTORY).exists()


@pytest.mark.parametrize("rejected", [False, True])
def test_readonly_preflight_sends_exact_native_schema_wire_and_makes_no_attempts(
    inputs, monkeypatch, rejected
):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    receipt = runtime(root, cfg, outside=True)
    before = runner.snapshot(root)
    wires, routes = [], []

    def handler(request):
        routes.append(request.url.path)
        if request.url.path == "/props":
            body = {
                "model_path": cfg.model,
                "build_info": "synthetic",
                "total_slots": 1,
                "default_generation_settings": {"n_ctx": 16384},
            }
        elif request.url.path == "/apply-template":
            sent = json.loads(request.content)
            wires.append(sent)
            if rejected and sent["response_format"].get("type") == "json_schema":
                return httpx.Response(400, json={"error": "Synthetic grammar rejection"})
            body = {"prompt": "Synthetic tokenizer input"}
        elif request.url.path == "/tokenize":
            body = {"tokens": [1] * 100}
        else:
            pytest.fail(f"Forbidden preflight route {request.url.path}")
        return httpx.Response(200, json=body)

    monkeypatch.setattr(
        runner,
        "LocalServer",
        lambda base, key: LocalServer(base, key, transport=httpx.MockTransport(handler)),
    )
    if rejected:
        with pytest.raises(ValueError, match="rejected the schema-bearing request"):
            runner.run(root, "preflight", preflight_receipt=receipt)
    else:
        result = runner.run(root, "preflight", preflight_receipt=receipt)
        assert result["measured_requests_fit"] is True and result["inference_requests"] == 0
        assert runner.digest(wires[-1]) == result["diagnostic_judgment"]["fit"]["wire_sha256"]
        assert routes.count("/apply-template") == routes.count("/tokenize") == 11
    judgment = wires[-1]
    schema = judgment["response_format"]["json_schema"]["schema"]
    assert judgment["response_format"]["json_schema"]["name"] == "GroundedJudgment"
    assert (
        json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        in (judgment["messages"][0]["content"])
    )
    content = json.loads(judgment["messages"][1]["content"])
    task = content["untrusted_reference_context"]["task"]["brief"]
    assert task in json.dumps(schema, ensure_ascii=False)
    assert "SYNTHETIC_NOT_FOR_MODEL" not in str(wires)
    assert runner.snapshot(root) == before


def test_score_sends_bound_native_contract_replays_offline_and_preserves_ancestors(
    inputs, monkeypatch
):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    parents = {name: runner.snapshot(root / name) for name in ANCESTORS}
    calls = live(monkeypatch, cfg)
    result = runner.run(root, "score")
    assert len(calls["model"]) == len(calls["judgments"]) == calls["pages"] == 10
    target = root / runner.DIRECTORY
    for key, sent in zip(ids, calls["judgments"], strict=True):
        started = read_json(target / "grounded_judgment" / key / "start.json")
        fit = read_json(target / f"{key}-grounded_judgment-fit.json")
        contract = read_json(target / f"{key}-contract.json")
        assert sent == started["wire"] and started["contract"] == contract
        assert runner.digest(sent) == fit["wire_sha256"] == started["identity"]["wire_sha256"]
        assert sent["response_format"]["json_schema"]["schema"] == contract["factored"]
        assert started["instructor_wire"]["response_format"] == {"type": "json_object"}
        assert started["identity"]["contract"] == contract["binding"]
        shown = decode_pages(json.loads(started["messages"][1]["content"])["online_documentation"])
        assert shown == runner.project_pages(read_json(target / f"{key}-pages.json")["pages"])
        assert contract["binding"]["shown_pages_sha256"] == runner.digest(shown)
    before = runner.snapshot(target)
    assert runner.run(root, "replay") == result
    assert runner.snapshot(target) == before
    assert len(calls["judgments"]) == 10
    report = read_json(target / "report.json")
    assert report["validated_judgments"] == report["selected_denominator"] == 10
    assert all(runner.snapshot(root / name) == parents[name] for name in ANCESTORS)


def _quote_span(body):
    value = conformant(body)
    value["task_checks"][0]["task_quote"] = value["task_checks"][0]["task_quote"][:12]
    return value


def _page_only(body):
    value = conformant(body)
    value["documentation"][0]["passage_id"] = "P1"
    return value


def _tips_reversed(body):
    value = conformant(body)
    value["tips"].reverse()
    return value


def test_native_rejection_stops_after_lookup_before_judgment_start(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    calls = live(monkeypatch, cfg, reject_native=True)
    with pytest.raises(ValueError, match="rejected the schema-bearing request"):
        runner.run(root, "score")
    assert len(calls["model"]) == calls["pages"] == 1 and calls["judgments"] == []
    target = root / runner.DIRECTORY
    assert not (target / "grounded_judgment" / ids[0] / "start.json").exists()
    assert read_json(target / f"{ids[0]}-grounded_judgment-incomplete.json")["start_sha256"] is None


def test_replay_rejects_tampered_contract_fit_or_wire(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    calls = live(monkeypatch, cfg)
    runner.run(root, "score")
    target = root / runner.DIRECTORY
    start_path = target / "grounded_judgment" / ids[0] / "start.json"
    original = start_path.read_bytes()
    start = read_json(start_path)
    start["contract"]["logical"]["$defs"]["TaskEvidence"]["properties"]["task_quote"]["const"] = (
        "SYNTHETIC stale task"
    )
    start_path.write_text(json.dumps(start))
    with pytest.raises(ValueError, match="different inputs, contract or wire"):
        runner.run(root, "replay")
    start = json.loads(original)
    start["wire"]["response_format"] = {"type": "json_object"}
    start_path.write_text(json.dumps(start))
    with pytest.raises(ValueError, match="different inputs, contract or wire"):
        runner.run(root, "replay")
    start_path.write_bytes(original)
    fit_path = target / f"{ids[0]}-grounded_judgment-fit.json"
    fit = read_json(fit_path)
    fit_path.write_text(json.dumps(fit | {"wire_sha256": "0" * 64}))
    with pytest.raises(ValueError, match="successful measured fit"):
        runner.run(root, "replay")
    assert len(calls["judgments"]) == 10


def test_parent_altered_before_first_prepare_is_rejected(inputs):
    root, _, _ = inputs
    (root / runner.PREDECESSOR / "runtime-late-log.txt").write_text("Synthetic late file")
    with pytest.raises(ValueError, match="reviewed final state"):
        runner.run(root, "prepare")
    assert not (root / runner.DIRECTORY).exists()


def test_real_parent_identity_is_the_reviewed_45_file_state():
    assert runner.PARENT_IDENTITY["files"] == 45
    assert runner.PARENT_IDENTITY["protocol.json"].startswith("c1456135")
    assert runner.PARENT_IDENTITY["execution-completion.json"].startswith("40ccfbdc")


def once(index, failure):
    """Fail only the index-th judgment request; every other request is conformant."""
    sent = []

    def outcome(body):
        sent.append(body)
        if len(sent) - 1 == index:
            if isinstance(failure, BaseException):
                raise failure
            return failure(body)
        return conformant(body)

    return outcome, sent


@pytest.mark.parametrize("index", [0, 2])
@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (_quote_span, "required constant"),
        (_page_only, "allowed identifier"),
        (_tips_reversed, "every original tip in order"),
        (httpx.ReadTimeout("Synthetic transport failure"), "transport checks"),
    ],
)
def test_consumed_invalid_case_is_failed_and_remaining_cases_still_run(
    inputs, monkeypatch, index, failure, message
):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    outcome, sent = once(index, failure)
    calls = live(monkeypatch, cfg, outcome)
    monkeypatch.setattr(
        runner,
        "OneShotWireTransport",
        lambda expected, actual: OneShotWireTransport(
            expected, actual, inner=httpx.MockTransport(handler_for(cfg, outcome, calls))
        ),
    )
    result = runner.run(root, "score")
    assert result["failed_cases"] == [ids[index]] and result["validated_judgments"] == 9
    assert len(calls["model"]) == calls["pages"] == len(calls["judgments"]) == 10
    target = root / runner.DIRECTORY
    report = read_json(target / "report.json")
    failed = report["failed_cases"][ids[index]]
    assert failed["consumed"] is True and failed["stage"] == "grounded_judgment"
    assert message in failed["error"] and report["complete"] is False
    assert report["selected_denominator"] == 10
    assert all(v["compared"] == 9 for v in report["summary"]["dimensions"].values())
    returned = read_json(target / "grounded_judgment" / ids[index] / "return.json")
    assert (returned["raw"] is None) is isinstance(failure, BaseException)
    before = runner.snapshot(target)
    assert runner.run(root, "replay") == result
    assert runner.run(root, "score") == result
    assert runner.snapshot(target) == before and len(calls["judgments"]) == 10


def handler_for(cfg, outcome, calls):
    def handler(request):
        body = json.loads(request.content)
        calls["judgments"].append(body)
        value = outcome(body)
        return httpx.Response(
            200,
            json={
                "id": "synthetic-completion",
                "object": "chat.completion",
                "created": 1,
                "model": cfg.model,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(value)},
                    }
                ],
            },
        )

    return handler


def test_unknown_outcome_is_failed_on_rerun_and_never_dispatched_again(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    outcome, _ = once(0, KeyboardInterrupt())
    calls = live(monkeypatch, cfg, outcome)
    monkeypatch.setattr(
        runner,
        "OneShotWireTransport",
        lambda expected, actual: OneShotWireTransport(
            expected, actual, inner=httpx.MockTransport(handler_for(cfg, outcome, calls))
        ),
    )
    with pytest.raises(KeyboardInterrupt):
        runner.run(root, "score")
    target = root / runner.DIRECTORY / "grounded_judgment" / ids[0]
    assert (target / "start.json").exists() and not (target / "return.json").exists()
    result = runner.run(root, "score")
    assert result["failed_cases"] == [ids[0]] and result["validated_judgments"] == 9
    report = read_json(root / runner.DIRECTORY / "report.json")
    assert "Unknown outcome consumes" in report["failed_cases"][ids[0]]["error"]
    assert len(calls["judgments"]) == 10


def test_non_json_body_is_a_consumed_integrity_failure_and_others_continue(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    calls = live(monkeypatch, cfg)
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        if len(sent) == 1:
            return httpx.Response(200, text="SYNTHETIC non-JSON body")
        return handler_for(cfg, conformant, {"judgments": []})(request)

    monkeypatch.setattr(
        runner,
        "OneShotWireTransport",
        lambda expected, actual: OneShotWireTransport(
            expected, actual, inner=httpx.MockTransport(handler)
        ),
    )
    result = runner.run(root, "score")
    assert result["failed_cases"] == [ids[0]] and len(sent) == 10
    report = read_json(root / runner.DIRECTORY / "report.json")
    assert "model or transport checks" in report["failed_cases"][ids[0]]["error"]
    returned = read_json(root / runner.DIRECTORY / "grounded_judgment" / ids[0] / "return.json")
    assert not isinstance(returned["raw"], dict)
    assert len(calls["model"]) == 10


def test_unknown_lookup_outcome_is_a_failed_case_and_tampered_lookup_stops(inputs, monkeypatch):
    import run_aec_development as development

    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    calls = live(monkeypatch, cfg)
    base = development.InstructorClient

    class InterruptFirstLookup(base):
        def generate(self, messages):
            if not calls["model"]:
                calls["model"].append(messages)
                raise KeyboardInterrupt
            return super().generate(messages)

    monkeypatch.setattr(development, "InstructorClient", InterruptFirstLookup)
    with pytest.raises(KeyboardInterrupt):
        runner.run(root, "score")
    result = runner.run(root, "score")
    assert result["failed_cases"] == [ids[0]] and result["validated_judgments"] == 9
    target = root / runner.DIRECTORY
    failed = read_json(target / "report.json")["failed_cases"][ids[0]]
    assert failed["stage"] == "grounded_lookup" and failed["consumed"] is True
    assert len(calls["model"]) == 10 and len(calls["judgments"]) == 9
    path = target / "grounded_lookup" / ids[1] / "return.json"
    body = read_json(path)
    path.write_text(json.dumps(body | {"sha256": "0" * 64}))
    with pytest.raises(ValueError, match="integrity"):
        runner.run(root, "replay")


def test_stop_receipt_does_not_mask_a_later_consumed_failure(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    live(monkeypatch, cfg, reject_native=True)
    with pytest.raises(ValueError, match="rejected the schema-bearing request"):
        runner.run(root, "score")
    target = root / runner.DIRECTORY
    stop = read_json(target / f"{ids[0]}-grounded_judgment-incomplete.json")
    assert stop["consumed"] is False
    outcome, _ = once(0, _page_only)
    calls = live(monkeypatch, cfg, outcome)
    monkeypatch.setattr(
        runner,
        "OneShotWireTransport",
        lambda expected, actual: OneShotWireTransport(
            expected, actual, inner=httpx.MockTransport(handler_for(cfg, outcome, calls))
        ),
    )
    result = runner.run(root, "score")
    assert result["failed_cases"] == [ids[0]]
    failed = read_json(target / "report.json")["failed_cases"][ids[0]]
    assert failed["consumed"] is True and "allowed identifier" in failed["error"]
    assert read_json(target / f"{ids[0]}-grounded_judgment-incomplete.json") == stop


def test_altered_lookup_start_without_return_stops_instead_of_counting_failed(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    target = root / runner.DIRECTORY / "grounded_lookup" / ids[0]
    target.mkdir(parents=True)
    save_new(
        target / "start.json",
        {"identity": {"item_id": ids[0], "stage": "foreign"}, "messages": []},
    )
    calls = live(monkeypatch, cfg)
    with pytest.raises(ValueError, match="different inputs"):
        runner.run(root, "score")
    assert not (root / runner.DIRECTORY / f"{ids[0]}-grounded_lookup-failed.json").exists()
    assert calls["model"] == [] and calls["judgments"] == []


def test_replay_never_recreates_a_deleted_failed_receipt(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    outcome, _ = once(0, _page_only)
    calls = live(monkeypatch, cfg, outcome)
    monkeypatch.setattr(
        runner,
        "OneShotWireTransport",
        lambda expected, actual: OneShotWireTransport(
            expected, actual, inner=httpx.MockTransport(handler_for(cfg, outcome, calls))
        ),
    )
    runner.run(root, "score")
    receipt = root / runner.DIRECTORY / f"{ids[0]}-grounded_judgment-failed.json"
    receipt.unlink()
    before = runner.snapshot(root / runner.DIRECTORY)
    with pytest.raises(ValueError, match="without its retained receipt"):
        runner.run(root, "replay")
    assert runner.snapshot(root / runner.DIRECTORY) == before
