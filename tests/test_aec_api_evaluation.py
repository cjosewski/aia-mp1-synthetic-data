"""A lost response consumes an attempt and cannot become a matching decision."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from aia_mp1.assessment import save_new
from aia_mp1.tracing import append_record, artifact_hashes

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from run_aec_api_evaluation import record, replay  # noqa: E402


def test_replay_preserves_unknown_outcome_after_valid_retry(tmp_path):
    ledger = tmp_path / "attempts.jsonl"
    ledger.touch()
    manifest = {"artifacts_sha256": artifact_hashes(tmp_path)}
    save_new(tmp_path / "manifest.json", manifest)
    item = {"item_id": "synthetic-item", "messages_sha256": "synthetic-wire"}
    config = SimpleNamespace(max_attempts=2, model="synthetic-judge")
    first = item | {"kind": "start", "attempt_id": "synthetic-item:1"}
    second = first | {"attempt_id": "synthetic-item:2"}
    record(tmp_path, manifest, first)
    record(tmp_path, manifest, second)
    scores = {f"D{i}": {"decision": 0, "justification": "synthetic"} for i in range(1, 7)}
    record(
        tmp_path,
        manifest,
        second
        | {
            "kind": "result",
            "valid": True,
            "response_model": config.model,
            "judgment": scores,
        },
    )
    counts, decisions, unknown = replay(tmp_path, [item], config)
    assert counts == {"synthetic-item": 2}
    assert decisions == {"synthetic-item": scores}
    assert unknown == ["synthetic-item:1"]
    with pytest.raises(ValueError, match="Unexpected judge input"):
        replay(tmp_path, [item | {"messages_sha256": "different-wire"}], config)
    append_record(ledger, first)
    with pytest.raises(ValueError, match="checkpoint"):
        replay(tmp_path, [item], config)
