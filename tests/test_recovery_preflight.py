"""Synthetic HTTP metadata/tokenization only; no real inference or model files."""

import json
from copy import deepcopy

import httpx
import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_evidence import evidence as evidence
from test_recovery_packet import prepared as prepared
from test_recovery_requests import journal
from test_recovery_wire import request_data as request_data

from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.recovery_preflight import preflight_next


def setup(tmp_path, prepared, request_data):
    original = journal(tmp_path, prepared, request_data)
    manifest = original.read()[0]
    props = {
        "build_info": "synthetic-build",
        "chat_template": "synthetic-template",
        "total_slots": 1,
        "model_path": request_data["model"],
        "default_generation_settings": {"n_ctx": 8192},
    }
    ledger = RecoveryLedger.create(
        tmp_path / "preflight-journal",
        manifest["case_ids"],
        {**manifest["experiment"], "server_properties": props},
    )
    return ledger, props


def server(props, *, tokens=20, drift=None):
    calls = []
    observations = []

    def handle(request):
        path = request.url.path
        calls.append(path)
        if path == "/props":
            observed = deepcopy(props)
            if drift and (drift != "late_template" or observations):
                if drift in {"late_template", "template"}:
                    observed["chat_template"] = "different template"
                elif drift == "context":
                    observed["default_generation_settings"]["n_ctx"] = 16384
                else:
                    observed["build_info"] = "different build"
            observations.append(observed)
            return httpx.Response(200, json=observed)
        if path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": props["model_path"]}]})
        if path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if path == "/apply-template":
            wire = json.loads(request.content)
            assert "Observations" in wire["messages"][0]["content"]
            assert wire["model"] == props["model_path"]
            return httpx.Response(200, json={"prompt": "synthetic rendered prompt"})
        if path == "/tokenize":
            assert json.loads(request.content) == {
                "content": "synthetic rendered prompt",
                "add_special": True,
                "parse_special": True,
            }
            return httpx.Response(200, json={"tokens": list(range(tokens))})
        pytest.fail("unexpected endpoint, including any inference")

    return httpx.MockTransport(handle), calls


@pytest.mark.parametrize("tokens,fits", [(20, True), (5000, False)])
def test_exact_wire_fit_includes_output_and_never_starts(
    tmp_path, prepared, request_data, tokens, fits
):
    ledger, props = setup(tmp_path, prepared, request_data)
    transport, calls = server(props, tokens=tokens)
    result = preflight_next(ledger, prepared, "synthetic-key", transport=transport)
    assert result["token_fit"]["fits"] is fits
    assert result["token_fit"]["required_tokens"] == tokens + request_data["max_tokens"]
    assert result["server_properties"] == props
    assert calls == [
        "/props",
        "/v1/models",
        "/health",
        "/apply-template",
        "/tokenize",
        "/props",
        "/v1/models",
        "/health",
    ]
    assert ledger.read()[2]["starts"] == 0 and not result["execution_enabled"]


@pytest.mark.parametrize("drift", ["template", "context", "build", "late_template"])
def test_runtime_drift_blocks_even_after_tokenization(tmp_path, prepared, request_data, drift):
    ledger, props = setup(tmp_path, prepared, request_data)
    transport, calls = server(props, drift=drift)
    with pytest.raises(ValueError, match="live model or server"):
        preflight_next(ledger, prepared, "synthetic-key", transport=transport)
    assert ("/tokenize" in calls) is (drift == "late_template")
    assert ledger.read()[2]["starts"] == 0


def test_changed_packet_prevents_all_http(tmp_path, prepared, request_data):
    ledger, props = setup(tmp_path, prepared, request_data)
    review_path = prepared / "synthetic-0/preparation-review.json"
    review = json.loads(review_path.read_text())
    review["entries"][0]["reason"] = "changed preparation"
    review_path.write_text(json.dumps(review))
    transport, calls = server(props)
    with pytest.raises(ValueError, match="frozen"):
        preflight_next(ledger, prepared, "synthetic-key", transport=transport)
    assert calls == [] and ledger.read()[2]["starts"] == 0
