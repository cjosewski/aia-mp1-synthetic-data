"""A paired comparison cannot pass on incomplete or altered ledgers."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from report_paired_judges import arm  # noqa: E402


def test_report_rejects_missing_result_and_changed_wire(tmp_path):
    rows = [
        {"item_id": f"synthetic-{i:02d}", "messages_sha256": f"hash-{i:02d}"} for i in range(50)
    ]
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {"protocol": "paired-frontier-v1", "status": "complete", "input_sha256": "bundle"}
        ),
        "utf-8",
    )
    starts = [
        {"item_id": r["item_id"], "messages_sha256": r["messages_sha256"], "index": i}
        for i, r in enumerate(rows)
    ]
    (tmp_path / "starts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in starts), "utf-8")
    (tmp_path / "results.jsonl").write_text(
        "".join(json.dumps(r | {"valid": True, "judgment": {}}) + "\n" for r in starts[:-1]),
        "utf-8",
    )
    with pytest.raises(ValueError, match="incomplete"):
        arm(tmp_path, rows, "bundle", "paired-frontier-v1")
    (tmp_path / "results.jsonl").write_text(
        "".join(json.dumps(r | {"valid": True, "judgment": {}}) + "\n" for r in starts), "utf-8"
    )
    rows[0]["messages_sha256"] = "tampered"
    with pytest.raises(ValueError, match="invalid"):
        arm(tmp_path, rows, "bundle", "paired-frontier-v1")
