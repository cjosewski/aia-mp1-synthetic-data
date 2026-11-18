"""Synthetic schedule receipts, never real audit approvals or model results."""

import pytest

from aia_mp1.recovery_schedule import replay
from aia_mp1.tracing import digest

CASES = [f"synthetic-{i}" for i in range(10)]


def start(item=0, stage="facts"):
    return {"kind": "start", "item_id": CASES[item], "stage": stage, "request_sha256": "a" * 64}


def finish(s, valid=True):
    return {
        "kind": "finish",
        "start_sha256": digest(s),
        "completion_sha256": "b" * 64,
        "structurally_valid": valid,
    }


def audit(f, accepted=True):
    return {
        "kind": "audit",
        "finish_sha256": digest(f),
        "audit_sha256": "c" * 64,
        "accepted": accepted,
    }


def test_unknown_outcome_consumes_start_and_stops():
    state = replay(CASES, [start()])
    assert state["unknown_outcome"] and state["starts"] == 1
    assert state["next_request"] is None
    with pytest.raises(ValueError):
        replay(CASES, [start(), start()])


def test_score_requires_completion_and_audit():
    s = start()
    f = finish(s)
    assert replay(CASES, [s, f])["next_request"] is None
    with pytest.raises(ValueError):
        replay(CASES, [s, f, start(stage="score")])
    state = replay(CASES, [s, f, audit(f)])
    assert state["next_request"] == {"item_id": CASES[0], "stage": "score"}


def test_failure_skips_score_without_donating_retry():
    s = start()
    f = finish(s, False)
    state = replay(CASES, [s, f])
    assert state["cases"][CASES[0]]["score"] == "skipped"
    assert state["next_request"]["item_id"] == CASES[1]
    with pytest.raises(ValueError):
        replay(CASES, [s, f, s])
    other = start(1)
    state = replay(CASES, [s, f, other, finish(other, False)])
    assert state["halt"] == "two_structural_failures"
    assert state["coverage_denominator"] == 10


def test_rejected_audit_stops_all_remaining_cases():
    s = start()
    f = finish(s)
    state = replay(CASES, [s, f, audit(f, False)])
    assert state["halt"] == "semantic_audit_rejected"
    assert state["next_request"] is None


def test_twenty_starts_complete_without_reallocation():
    events = []
    for i in range(10):
        for stage in ("facts", "score"):
            s = start(i, stage)
            f = finish(s)
            events.extend([s, f, audit(f)])
    state = replay(CASES, events)
    assert state["starts"] == 20 and state["next_request"] is None
    assert not state["execution_enabled"]
    with pytest.raises(ValueError):
        replay(CASES, events + [start()])


def test_foreign_completion_and_audit_fail():
    s = start()
    f = finish(start(1))
    with pytest.raises(ValueError):
        replay(CASES, [s, f])
    f = finish(s)
    with pytest.raises(ValueError):
        replay(CASES, [s, f, audit(finish(start(1)))])
