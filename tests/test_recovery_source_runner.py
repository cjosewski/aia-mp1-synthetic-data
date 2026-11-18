"""Synthetic bounded source-ID runner; no Mac or model is touched."""

import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_evidence import evidence as evidence
from test_recovery_packet import prepared as prepared
from test_recovery_source_requests import journal
from test_recovery_source_requests import source_packet as source_packet

from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.recovery_source_requests import prepare_source_next
from aia_mp1.recovery_source_runner import run_source_next


def setup(tmp_path, source_packet):
    original = journal(tmp_path, source_packet)
    manifest = original.read()[0]
    experiment = {
        **manifest["experiment"],
        "development_allocation": {
            "protocol": "m4-source-development-v1",
            "max_starts": 20,
            "decision_ref": "synthetic-only-decision",
        },
    }
    return RecoveryLedger.create(tmp_path / "run-journal", manifest["case_ids"], experiment)


@pytest.mark.parametrize("fits", [True, False])
def test_source_preflight_receipt_and_fit_gate(tmp_path, source_packet, monkeypatch, fits):
    ledger = setup(tmp_path, source_packet)
    calls = []

    def preflight(*args, **kwargs):
        calls.append("preflight")
        return {
            "prepared": prepare_source_next(ledger, source_packet),
            "token_fit": {"fits": fits},
            "observed_at": f"synthetic-{len(calls)}",
        }

    monkeypatch.setattr("aia_mp1.recovery_source_runner.preflight_source_owned", preflight)
    monkeypatch.setattr(
        "aia_mp1.recovery_source_runner.dispatch_source_next",
        lambda *a, **kw: pytest.fail("no dispatch permitted"),
    )
    first = run_source_next(ledger, source_packet, "synthetic-key", None, None)
    assert first["outcome"] == ("preflight_only" if fits else "token_fit_failed")
    assert ledger.read()[2]["starts"] == 0
    assert (ledger.directory / first["receipt"].split("/")[-1]).exists()
    second = run_source_next(ledger, source_packet, "synthetic-key", None, None)
    assert second["receipt"] != first["receipt"]
    assert calls == ["preflight", "preflight"]


def test_source_dispatch_only_after_fresh_fitting_receipt(tmp_path, source_packet, monkeypatch):
    ledger = setup(tmp_path, source_packet)
    monkeypatch.setattr(
        "aia_mp1.recovery_source_runner.preflight_source_owned",
        lambda *a, **kw: {
            "prepared": prepare_source_next(ledger, source_packet),
            "token_fit": {"fits": True},
            "observed_at": "synthetic-time",
        },
    )

    def dispatch(*args, **kwargs):
        assert len(list(ledger.directory.glob("source-preflight-*.json"))) == 1
        assert args[1:3] == ("synthetic-0", "facts")
        return {"outcome": "synthetic_response_retained", "calibration_eligible": False}

    monkeypatch.setattr("aia_mp1.recovery_source_runner.dispatch_source_next", dispatch)
    result = run_source_next(ledger, source_packet, "synthetic-key", None, None, execute=True)
    assert result["outcome"] == "synthetic_response_retained"
    assert ledger.read()[2]["starts"] == 0


def test_missing_allocation_blocks_before_preflight(tmp_path, source_packet, monkeypatch):
    ledger = journal(tmp_path, source_packet)
    monkeypatch.setattr(
        "aia_mp1.recovery_source_runner.preflight_source_owned",
        lambda *a, **kw: pytest.fail("preflight should not run"),
    )
    with pytest.raises(ValueError, match="allocation"):
        run_source_next(ledger, source_packet, "synthetic-key", None, None, execute=True)


def test_changed_source_implementation_blocks_before_preflight(
    tmp_path, source_packet, monkeypatch
):
    original = setup(tmp_path, source_packet)
    manifest = original.read()[0]
    experiment = {**manifest["experiment"], "source_contract_sha256": "0" * 64}
    ledger = RecoveryLedger.create(
        tmp_path / "wrong-code-journal", manifest["case_ids"], experiment
    )
    monkeypatch.setattr(
        "aia_mp1.recovery_source_runner.preflight_source_owned",
        lambda *a, **kw: pytest.fail("preflight should not run"),
    )
    with pytest.raises(ValueError, match="implementation differs"):
        run_source_next(ledger, source_packet, "synthetic-key", None, None, execute=True)
    assert ledger.read()[2]["starts"] == 0
