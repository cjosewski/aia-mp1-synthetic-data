"""Synthetic audit binding; no real item receives an accepting audit."""

import json
from copy import deepcopy

import pytest
from test_compact_evidence import envelope
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_scoring import scoring as scoring

from aia_mp1.recovery_audit_bridge import (
    accept_fact_audit,
    accept_score_audit,
    case_binding,
    record_completion,
)
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
    record_completion(ledger, digest(start), raw)
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
    if attack == "raw":
        assert ledger.read()[2]["cases"]["synthetic-0"]["facts"] == "failed"
    else:
        assert ledger.read()[2]["awaiting_audit"]


def score_ready(tmp_path, args, scores, stale=False):
    ledger = prepared(tmp_path, args)
    accepted = accept_fact_audit(ledger, *args[:4], args[5])
    payload = {
        "case_binding": case_binding(*args[:3]),
        "scoring_input_sha256": "a" * 64 if stale else digest(accepted["scoring_input"]),
        "request": {"synthetic": True},
    }
    start = {
        "kind": "start",
        "item_id": "synthetic-0",
        "stage": "score",
        "request_sha256": digest(payload),
    }
    ledger.append(start, payload)
    raw = envelope(scores.model_dump(mode="json"))
    record_completion(ledger, digest(start), raw)
    return ledger


def test_saved_score_and_fact_audits_release_next_case(scoring, tmp_path):
    args, scores, audit = scoring
    ledger = score_ready(tmp_path, args, scores)
    result = accept_score_audit(ledger, *args[:4], audit)
    assert result["state"]["next_request"] == {"item_id": "synthetic-1", "stage": "facts"}
    assert result["report"]["status"] == "audited_development"
    assert not result["report"]["calibration_eligible"]


@pytest.mark.parametrize("attack", ["start", "scores", "audit", "source", "unresolved"])
def test_score_acceptance_revalidates_entire_saved_chain(scoring, tmp_path, attack):
    args, scores, audit = deepcopy(scoring)
    if attack == "scores":
        scores.scoring_input_sha256 = "b" * 64
    if attack == "unresolved":
        scores.D1.decision = None
    ledger = score_ready(tmp_path, args, scores, stale=attack == "start")
    if attack == "audit":
        audit.dimensions[0].accepted = False
    if attack == "source":
        # Source permission is revalidated even after the fact audit was accepted.
        (args[3] / "permission.txt").write_text("Changed permission", encoding="utf-8")
    before = (ledger.directory / "events.jsonl").read_bytes()
    with pytest.raises(ValueError):
        accept_score_audit(ledger, *args[:4], audit)
    assert (ledger.directory / "events.jsonl").read_bytes() == before
    assert ledger.read()[2]["awaiting_audit"]["stage"] == "score"


@pytest.mark.parametrize("raw", ["not JSON", {"choices": []}, envelope({"wrong": "schema"})])
def test_invalid_returns_are_retained_and_halt_after_two(tmp_path, raw):
    cases = [f"synthetic-{i}" for i in range(10)]
    ledger = RecoveryLedger.create(tmp_path / "journal", cases, {"synthetic": True})
    for item in cases[:2]:
        payload = {"synthetic": item}
        start = {
            "kind": "start",
            "item_id": item,
            "stage": "facts",
            "request_sha256": digest(payload),
        }
        ledger.append(start, payload)
        before = (ledger.directory / "events.jsonl").read_bytes()
        with pytest.raises(ValueError, match="missing outcome"):
            record_completion(ledger, digest(start), None)
        assert ledger.read()[2]["unknown_outcome"]
        with pytest.raises(ValueError, match="pending"):
            record_completion(ledger, "a" * 64, raw)
        assert (ledger.directory / "events.jsonl").read_bytes() == before
        result = record_completion(ledger, digest(start), raw)
        assert result["schema_error_type"]
        rows = [
            json.loads(line)
            for line in (ledger.directory / "events.jsonl").read_text().splitlines()
        ]
        assert rows[-1]["payload"] == raw
        with pytest.raises(ValueError, match="pending"):
            record_completion(ledger, digest(start), raw)
    assert result["state"]["halt"] == "two_structural_failures"
    assert result["state"]["starts"] == 2
    assert result["state"]["coverage_denominator"] == 10
