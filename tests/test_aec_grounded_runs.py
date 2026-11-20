"""Synthetic bounded-run execution and replay; all model/page dispatches are local fakes."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_aec_development as development
import screen_aec_grounded_docs as runner
from test_aec_grounded_judgment import case, response

from aia_mp1.assessment import read_json, save_new
from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.judge import JudgeConfig
from aia_mp1.tracing import digest


def retained(directory, key, stage, messages, cfg, parsed=None):
    target = directory / stage / key
    target.mkdir(parents=True)
    start = target / "start.json"
    save_new(
        start,
        {
            "identity": {
                "item_id": key,
                "stage": stage,
                "protocol_sha256": runner.file_hash(directory / "protocol.json"),
                "messages_sha256": digest({"messages": messages}),
                "model": cfg.model,
            },
            "started_at": "synthetic",
            "messages": messages,
        },
    )
    if parsed is not None:
        body = {
            "start_sha256": runner.file_hash(start),
            "completed_at": "synthetic",
            "raw": {
                "model": cfg.model,
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(parsed)}}],
            },
            "model": cfg.model,
            "parsed": parsed,
            "error_type": None,
            "error": None,
        }
        save_new(target / "return.json", body | {"sha256": digest(body)})


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    root = tmp_path
    cfg = JudgeConfig(
        base_url="http://127.0.0.1:18082/v1",
        model="/synthetic/qwen.gguf",
        model_sha256=runner.QWEN_MODEL_SHA,
        **runner.QWEN_SETTINGS,
    )
    (root / "judge-preparation-v1").mkdir()
    save_new(root / "judge-preparation-v1/judge.json", cfg.model_dump())
    ids = [f"synthetic-{i}" for i in range(10)]
    ratings = response()["ratings"]
    records = [{"item_id": key} for key in ids]
    monkeypatch.setattr(
        runner, "load_assessment", lambda *a: (root / "review", {"selected_ids": ids}, records, {})
    )
    checkpoint = {"private_label_sentinel": "SYNTHETIC_NOT_FOR_MODEL"}

    def freeze(directory, *args):
        runner.pin(directory / "review-checkpoint.json", checkpoint)
        return {key: {"decisions": dict.fromkeys(DIMENSIONS, 1)} for key in ids}

    monkeypatch.setattr(runner, "freeze_development_labels", freeze)

    def no_network(*args, **kwargs):
        pytest.fail("Unexpected network/model dispatch")

    monkeypatch.setattr(runner, "LocalServer", no_network)
    monkeypatch.setattr(runner, "open_page", no_network)
    monkeypatch.setattr(development, "LocalServer", no_network)
    monkeypatch.setattr(development, "InstructorClient", no_network)
    control = root / runner.CONTROL
    control.mkdir()
    save_new(control / "protocol.json", {"synthetic": True})
    save_new(control / "control-report.json", {"synthetic": True})
    save_new(control / "review-checkpoint.json", checkpoint)
    originals = {}
    for i, key in enumerate(ids):
        payload = case()
        payload["untrusted_reference_context"]["task"]["category"] = list(runner.PAGES)[i % 5]
        originals[key] = runner.wire("Synthetic original binary anchors", payload)
        retained(control, key, "control", originals[key], cfg, ratings)
    (root / runner.SCREEN_MODEL).mkdir()
    save_new(root / runner.SCREEN_MODEL / "requests.json", originals)
    prior = root / runner.PREDECESSOR
    prior.mkdir()
    old_requests = {
        key: runner.wire("Historical selector", {"case": json.loads(originals[key][1]["content"])})
        for key in ids
    }
    save_new(prior / "lookup-requests.json", old_requests)
    save_new(prior / "review-checkpoint.json", checkpoint)
    save_new(
        prior / "protocol.json",
        {
            "development_only": True,
            "cases": ids,
            "judge": cfg.public_settings(),
            "control_report": runner.file_hash(control / "control-report.json"),
            "reference": runner.file_hash(control / "review-checkpoint.json"),
            "lookup_inputs": runner.file_hash(prior / "lookup-requests.json"),
            "max_model_starts": 20,
            "max_page_requests": 30,
            "promotion": "Ten complete judgments with usable online evidence, at least eight matches on each dimension, and sound explanations.",
        },
    )
    for key in ids:
        retained(prior, key, "documented", originals[key], cfg, ratings)
    (prior / ".writer.lock").write_text("Synthetic preserved marker")
    return root, cfg, ids


def deployment(root, cfg, **changes):
    now = datetime.now(timezone.utc)
    body = {
        "parts": runner.QWEN_FILES,
        "model": cfg.model,
        "reasoning_budget": 4096,
        "protocol_sha256": runner.file_hash(root / runner.DIRECTORY / "protocol.json"),
        "build": "synthetic",
        "launched_at": (now - timedelta(minutes=5)).isoformat(),
        "verified_at": now.isoformat(),
        "maximum_server_lifetime_seconds": 14400,
    }
    body.update(changes)
    save_new(root / runner.DIRECTORY / "deployment.json", body)


def fake_live(monkeypatch, cfg, output=None):
    calls = {"model": [], "pages": 0, "fits": []}

    class Server:
        def __init__(self, *a):
            pass

        def json(self, route):
            return {
                "/health": {"status": "ok"},
                "/v1/models": {"data": [{"id": cfg.model}]},
                "/props": {
                    "model_path": cfg.model,
                    "build_info": "synthetic",
                    "total_slots": 1,
                    "default_generation_settings": {"n_ctx": 16384},
                },
            }[route]

        def token_fit(self, wire, context, reserve):
            assert "GroundedJudgment" in str(wire) or "Lookup" in str(wire)
            calls["fits"].append(wire)
            return {"fits": True, "wire_sha256": digest(wire)}

        def close(self):
            pass

    class Client:
        def __init__(self, **kwargs):
            self.schema = kwargs["response_model"]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def generate(self, messages):
            calls["model"].append(messages)
            if self.schema is runner.Lookup:
                payload = json.loads(messages[1]["content"])
                value = {
                    "pages": [
                        {
                            "page": next(iter(payload["pages"])),
                            "anchors": ["operation"],
                            "claim": "Synthetic.",
                        }
                    ]
                }
            else:
                value = response() if output is None else output
            try:
                item = self.schema.model_validate(value)
                failure = None
            except ValueError:
                item = None
                failure = "ValidationError"
            return SimpleNamespace(
                raw_response={
                    "model": cfg.model,
                    "choices": [
                        {"finish_reason": "stop", "message": {"content": json.dumps(value)}}
                    ],
                },
                response_model=cfg.model,
                item=item,
                error_type=failure,
                error=failure,
            )

    def page(category, request):
        calls["pages"] += 1
        return {
            "request": request.model_dump(),
            "http_status": 200,
            "evidence_status": "matched",
            "excerpts": [{"id": "E1", "text": "A bounded operation."}],
            "opened_at": "synthetic",
        }

    monkeypatch.setattr(runner, "LocalServer", Server)
    monkeypatch.setattr(development, "LocalServer", Server)
    monkeypatch.setattr(development, "InstructorClient", Client)
    monkeypatch.setattr(runner, "open_page", page)
    return calls


def test_prepare_and_replay_are_offline_preserve_parent_and_exclude_labels(inputs, monkeypatch):
    root, cfg, ids = inputs
    parent_before = runner.snapshot(root / runner.PREDECESSOR)
    assert runner.run(root, "prepare") == {"prepared": 10}
    target = root / runner.DIRECTORY
    assert set(runner.snapshot(target)) == {
        "protocol.json",
        "lookup-requests.json",
        "review-checkpoint.json",
    }
    assert "SYNTHETIC_NOT_FOR_MODEL" not in (target / "lookup-requests.json").read_text()
    deployment(root, cfg)
    calls = fake_live(monkeypatch, cfg)
    result = runner.run(root, "score")
    assert len(calls["model"]) == 20 and calls["pages"] == 10 and len(calls["fits"]) == 20
    assert "SYNTHETIC_NOT_FOR_MODEL" not in json.dumps(calls["model"])
    assert runner.run(root, "replay") == result
    assert len(calls["model"]) == 20 and calls["pages"] == 10
    assert runner.snapshot(root / runner.PREDECESSOR) == parent_before
    report = read_json(target / "report.json")
    assert report["selected_denominator"] == report["validated_judgments"] == 10
    assert report["paired_previous"] == report["paired_control"] == dict.fromkeys(ids, {})


@pytest.mark.parametrize("stage", ["prepare", "score", "replay"])
@pytest.mark.parametrize("change", ["add", "delete", "alter"])
def test_parent_tampering_rejected_before_output_changes(inputs, stage, change):
    root, _, _ = inputs
    runner.run(root, "prepare")
    before = runner.snapshot(root / runner.DIRECTORY)
    target = root / runner.PREDECESSOR / ".writer.lock"
    if change == "delete":
        target.unlink()
    elif change == "add":
        (target.parent / "extra").write_text("new")
    else:
        target.write_text("changed")
    with pytest.raises(ValueError, match="predecessor linkage"):
        runner.run(root, stage)
    assert runner.snapshot(root / runner.DIRECTORY) == before


@pytest.mark.parametrize("bad", ["../bad", "/tmp/bad", "a/b", "", "."])
def test_bad_run_ids_do_not_create_output(inputs, bad):
    root, _, _ = inputs
    before = set(root.iterdir())
    with pytest.raises(ValueError):
        runner.run(root, "prepare", run_id=bad)
    assert set(root.iterdir()) == before


def test_same_parent_or_symlink_rejected(inputs):
    root, _, _ = inputs
    with pytest.raises(ValueError, match="different"):
        runner.run(root, "prepare", run_id=runner.PREDECESSOR)
    (root / runner.DIRECTORY).symlink_to(root / runner.PREDECESSOR)
    with pytest.raises(ValueError):
        runner.run(root, "prepare")


def test_unknown_model_outcome_consumes_slot_and_keeps_denominator(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    deployment(root, cfg)
    calls = fake_live(monkeypatch, cfg)
    directory = root / runner.DIRECTORY
    retained(
        directory,
        ids[0],
        "grounded_lookup",
        read_json(directory / "lookup-requests.json")[ids[0]],
        cfg,
    )
    for _ in range(2):
        with pytest.raises(ValueError, match="Unknown outcome consumes"):
            runner.run(root, "score")
    assert calls["model"] == [] and calls["pages"] == 0
    receipt = read_json(directory / f"{ids[0]}-grounded_lookup-incomplete.json")
    assert receipt["selected_denominator"] == 10 and receipt["validated_judgments"] == 0
    assert not (directory / "report.json").exists()


def test_invalid_attribution_is_retained_and_never_retried(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    deployment(root, cfg)
    invalid = response()
    invalid["safety"]["candidate_ids"] = ["steps[0]"]
    calls = fake_live(monkeypatch, cfg, invalid)
    for _ in range(2):
        with pytest.raises(ValueError, match="safety_info"):
            runner.run(root, "score")
    assert len(calls["model"]) == 2 and calls["pages"] == 1
    directory = root / runner.DIRECTORY
    assert (directory / "grounded_judgment" / ids[0] / "return.json").exists()
    assert not (directory / "report.json").exists()


def test_interrupted_page_fetch_consumes_all_requested_pages(inputs, monkeypatch):
    root, cfg, _ = inputs
    runner.run(root, "prepare")
    deployment(root, cfg)
    calls = fake_live(monkeypatch, cfg)

    def fail(*args):
        raise ValueError("Synthetic interrupted page fetch")

    monkeypatch.setattr(runner, "open_page", fail)
    with pytest.raises(ValueError, match="interrupted page"):
        runner.run(root, "score")
    with pytest.raises(ValueError, match="Unknown documentation|Frozen"):
        runner.run(root, "score")
    assert len(calls["model"]) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"protocol_sha256": "0" * 64},
        {"maximum_server_lifetime_seconds": 14401},
        {"verified_at": "2099-01-01T00:00:00+00:00"},
        {"launched_at": "2000-01-01T00:00:00+00:00"},
        {"launched_at": "2026-01-01T00:00:00"},
    ],
)
def test_unverified_or_expired_deployment_prevents_dispatch(inputs, changes):
    root, cfg, _ = inputs
    runner.run(root, "prepare")
    deployment(root, cfg, **changes)
    with pytest.raises(ValueError):
        runner.run(root, "score")


@pytest.mark.parametrize(
    "field,value",
    [
        ("cases", []),
        ("judge", {}),
        ("reference", "0" * 64),
        ("control_report", "0" * 64),
        ("max_model_starts", 21),
        ("max_page_requests", 31),
    ],
)
def test_changed_parent_comparison_inputs_block_preparation(inputs, field, value):
    root, _, _ = inputs
    path = root / runner.PREDECESSOR / "protocol.json"
    path.write_text(json.dumps(read_json(path) | {field: value}))
    with pytest.raises(ValueError, match="comparison inputs differ"):
        runner.run(root, "prepare")
    assert not (root / runner.DIRECTORY).exists()


def test_malformed_raw_response_remains_consumed_without_default_scores(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    deployment(root, cfg)
    calls = fake_live(monkeypatch, cfg, {"malformed": "Synthetic invalid schema"})
    for _ in range(2):
        with pytest.raises(ValueError, match="response checks"):
            runner.run(root, "score")
    assert len(calls["model"]) == 2 and calls["pages"] == 1
    directory = root / runner.DIRECTORY
    raw = read_json(directory / "grounded_judgment" / ids[0] / "return.json")
    assert raw["parsed"] is None and raw["error_type"] == "ValidationError"
    assert not (directory / "report.json").exists()


def test_oversize_schema_bearing_request_stops_before_durable_start(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    deployment(root, cfg)
    calls = fake_live(monkeypatch, cfg)
    base = runner.LocalServer

    class Oversize(base):
        def token_fit(self, wire, context, reserve):
            assert context == 16384 and wire["max_tokens"] == 8192 and reserve == 1200
            assert "Lookup" in str(wire)
            return {"fits": False, "required_tokens": 17000, "wire_sha256": digest(wire)}

    monkeypatch.setattr(runner, "LocalServer", Oversize)
    with pytest.raises(ValueError, match="exceeds context"):
        runner.run(root, "score")
    directory = root / runner.DIRECTORY
    assert not (directory / "grounded_lookup" / ids[0] / "start.json").exists()
    assert read_json(directory / f"{ids[0]}-grounded_lookup-fit.json")["fits"] is False
    assert calls["model"] == [] and calls["pages"] == 0
