"""Synthetic approval/ownership fixtures; no real attribution or model requests."""

import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "tools/reasoning_budget_probe.py"
SPEC = importlib.util.spec_from_file_location("reasoning_budget_probe", PATH)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def test_missing_or_wrong_plan_approval_blocks_execution(tmp_path):
    plan = {"sha256": "synthetic-plan"}
    with pytest.raises(ValueError, match="approval required"):
        probe.require_approval(tmp_path, plan)
    (tmp_path / "owner-approval.json").write_text(
        json.dumps(
            {
                "plan_sha256": "another-plan",
                "approved_by": "Chad Josewski",
                "source": "user_message",
                "owner_statement": "Synthetic test only",
                "approved_at": "2026-01-01T00:00:00Z",
            }
        )
    )
    with pytest.raises(ValueError, match="does not cover"):
        probe.require_approval(tmp_path, plan)


@pytest.mark.parametrize("change", ["budget", "owner"])
def test_server_with_wrong_budget_or_parent_is_rejected(tmp_path, monkeypatch, change):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "owned-server.pid").write_text("123")
    (runtime / "launcher.pid").write_text("100")
    argv = probe.server_command("/synthetic/model.gguf")
    if change == "budget":
        argv[-1] = "-1"

    def output(command, **kwargs):
        if command[2] == "command=":
            return " ".join(argv)
        return "99" if change == "owner" else "100"

    monkeypatch.setattr(probe.subprocess, "check_output", output)
    with pytest.raises(ValueError, match="command or thinking budget differs"):
        probe.check_owned_server(tmp_path, "/synthetic/model.gguf")
