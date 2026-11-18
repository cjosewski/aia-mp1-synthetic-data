"""Synthetic source-ID preflight; every HTTP request is intercepted."""

import json

import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_evidence import evidence as evidence
from test_recovery_packet import prepared as prepared
from test_recovery_preflight import server
from test_recovery_source_requests import journal
from test_recovery_source_requests import source_packet as source_packet

from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.recovery_source_preflight import preflight_source_next, preflight_source_owned


def setup(tmp_path, source_packet):
    original = journal(tmp_path, source_packet)
    manifest = original.read()[0]
    model = manifest["experiment"]["transport_policy"]["model"]
    props = {
        "build_info": "synthetic-build",
        "chat_template": "synthetic-template",
        "total_slots": 1,
        "model_path": model,
        "default_generation_settings": {"n_ctx": 8192},
    }
    ledger = RecoveryLedger.create(
        tmp_path / "source-preflight-journal",
        manifest["case_ids"],
        {**manifest["experiment"], "server_properties": props},
    )
    return ledger, props


@pytest.mark.parametrize("tokens,fits", [(20, True), (8000, False)])
def test_source_wire_fit_does_not_start_inference(tmp_path, source_packet, tokens, fits):
    ledger, props = setup(tmp_path, source_packet)
    transport, calls = server(props, tokens=tokens)
    result = preflight_source_next(ledger, source_packet, "synthetic-key", transport=transport)
    assert result["token_fit"]["fits"] is fits
    assert result["token_fit"]["required_tokens"] == tokens + 512
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
    assert ledger.read()[2]["starts"] == 0


def test_packet_tamper_blocks_before_http(tmp_path, source_packet):
    ledger, props = setup(tmp_path, source_packet)
    review_path = source_packet / "synthetic-0/preparation-review.json"
    review = json.loads(review_path.read_text())
    review["entries"][0]["reason"] = "Changed preparation"
    review_path.write_text(json.dumps(review))
    transport, calls = server(props)
    with pytest.raises(ValueError, match="frozen"):
        preflight_source_next(ledger, source_packet, "synthetic-key", transport=transport)
    assert calls == [] and ledger.read()[2]["starts"] == 0


def test_owner_bracketing_fails_closed_on_process_change(tmp_path, source_packet, monkeypatch):
    ledger, props = setup(tmp_path, source_packet)
    transport, _ = server(props)
    # Use a fresh journal with a synthetic owner field; the existing manifest is immutable.
    manifest = ledger.read()[0]
    experiment = {**manifest["experiment"], "owned_process": {"synthetic": True}}
    owned = RecoveryLedger.create(tmp_path / "owned-journal", manifest["case_ids"], experiment)
    observations = iter([{"pid": 1}, {"pid": 2}])
    monkeypatch.setattr(
        "aia_mp1.recovery_source_preflight.observe_process", lambda *a: next(observations)
    )
    monkeypatch.setattr("aia_mp1.recovery_source_preflight.observe_tunnel", lambda *a: {"pid": 3})
    monkeypatch.setattr("aia_mp1.recovery_source_preflight.observe_files", lambda *a: [])
    with pytest.raises(ValueError, match="changed across preflight"):
        preflight_source_owned(
            owned,
            source_packet,
            "synthetic-key",
            lambda *a, **k: "",
            lambda *a: {},
            transport=transport,
        )
    assert owned.read()[2]["starts"] == 0
