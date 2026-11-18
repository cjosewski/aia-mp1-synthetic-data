"""Synthetic audit binding; no real item receives an accepting audit."""

from copy import deepcopy

import pytest
from test_compact_evidence import envelope
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_scoring import scoring as scoring

from aia_mp1.recovery_audit_bridge import accept_fact_audit, case_binding
from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.tracing import digest


def prepared(tmp_path, args, raw=None, stale=False):
    plan, content, rubric, _, observations, _ = args
    binding = case_binding(plan, content, rubric)
    cases = [f"synthetic-{i}" for i in range(10)]
    ledger = RecoveryLedger.create(
        tmp_path / "journal", cases, {"case_bindings": {cases[0]: binding}}
    )
    payload = {
        "case_binding": {**binding, "input_sha256": "a" * 64} if stale else binding,
        "request": {"synthetic": True},
    }
    start = {
        "kind": "start",
        "item_id": cases[0],
        "stage": "facts",
        "request_sha256": digest(payload),
    }
    ledger.append(start, payload)
    raw = raw if raw is not None else envelope(observations.model_dump(mode="json"))
    ledger.append(
        {
            "kind": "finish",
            "start_sha256": digest(start),
            "completion_sha256": digest(raw),
            "structurally_valid": True,
        },
        raw,
    )
    return ledger


def test_actual_saved_observations_and_audit_unlock_score(scoring, tmp_path):
    args, _, _ = scoring
    ledger = prepared(tmp_path, args)
    result = accept_fact_audit(ledger, *args[:4], args[5])
    assert result["state"]["next_request"]["stage"] == "score"
    assert not result["execution_enabled"]


@pytest.mark.parametrize("attack", ["case", "start", "raw", "audit", "source"])
def test_stale_or_unverified_artifacts_do_not_append_acceptance(scoring, tmp_path, attack):
    args, _, _ = scoring
    args = deepcopy(args)
    raw = {"choices": []} if attack == "raw" else None
    ledger = prepared(tmp_path, args, raw, stale=attack == "start")
    if attack == "case":
        args[1]["untrusted_item"]["answer"] += " changed"
    if attack == "audit":
        args[5].checks[0].accepted = False
    if attack == "source":
        args[5].sources_applicable_and_permitted = False
    before = (ledger.directory / "events.jsonl").read_bytes()
    with pytest.raises(ValueError):
        accept_fact_audit(ledger, *args[:4], args[5])
    assert (ledger.directory / "events.jsonl").read_bytes() == before
    assert ledger.read()[2]["awaiting_audit"]
