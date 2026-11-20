"""Synthetic compact display and stopped-parent lineage; no live evidence or inference."""

import json
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import screen_aec_compact_docs as runner
import screen_aec_grounded_docs as grounded
from test_aec_grounded_judgment import case, response
from test_aec_grounded_runs import fake_live, retained
from test_aec_grounded_runs import inputs as base_inputs  # noqa: F401

from aia_mp1.assessment import read_json, save_new


def page(request=None):
    return {
        "request": request
        or {"page": "synthetic", "anchors": ["α", "absent"], "claim": "Keep exact text"},
        "url": "https://example.invalid/version",
        "edition": "Synthetic edition",
        "opened_at": "synthetic",
        "body_sha256": "a" * 64,
        "http_status": 200,
        "normalized_text_sha256": "b" * 64,
        "normalized_text_chars": 77,
        "search_strategy": "literal-first-match",
        "evidence_status": "partial",
        "search_results": [
            {
                "anchor": "α",
                "matched": True,
                "match_start": 4,
                "match_end": 5,
                "occurrence_count": 2,
                "excerpt_ids": ["E1"],
            },
            {
                "anchor": "absent",
                "matched": False,
                "match_start": None,
                "match_end": None,
                "occurrence_count": 0,
                "excerpt_ids": [],
            },
        ],
        "excerpts": [
            {
                "id": "E1",
                "start": 0,
                "end": 30,
                "anchors": ["α"],
                "text": '  α "quoted"\nA bounded operation.  ',
            }
        ],
    }


def test_projection_preserves_text_search_outcomes_order_and_input_object():
    pages = [page(), page()]
    before = deepcopy(pages)
    shown = runner.project_pages(pages)
    assert pages == before
    assert [value["id"] for value in shown] == ["P1", "P2"]
    for original, projected in zip(pages, shown, strict=True):
        expected = {
            key: value
            for key, value in original.items()
            if key
            not in {"opened_at", "body_sha256", "normalized_text_sha256", "normalized_text_chars"}
        }
        expected["search_results"] = [
            {key: value for key, value in row.items() if key not in {"match_start", "match_end"}}
            for row in original["search_results"]
        ]
        expected["excerpts"] = [{"id": "E1", "text": original["excerpts"][0]["text"]}]
        assert {key: value for key, value in projected.items() if key != "id"} == expected


@pytest.mark.parametrize("status", ["unresolved", "error"])
def test_misses_and_errors_never_gain_substitute_evidence(status):
    raw = page() | {"evidence_status": status, "excerpts": []}
    if status == "error":
        raw["search_results"] = []
        raw["error"] = "Synthetic timeout"
    compact = runner.project_pages([raw])[0]
    assert compact["excerpts"] == [] and compact["evidence_status"] == status
    assert raw["excerpts"] == []
    if status == "error":
        assert compact["error"] == "Synthetic timeout" and compact["search_results"] == []


def test_minification_is_lossless_and_preserves_original_system_and_unicode():
    original = runner.wire("Original six anchors", case())
    compact = runner.build_judgment_messages(original, [page()])
    metadata_only = runner.build_judgment_messages(original, [page()], compact_json=False)
    assert (
        compact[0]
        == metadata_only[0]
        == {"role": "system", "content": "Original six anchors\n\n" + grounded.FINAL}
    )
    assert json.loads(compact[1]["content"]) == json.loads(metadata_only[1]["content"])
    assert len(compact[1]["content"]) < len(metadata_only[1]["content"])
    assert (
        json.loads(compact[1]["content"])["online_documentation"][0]["excerpts"][0]["text"]
        == page()["excerpts"][0]["text"]
    )
    assert "α" in compact[1]["content"]
    assert runner.SELECT == grounded.SELECT and runner.FINAL == grounded.FINAL


@pytest.fixture
def inputs(request, monkeypatch):
    root, cfg, ids = request.getfixturevalue("base_inputs")
    grounded.run(root, "prepare")
    # Preserve a stopped parent with a valid lookup and pages, but no judgment/report.
    prior = root / grounded.DIRECTORY
    messages = read_json(prior / "lookup-requests.json")[ids[0]]
    menu = json.loads(messages[1]["content"])["pages"]
    lookup = grounded.Lookup.model_validate(
        {"pages": [{"page": next(iter(menu)), "anchors": ["α"], "claim": "Synthetic"}]}
    )
    retained(prior, ids[0], "grounded_lookup", messages, cfg, lookup.model_dump())
    category = json.loads(messages[1]["content"])["case"]["untrusted_reference_context"]["task"][
        "category"
    ]
    identity = {
        "lookup": lookup.model_dump(),
        "category": category,
        "protocol": runner.file_hash(prior / "protocol.json"),
    }
    save_new(prior / f"{ids[0]}-pages-start.json", identity)
    body = {"identity": identity, "pages": [page(lookup.pages[0].model_dump())]}
    save_new(prior / f"{ids[0]}-pages.json", body | {"sha256": runner.digest(body)})
    (prior / ".writer.lock").write_text("Synthetic preserved stop")
    for name in ("load_assessment", "freeze_development_labels", "LocalServer"):
        monkeypatch.setattr(runner, name, getattr(grounded, name))
    return root, cfg, ids


def runtime_receipt(root, cfg, *, outside=False):
    now = datetime.now(timezone.utc)
    target = (
        root / "synthetic-runtime.json" if outside else root / runner.DIRECTORY / "deployment.json"
    )
    save_new(
        target,
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
    return target


def fake_compact_live(monkeypatch, cfg, output=None):
    calls = fake_live(monkeypatch, cfg, output)
    monkeypatch.setattr(runner, "LocalServer", grounded.LocalServer)

    def open_page(category, request):
        calls["pages"] += 1
        return page(request.model_dump())

    monkeypatch.setattr(grounded, "open_page", open_page)
    return calls


def test_prepare_pins_stopped_parent_and_complete_baseline_without_copying_attempt(inputs):
    root, _, _ = inputs
    old = runner.snapshot(root / runner.PREDECESSOR)
    baseline = runner.snapshot(root / grounded.PREDECESSOR)
    for _ in range(2):
        assert runner.run(root, "prepare") == {"prepared": 10}
    directory = root / runner.DIRECTORY
    assert set(runner.snapshot(directory)) == {
        "protocol.json",
        "lookup-requests.json",
        "review-checkpoint.json",
    }
    protocol = read_json(directory / "protocol.json")
    assert protocol["predecessor"] == {"run_id": runner.PREDECESSOR, "files_sha256": old}
    assert protocol["completed_baseline"] == {
        "run_id": grounded.PREDECESSOR,
        "files_sha256": baseline,
    }
    assert protocol["judgment_json_separators"] == [",", ":"]
    assert protocol["max_model_starts"] == 20 and protocol["max_page_requests"] == 30
    assert len(protocol["source"]) == 19
    assert runner.snapshot(root / runner.PREDECESSOR) == old
    assert not (root / runner.PREDECESSOR / "report.json").exists()


@pytest.mark.parametrize("where", ["stopped", "complete"])
def test_changed_parent_or_completed_baseline_stops_without_output_mutation(inputs, where):
    root, _, _ = inputs
    runner.run(root, "prepare")
    before = runner.snapshot(root / runner.DIRECTORY)
    target = runner.PREDECESSOR if where == "stopped" else grounded.PREDECESSOR
    (root / target / "unexpected").write_text("Synthetic tamper")
    with pytest.raises(ValueError, match="predecessor linkage|baseline differs"):
        runner.run(root, "prepare")
    assert runner.snapshot(root / runner.DIRECTORY) == before


def test_readonly_preflight_tokenizes_eleven_requests_without_attempts_or_page_calls(
    inputs, monkeypatch
):
    root, cfg, _ = inputs
    runner.run(root, "prepare")
    receipt = runtime_receipt(root, cfg, outside=True)
    before = runner.snapshot(root / runner.DIRECTORY)
    parent_before = runner.snapshot(root / runner.PREDECESSOR)
    calls = fake_compact_live(monkeypatch, cfg)
    report = runner.run(root, "preflight", preflight_receipt=receipt)
    assert report["inference_requests"] == 0 and report["measured_requests_fit"]
    assert len(report["lookup_fits"]) == 10 and len(calls["fits"]) == 11
    assert calls["model"] == [] and calls["pages"] == 0
    assert runner.snapshot(root / runner.DIRECTORY) == before
    assert runner.snapshot(root / runner.PREDECESSOR) == parent_before
    assert "other judgment inputs remain unmeasured" in report["scope"]


def test_fresh_compact_score_and_replay_never_count_parent_lookup_as_new_attempt(
    inputs, monkeypatch
):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime_receipt(root, cfg)
    calls = fake_compact_live(monkeypatch, cfg)
    result = runner.run(root, "score")
    assert len(calls["model"]) == 20 and calls["pages"] == 10
    assert runner.run(root, "replay") == result
    assert len(calls["model"]) == 20 and calls["pages"] == 10
    report = read_json(root / runner.DIRECTORY / "report.json")
    assert report["paired_previous"] == report["paired_control"] == dict.fromkeys(ids, {})


def test_invalid_grounding_return_stays_consumed(inputs, monkeypatch):
    root, cfg, _ = inputs
    runner.run(root, "prepare")
    runtime_receipt(root, cfg)
    invalid = response()
    invalid["safety"]["candidate_ids"] = ["steps[0]"]
    calls = fake_compact_live(monkeypatch, cfg, invalid)
    for _ in range(2):
        with pytest.raises(ValueError, match="safety_info"):
            runner.run(root, "score")
    assert len(calls["model"]) == 2 and calls["pages"] == 1
    assert not (root / runner.DIRECTORY / "report.json").exists()


def test_unknown_new_lookup_is_not_replaced_by_parent_lookup(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime_receipt(root, cfg)
    target = root / runner.DIRECTORY
    retained(
        target, ids[0], "grounded_lookup", read_json(target / "lookup-requests.json")[ids[0]], cfg
    )
    calls = fake_compact_live(monkeypatch, cfg)
    with pytest.raises(ValueError, match="Unknown outcome consumes"):
        runner.run(root, "score")
    assert calls["model"] == [] and calls["pages"] == 0


def test_oversize_compact_request_still_stops_before_model_start(inputs, monkeypatch):
    root, cfg, ids = inputs
    runner.run(root, "prepare")
    runtime_receipt(root, cfg)
    calls = fake_compact_live(monkeypatch, cfg)
    base = runner.LocalServer

    class Oversize(base):
        def token_fit(self, wire, context, reserve):
            assert context == 16384 and reserve == 1200 and wire["max_tokens"] == 8192
            return {"fits": False}

    monkeypatch.setattr(runner, "LocalServer", Oversize)
    with pytest.raises(ValueError, match="exceeds context"):
        runner.run(root, "score")
    assert calls["model"] == [] and calls["pages"] == 0
    assert not (root / runner.DIRECTORY / "grounded_lookup" / ids[0] / "start.json").exists()


def test_failed_preflight_uses_only_readonly_tokenizer_routes_and_changes_no_evidence(
    inputs, monkeypatch
):
    import httpx

    from aia_mp1.factcheck_transport import LocalServer

    root, cfg, _ = inputs
    runner.run(root, "prepare")
    receipt = runtime_receipt(root, cfg, outside=True)
    before = runner.snapshot(root)
    routes = []

    def transport(request):
        routes.append(request.url.path)
        if request.url.path == "/props":
            body = {
                "model_path": cfg.model,
                "build_info": "synthetic",
                "total_slots": 1,
                "default_generation_settings": {"n_ctx": 16384},
            }
        elif request.url.path == "/apply-template":
            wire = json.loads(request.content)
            assert wire["max_tokens"] == 8192
            body = {"prompt": "Synthetic schema-bearing tokenizer input"}
        elif request.url.path == "/tokenize":
            body = {"tokens": [1] * 8000}
        else:
            pytest.fail(f"Forbidden preflight route: {request.url.path}")
        return httpx.Response(200, json=body)

    monkeypatch.setattr(
        runner,
        "LocalServer",
        lambda base, key: LocalServer(base, key, transport=httpx.MockTransport(transport)),
    )
    report = runner.run(root, "preflight", preflight_receipt=receipt)
    assert report["measured_requests_fit"] is False
    assert report["diagnostic_judgment"]["fit"]["fits"] is False
    assert report["inference_requests"] == 0
    assert routes.count("/props") == 2
    assert routes.count("/apply-template") == routes.count("/tokenize") == 11
    assert runner.snapshot(root) == before
