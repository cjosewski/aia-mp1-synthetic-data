"""Synthetic local-only transport tests; no real model or human judgments."""

import json
from copy import deepcopy

import httpx
import pytest
from test_factcheck import bundle as bundle
from test_factcheck import completion, facts, judgment, score
from test_factcheck import sample as sample

from aia_mp1.factcheck import validate_input
from aia_mp1.factcheck_stages import Ledger, request_for
from aia_mp1.factcheck_transport import LocalServer, dispatch, loopback_url, wire_request
from aia_mp1.tracing import digest


def test_real_packet_metadata_key_is_preserved(bundle):
    experiment, root = bundle
    content = experiment.cases[0].content
    content["untrusted_reference_context"]["source_pack_sha256"] = "a" * 64
    assert validate_input(content, experiment.rubric, root)
    request = request_for(experiment, experiment.cases[0], "control", None)
    sent = json.loads(request["messages"][1]["content"])
    assert sent["untrusted_reference_context"]["source_pack_sha256"] == "a" * 64
    assert "text" not in sent["passage_catalog"]["C.answer"]
    assert sent["untrusted_item"] == content["untrusted_item"]


def test_compact_wire_preserves_every_passage_and_source_authority(bundle):
    experiment, root = bundle
    case = experiment.cases[0]
    original = deepcopy(case.content)
    for stage in ("control", "facts"):
        request = request_for(experiment, case, stage, None)
        sent = json.loads(request["messages"][1]["content"])
        lookup = {**sent, "rubric": experiment.rubric}
        for identifier, entry in original["passage_catalog"].items():
            value = lookup
            assert sent["passage_index"][identifier] == entry["path"]
            for component in sent["passage_index"][identifier].strip("/").split("/"):
                value = value[int(component)] if isinstance(value, list) else value[component]
            assert value == entry["text"], identifier
            assert sent["passage_catalog"][identifier]["authority"] == entry["authority"]
        for frozen, wire in zip(
            original["primary_excerpts"], sent["primary_excerpts"], strict=True
        ):
            assert "artifact_sha256" not in wire
            assert all(wire[key] == frozen[key] for key in wire)
    assert case.content == original
    assert validate_input(case.content, experiment.rubric, root)


@pytest.mark.parametrize("suffix", ["/unexpected", "/v1?key=test", "/v1#fragment"])
def test_loopback_url_rejects_ambiguous_paths(suffix):
    with pytest.raises(ValueError):
        loopback_url("http://127.0.0.1:8081" + suffix)


@pytest.mark.parametrize(
    "url", ["https://example.com/v1", "http://example.com/v1", "http://user:secret@localhost/v1"]
)
def test_transport_has_no_remote_provider_fallback(url):
    with pytest.raises(ValueError):
        loopback_url(url)


def test_actual_instructor_wire_and_single_dispatch_are_identical(bundle):
    from test_compact_evidence import envelope

    experiment, _ = bundle
    request = request_for(experiment, experiment.cases[0], "control", None)
    original = deepcopy(request)
    wire = wire_request(request, "control")
    assert wire["response_format"] == {"type": "json_object"}
    assert "properties" in wire["messages"][0]["content"]
    calls = []

    def handler(incoming):
        calls.append(json.loads(incoming.content))
        return httpx.Response(200, json=envelope(judgment()))

    response = dispatch(
        request,
        "control",
        wire,
        "http://localhost:8081/v1",
        "synthetic-key",
        httpx.MockTransport(handler),
    )
    assert len(calls) == 1 and calls[0] == wire
    assert response.raw_response["choices"][0]["finish_reason"] == "stop"
    assert response.transport_failure is False and request == original


def test_wire_mismatch_prevents_network_call(bundle):
    experiment, _ = bundle
    request = request_for(experiment, experiment.cases[0], "control", None)
    wire = wire_request(request, "control")
    wire["max_tokens"] = 1
    calls = []

    def handler(incoming):
        calls.append(incoming)
        return httpx.Response(500)

    with pytest.raises(ValueError, match="no verified dispatch"):
        dispatch(
            request,
            "control",
            wire,
            "http://localhost:8081/v1",
            "synthetic-key",
            httpx.MockTransport(handler),
        )
    assert calls == []


def test_timeout_is_one_consumed_transport_failure(bundle):
    experiment, _ = bundle
    request = request_for(experiment, experiment.cases[0], "facts", None)
    wire = wire_request(request, "facts")
    calls = []

    def handler(incoming):
        calls.append(incoming)
        raise httpx.ReadTimeout("Synthetic timeout", request=incoming)

    result = dispatch(
        request,
        "facts",
        wire,
        "http://localhost:8081/v1",
        "synthetic-key",
        httpx.MockTransport(handler),
    )
    assert len(calls) == 1 and result.transport_failure and result.raw_response is None


def test_token_fit_uses_full_chat_template_and_special_tokens():
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append((request.url.path, body))
        return httpx.Response(
            200,
            json={"prompt": "synthetic rendered chat"}
            if request.url.path == "/apply-template"
            else {"tokens": [1] * 10},
        )

    server = LocalServer("http://localhost:8081/v1", "synthetic-key", httpx.MockTransport(handler))
    try:
        wire = {"messages": [{"role": "user", "content": "Synthetic."}], "max_tokens": 5}
        assert server.token_fit(wire, 15)["fits"] is True
        assert server.token_fit(wire, 15, reserve=1)["fits"] is False
        assert seen[0][1] == wire
        assert seen[1][1]["add_special"] is True and seen[1][1]["parse_special"] is True
    finally:
        server.close()


def test_extraction_receipt_binds_original_tool_output_and_permissions(bundle):
    experiment, root = bundle
    original, extractor = b"Synthetic original PDF bytes", b"Synthetic extractor script"
    (root / "original.pdf").write_bytes(original)
    (root / "extract.py").write_bytes(extractor)
    excerpt = experiment.cases[0].content["primary_excerpts"][0]
    receipt = {
        "original_sha256": digest(original.decode()),
        "extractor_sha256": digest(extractor.decode()),
        "output_sha256": excerpt["artifact_sha256"],
        "extractor_version": "synthetic-1",
    }
    (root / "extraction.json").write_text(json.dumps(receipt))
    excerpt["extraction"] = {
        "original_path": "original.pdf",
        "original_sha256": receipt["original_sha256"],
        "extractor_path": "extract.py",
        "extractor_sha256": receipt["extractor_sha256"],
        "receipt_path": "extraction.json",
        "receipt_sha256": digest(json.dumps(receipt)),
    }
    assert validate_input(experiment.cases[0].content, experiment.rubric, root)
    (root / "original.pdf").write_bytes(b"Changed original")
    with pytest.raises(ValueError, match="original/extractor"):
        validate_input(experiment.cases[0].content, experiment.rubric, root)


def test_token_halt_does_not_fabricate_a_request_start(bundle, tmp_path):
    experiment, root = bundle
    ledger = Ledger.create(tmp_path / "run", experiment, root)
    ledger.halt("token_fit")
    _, state = ledger.read()
    assert state["halt"] == "token_fit" and state["starts"] == []
    with pytest.raises(ValueError):
        ledger.begin(experiment.runtime.model_dump(), root)


@pytest.mark.parametrize("overflow", [None, "initial", "actual_score"])
def test_native_runner_preflight_resume_and_actual_memo_guard(
    bundle, tmp_path, monkeypatch, overflow
):
    from aia_mp1 import factcheck_transport as module

    experiment, root = bundle
    ledger = Ledger.create(tmp_path / "run", experiment, root)
    weight = root / "reader.txt"
    stat = weight.stat()
    monkeypatch.setattr(module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(module.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(
        module,
        "verify_weight",
        lambda *args: {
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": "a" * 64,
        },
    )

    class FakeServer:
        def __init__(self, *_):
            pass

        def observe(self, *_):
            return {"model_path": str(weight), **dict.fromkeys(module.PROPERTIES, "synthetic")}

        def token_fit(self, wire, context, reserve=0):
            is_score = "untrusted_fact_memo" in wire["messages"][1]["content"]
            return {
                "wire_sha256": digest(wire),
                "fits": not (overflow == "initial" or overflow == "actual_score" and is_score),
            }

        def close(self):
            pass

    monkeypatch.setattr(module, "LocalServer", FakeServer)
    calls = []

    def fake_dispatch(request, stage, *_):
        calls.append(stage)
        body = json.loads(request["messages"][1]["content"])
        item = next(
            case
            for case in experiment.cases
            if case.content["untrusted_item"] == body["untrusted_item"]
        )
        expected = json.loads(
            request_for(experiment, item, "control", None)["messages"][1]["content"]
        )
        assert {
            key: value for key, value in body.items() if key != "untrusted_fact_memo"
        } == expected
        return completion(
            facts(body) if stage == "facts" else score() if stage == "score" else judgment()
        )

    monkeypatch.setattr(module, "dispatch", fake_dispatch)
    initial = module.run_prepared(ledger, root, {}, "http://localhost:8081/v1", "synthetic")
    assert calls == []
    if overflow == "initial":
        assert initial["stopped"] == "token_fit" and initial["starts"] == 0
    else:
        assert initial["stopped"] == "preflight_only"
        result = module.run_prepared(
            ledger, root, {}, "http://localhost:8081/v1", "synthetic", execute=True
        )
        assert result["starts"] == (2 if overflow == "actual_score" else 15)
        assert result["stopped"] == ("token_fit" if overflow else "complete")
        assert len(calls) == result["starts"]
