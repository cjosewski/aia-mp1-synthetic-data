"""Synthetic wire-run lineage, exact transport dispatch and interruption accounting."""

import json
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import screen_aec_compact_docs as compact
import screen_aec_grounded_docs as grounded
import screen_aec_wire_docs as runner
from aec_wire_docs import OneShotWireTransport, decode_pages
from test_aec_compact_docs import inputs as compact_inputs  # noqa: F401
from test_aec_compact_docs import page
from test_aec_grounded_judgment import response
from test_aec_grounded_runs import fake_live
from test_aec_grounded_runs import inputs as raw_inputs  # noqa: F401

from aia_mp1.assessment import read_json, save_new
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.model_client import InstructorClient


def synthetic_page(request):
    value = page(request)
    value["search_results"] = [
        {
            "anchor": anchor,
            "matched": True,
            "match_start": 0,
            "match_end": len(anchor),
            "occurrence_count": 1,
            "excerpt_ids": ["E1"],
        }
        for anchor in request["anchors"]
    ]
    return value


@pytest.fixture
def base_inputs(request):
    root, cfg, ids = request.getfixturevalue("raw_inputs")
    path = root / runner.SCREEN_MODEL / "requests.json"
    originals = read_json(path)
    for key in ids:
        originals[key][0]["content"] += "\n\nRubric:\n" + json.dumps(
            {
                "synthetic": True,
                "dimensions": {f"D{i}": "Original binary anchor" for i in range(1, 7)},
            }
        )
        target = root / runner.CONTROL / "control" / key
        start = read_json(target / "start.json")
        start["messages"] = originals[key]
        start["identity"]["messages_sha256"] = runner.digest({"messages": originals[key]})
        (target / "start.json").write_text(json.dumps(start))
        returned = read_json(target / "return.json")
        returned.pop("sha256")
        returned["start_sha256"] = runner.file_hash(target / "start.json")
        (target / "return.json").write_text(
            json.dumps(returned | {"sha256": runner.digest(returned)})
        )
    path.write_text(json.dumps(originals))
    return root, cfg, ids


@pytest.fixture
def inputs(request, monkeypatch):
    root, cfg, ids = request.getfixturevalue("compact_inputs")
    # The inherited legacy fixture had an extra search row; this new fixture is exact.
    prior = root / grounded.DIRECTORY
    path = prior / f"{ids[0]}-pages.json"
    body = read_json(path)
    body["pages"] = [synthetic_page(body["identity"]["lookup"]["pages"][0])]
    body.pop("sha256")
    path.write_text(json.dumps(body | {"sha256": runner.digest(body)}))
    compact.run(root, "prepare")
    for name in ("load_assessment", "freeze_development_labels", "LocalServer"):
        monkeypatch.setattr(runner, name, getattr(compact, name))
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


def live(monkeypatch, cfg, outcome=None):
    calls = fake_live(monkeypatch, cfg)
    calls["judgments"] = []

    class Server(grounded.LocalServer):
        def token_fit(self, wire, context, reserve):
            return super().token_fit(wire, context, reserve) | {
                "rendered_prompt_sha256": "a" * 64,
                "prompt_tokens": 100,
                "output_tokens": wire["max_tokens"],
                "reserve_tokens": reserve,
                "context_size": context,
                "required_tokens": 100 + wire["max_tokens"] + reserve,
            }

    monkeypatch.setattr(runner, "LocalServer", Server)

    def open_page(category, request):
        calls["pages"] += 1
        return synthetic_page(request.model_dump())

    monkeypatch.setattr(grounded, "open_page", open_page)

    def handler(request):
        calls["judgments"].append(json.loads(request.content))
        if isinstance(outcome, BaseException):
            raise outcome
        value = response() if outcome is None else outcome
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

    monkeypatch.setattr(
        runner,
        "OneShotWireTransport",
        lambda expected, actual: OneShotWireTransport(
            expected, actual, inner=httpx.MockTransport(handler)
        ),
    )
    return calls


def test_prepare_pins_three_generations_without_copying_lookup(inputs):
    root, _, _ = inputs
    parents = {
        name: runner.snapshot(root / name)
        for name in [runner.PREDECESSOR, grounded.DIRECTORY, grounded.PREDECESSOR]
    }
    for _ in range(2):
        assert runner.run(root, "prepare") == {"prepared": 10}
    target = root / runner.DIRECTORY
    assert set(runner.snapshot(target)) == {
        "protocol.json",
        "lookup-requests.json",
        "review-checkpoint.json",
    }
    protocol = read_json(target / "protocol.json")
    for field, name in [
        ("predecessor", runner.PREDECESSOR),
        ("grounded_ancestor", grounded.DIRECTORY),
        ("completed_baseline", grounded.PREDECESSOR),
    ]:
        assert protocol[field] == {"run_id": name, "files_sha256": parents[name]}
        assert runner.snapshot(root / name) == parents[name]
    assert len(protocol["source"]) == 21
    assert protocol["max_model_starts"] == 20 and protocol["max_page_requests"] == 30
    assert protocol["stages"] == read_json(root / runner.PREDECESSOR / "protocol.json")["stages"]


@pytest.mark.parametrize("ancestor", [runner.PREDECESSOR, grounded.DIRECTORY, grounded.PREDECESSOR])
def test_any_changed_ancestor_stops_without_new_run_changes(inputs, ancestor):
    root, _, _ = inputs
    runner.run(root, "prepare")
    before = runner.snapshot(root / runner.DIRECTORY)
    (root / ancestor / "synthetic-tamper").write_text("Synthetic mutation")
    with pytest.raises(ValueError, match="lineage|baseline differs|predecessor linkage"):
        runner.run(root, "prepare")
    assert runner.snapshot(root / runner.DIRECTORY) == before


@pytest.mark.parametrize("prompt_tokens", [100, 8000])
def test_readonly_preflight_uses_exact_transformed_wire_and_no_attempts(
    inputs, monkeypatch, prompt_tokens
):
    root, cfg, _ = inputs
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
            wires.append(json.loads(request.content))
            body = {"prompt": "Synthetic tokenizer input"}
        elif request.url.path == "/tokenize":
            body = {"tokens": [1] * prompt_tokens}
        else:
            pytest.fail(f"Forbidden preflight route {request.url.path}")
        return httpx.Response(200, json=body)

    monkeypatch.setattr(
        runner,
        "LocalServer",
        lambda base, key: LocalServer(base, key, transport=httpx.MockTransport(handler)),
    )
    result = runner.run(root, "preflight", preflight_receipt=receipt)
    assert result["measured_requests_fit"] is (prompt_tokens == 100)
    assert result["inference_requests"] == 0
    assert routes.count("/apply-template") == routes.count("/tokenize") == 11
    assert runner.digest(wires[-1]) == result["diagnostic_judgment"]["fit"]["wire_sha256"]
    assert result["diagnostic_judgment"]["instructor_wire_sha256"] != runner.digest(wires[-1])
    assert (
        json.dumps(runner.GroundedJudgment.model_json_schema(), indent=2)
        not in wires[-1]["messages"][0]["content"]
    )
    assert "SYNTHETIC_NOT_FOR_MODEL" not in str(wires)
    assert runner.snapshot(root) == before


def test_score_transmits_measured_wire_replays_offline_and_preserves_all_ancestors(
    inputs, monkeypatch
):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    parents = {
        name: runner.snapshot(root / name)
        for name in [runner.PREDECESSOR, grounded.DIRECTORY, grounded.PREDECESSOR]
    }
    calls = live(monkeypatch, cfg)
    result = runner.run(root, "score")
    assert len(calls["model"]) == len(calls["judgments"]) == calls["pages"] == 10
    target = root / runner.DIRECTORY
    for key, sent in zip(ids, calls["judgments"], strict=True):
        started = read_json(target / "grounded_judgment" / key / "start.json")
        fit = read_json(target / f"{key}-grounded_judgment-fit.json")
        assert sent == started["wire"]
        assert runner.digest(sent) == fit["wire_sha256"] == started["identity"]["wire_sha256"]
        assert sent != started["instructor_wire"]
        shown = decode_pages(json.loads(started["messages"][1]["content"])["online_documentation"])
        assert shown == runner.project_pages(read_json(target / f"{key}-pages.json")["pages"])
    before = runner.snapshot(target)
    assert runner.run(root, "replay") == result
    assert runner.snapshot(target) == before
    assert len(calls["judgments"]) == 10
    report = read_json(target / "report.json")
    assert report["paired_control"] == report["paired_previous"] == dict.fromkeys(ids, {})
    assert all(runner.snapshot(root / name) == snapshot for name, snapshot in parents.items())


@pytest.mark.parametrize("kind", ["invalid", "transport", "grounding"])
def test_failed_judgment_return_remains_consumed_with_raw_response_or_failure(
    inputs, monkeypatch, kind
):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    value = response()
    if kind == "invalid":
        value["ratings"]["D1"]["decision"] = 2
    elif kind == "grounding":
        value["safety"]["candidate_ids"] = ["steps[0]"]
    else:
        value = httpx.ReadTimeout("Synthetic transport failure")
    calls = live(monkeypatch, cfg, value)
    for _ in range(2):
        with pytest.raises(ValueError, match="response checks|safety_info"):
            runner.run(root, "score")
    assert len(calls["model"]) == len(calls["judgments"]) == calls["pages"] == 1
    target = root / runner.DIRECTORY
    returned = read_json(target / "grounded_judgment" / ids[0] / "return.json")
    assert returned["raw"] is not None if kind != "transport" else returned["raw"] is None
    assert not (target / "report.json").exists()


def test_unknown_judgment_never_dispatches_again(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    calls = live(monkeypatch, cfg, KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        runner.run(root, "score")
    with pytest.raises(ValueError, match="Unknown outcome consumes"):
        runner.run(root, "score")
    target = root / runner.DIRECTORY / "grounded_judgment" / ids[0]
    assert (target / "start.json").exists() and not (target / "return.json").exists()
    assert len(calls["judgments"]) == 1


def test_judgment_oversize_stops_after_lookup_before_judgment_start(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    calls = live(monkeypatch, cfg)
    base = runner.LocalServer

    class Oversize(base):
        def token_fit(self, wire, context, reserve):
            value = super().token_fit(wire, context, reserve)
            if "GroundedJudgment" in str(wire):
                value["fits"] = False
            return value

    monkeypatch.setattr(runner, "LocalServer", Oversize)
    with pytest.raises(ValueError, match="exceeds context"):
        runner.run(root, "score")
    assert len(calls["model"]) == calls["pages"] == 1 and calls["judgments"] == []
    target = root / runner.DIRECTORY
    assert not (target / "grounded_judgment" / ids[0] / "start.json").exists()
    assert read_json(target / f"{ids[0]}-grounded_judgment-incomplete.json")["start_sha256"] is None


def test_instructor_wire_drift_is_consumed_without_network_forwarding(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    calls = live(monkeypatch, cfg)

    class Drift(InstructorClient):
        def generate(self, messages):
            changed = deepcopy(messages)
            changed[0]["content"] += " Synthetic drift"
            return super().generate(changed)

    monkeypatch.setattr(runner, "InstructorClient", Drift)
    for _ in range(2):
        with pytest.raises(ValueError, match="response checks"):
            runner.run(root, "score")
    assert len(calls["model"]) == 1 and calls["judgments"] == []
    body = read_json(root / runner.DIRECTORY / "grounded_judgment" / ids[0] / "return.json")
    assert body["raw"] is None and body["error_type"] is not None


def test_replay_rejects_tampered_transmitted_wire_and_fit(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime(root, cfg)
    calls = live(monkeypatch, cfg)
    runner.run(root, "score")
    target = root / runner.DIRECTORY
    fit_path = target / f"{ids[0]}-grounded_judgment-fit.json"
    fit_bytes = fit_path.read_bytes()
    fit = read_json(fit_path)
    fit_path.write_text(json.dumps(fit | {"wire_sha256": "0" * 64}))
    with pytest.raises(ValueError, match="successful measured fit"):
        runner.run(root, "replay")
    fit_path.write_text(json.dumps(fit | {"prompt_tokens": 101, "required_tokens": 9493}))
    with pytest.raises(ValueError, match="different inputs or wire"):
        runner.run(root, "replay")
    fit_path.write_bytes(fit_bytes)
    start_path = target / "grounded_judgment" / ids[0] / "start.json"
    start = read_json(start_path)
    start["wire"]["temperature"] = 0.9
    start_path.write_text(json.dumps(start))
    with pytest.raises(ValueError, match="different inputs or wire"):
        runner.run(root, "replay")
    assert len(calls["judgments"]) == 10
