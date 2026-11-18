"""Synthetic bounded runner tests; no model, tunnel or review is used."""

import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_evidence import evidence as evidence
from test_recovery_packet import prepared as prepared
from test_recovery_requests import journal
from test_recovery_wire import request_data as request_data

from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.recovery_requests import prepare_next
from aia_mp1.recovery_runner import run_next


def setup(tmp_path, prepared, request_data):
    original = journal(tmp_path, prepared, request_data)
    manifest = original.read()[0]
    experiment = {
        **manifest["experiment"],
        "development_allocation": {
            "protocol": "m4-recovery-development-v1",
            "max_starts": 20,
            "decision_ref": "synthetic-only-decision",
        },
    }
    return RecoveryLedger.create(tmp_path / "run-journal", manifest["case_ids"], experiment)


@pytest.mark.parametrize("fits", [True, False])
def test_preflight_receipt_and_fit_gate(tmp_path, prepared, request_data, monkeypatch, fits):
    ledger = setup(tmp_path, prepared, request_data)
    calls = []

    def preflight(*args, **kwargs):
        calls.append("preflight")
        return {"prepared": prepare_next(ledger, prepared), "token_fit": {"fits": fits}}

    monkeypatch.setattr("aia_mp1.recovery_runner.preflight_with_tunnel", preflight)
    monkeypatch.setattr(
        "aia_mp1.recovery_runner.dispatch_next",
        lambda *a, **kw: pytest.fail("no dispatch permitted"),
    )
    result = run_next(ledger, prepared, "synthetic-key", None, None)
    assert result["outcome"] == ("preflight_only" if fits else "token_fit_failed")
    assert calls == ["preflight"] and ledger.read()[2]["starts"] == 0
    assert (ledger.directory / result["receipt"].split("/")[-1]).exists()
    with pytest.raises(FileExistsError):
        run_next(ledger, prepared, "synthetic-key", None, None)


def test_dispatch_only_after_fitting_receipt(tmp_path, prepared, request_data, monkeypatch):
    ledger = setup(tmp_path, prepared, request_data)
    monkeypatch.setattr(
        "aia_mp1.recovery_runner.preflight_with_tunnel",
        lambda *a, **kw: {"prepared": prepare_next(ledger, prepared), "token_fit": {"fits": True}},
    )

    def dispatch(*args, **kwargs):
        assert len(list(ledger.directory.glob("preflight-*.json"))) == 1
        assert args[1:3] == ("synthetic-0", "facts")
        return {"outcome": "synthetic_response_retained", "calibration_eligible": False}

    monkeypatch.setattr("aia_mp1.recovery_runner.dispatch_next", dispatch)
    result = run_next(ledger, prepared, "synthetic-key", None, None, execute=True)
    assert result["outcome"] == "synthetic_response_retained"
    assert ledger.read()[2]["starts"] == 0  # Mock dispatch cannot claim a real start.


def test_missing_allocation_blocks_before_preflight(tmp_path, prepared, request_data, monkeypatch):
    ledger = journal(tmp_path, prepared, request_data)
    monkeypatch.setattr(
        "aia_mp1.recovery_runner.preflight_with_tunnel",
        lambda *a, **kw: pytest.fail("preflight should not run"),
    )
    with pytest.raises(ValueError, match="allocation"):
        run_next(ledger, prepared, "synthetic-key", None, None, execute=True)
