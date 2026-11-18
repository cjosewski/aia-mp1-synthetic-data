"""Synthetic durable scheduling; audit payloads here never concern real items."""

import json

import pytest

from aia_mp1.assessment import exclusive
from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.tracing import digest

CASES = [f"synthetic-{i}" for i in range(10)]


@pytest.fixture
def ledger(tmp_path):
    return RecoveryLedger.create(tmp_path / "journal", CASES, {"synthetic": True})


def begin(ledger):
    payload = {"messages": ["synthetic request"]}
    record = {
        "kind": "start",
        "item_id": CASES[0],
        "stage": "facts",
        "request_sha256": digest(payload),
    }
    ledger.append(record, payload)
    return record, payload


def test_reopen_preserves_unknown_start_and_prevents_retry(ledger):
    record, payload = begin(ledger)
    reopened = RecoveryLedger(ledger.directory)
    assert reopened.read()[2]["unknown_outcome"]
    with pytest.raises(ValueError):
        reopened.append(record, payload)
    assert reopened.read()[2]["starts"] == 1


def test_raw_completion_and_audit_retained(ledger):
    s, _ = begin(ledger)
    raw = {"raw_response": "synthetic completion"}
    f = {
        "kind": "finish",
        "start_sha256": digest(s),
        "completion_sha256": digest(raw),
        "structurally_valid": True,
    }
    ledger.append(f, raw)
    assert ledger.read()[2]["awaiting_audit"]
    receipt = {"synthetic_audit": "accepted"}
    ledger.append(
        {
            "kind": "audit",
            "finish_sha256": digest(f),
            "audit_sha256": digest(receipt),
            "accepted": True,
        },
        receipt,
    )
    assert ledger.read()[2]["next_request"]["stage"] == "score"
    rows = [
        json.loads(line) for line in (ledger.directory / "events.jsonl").read_text().splitlines()
    ]
    assert rows[1]["payload"] == raw and rows[2]["payload"] == receipt


def test_interrupted_head_write_requires_inspection(ledger, monkeypatch):
    def interrupted(*args):
        raise OSError("synthetic interruption")

    monkeypatch.setattr("aia_mp1.recovery_ledger.write_checkpoint", interrupted)
    with pytest.raises(OSError):
        begin(ledger)
    with pytest.raises(ValueError, match="event/head"):
        ledger.read()


def test_changed_payload_and_partial_tail_fail(ledger):
    begin(ledger)
    path = ledger.directory / "events.jsonl"
    original = path.read_text()
    path.write_text(original.replace("synthetic request", "changed request"))
    with pytest.raises(ValueError, match="chain"):
        ledger.read()
    path.write_text(original.rstrip("\n"))
    with pytest.raises(ValueError, match="incomplete"):
        ledger.read()


def test_payload_mismatch_does_not_write(ledger):
    with pytest.raises(ValueError, match="payload"):
        ledger.append({"kind": "start", "request_sha256": "a" * 64}, {"different": True})
    assert not (ledger.directory / "events.jsonl").exists()


def test_single_writer_and_existing_directory_fail(ledger):
    with exclusive(ledger.directory):
        with pytest.raises(FileExistsError):
            begin(ledger)
    with pytest.raises(FileExistsError):
        RecoveryLedger.create(ledger.directory, CASES, {"synthetic": True})


def test_symlink_event_file_rejected(ledger, tmp_path):
    target = tmp_path / "other.jsonl"
    target.write_text("")
    (ledger.directory / "events.jsonl").symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        ledger.read()
