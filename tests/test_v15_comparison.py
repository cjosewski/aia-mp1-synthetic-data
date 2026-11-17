"""Synthetic paired inputs/results; no real human ratings or model calls."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from test_confirmation_review import packet  # noqa: F401
from test_confirmation_transport import completion, confirmation  # noqa: F401

from aia_mp1.confirmation_review import byte_hash, load_review
from aia_mp1.confirmation_transport import audit, initialize, run_phase
from aia_mp1.tracing import digest

SPEC = importlib.util.spec_from_file_location(
    "v15_comparison", Path(__file__).resolve().parents[1] / "tools/v15_comparison.py"
)
screen = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
try:
    SPEC.loader.exec_module(screen)
finally:
    sys.path.pop(0)


@pytest.fixture
def paired(confirmation, tmp_path, monkeypatch):  # noqa: F811
    source, _, packet_dir, review_dir, _ = confirmation
    draft = tmp_path / "draft.md"
    draft.write_text("Synthetic alternative prompt only.")
    monkeypatch.setattr(screen, "SOURCE_SHA", source["sha256"])
    monkeypatch.setattr(screen, "DRAFT_SHA", byte_hash(draft))
    plan = screen.derive_plan(source, packet_dir, draft)
    ledger = tmp_path / "paired-ledger"
    initialize(plan, ledger)
    reference = load_review(packet_dir, source["packet_manifest_sha256"], review_dir)
    return plan, ledger, reference


def test_alternating_inputs_and_no_labels(paired):
    plan, ledger, reference = paired
    for control, treatment in zip(plan["cases"][::2], plan["cases"][1::2]):
        assert control["arm"] == "v13" and treatment["arm"] == "v15"
        assert control["messages"][1] == treatment["messages"][1]
        assert control["messages"][0] != treatment["messages"][0]
        assert "Synthetic test reviewer" not in json.dumps(treatment["messages"])
    calls = []

    def dispatch(model, case, wire):
        calls.append(case["arm"])
        return completion(model), None

    state = run_phase(plan, "candidate", ledger, dispatch)
    result = screen.report(plan, state, reference)
    assert calls == ["v13", "v15"] * 10
    assert result["starts"] == 20
    assert all(a["valid_cases"] == a["initial_valid"] == 10 for a in result["arms"].values())
    assert not result["numerical_advancement_conditions_met"]  # A tie is not improvement.


def test_failure_stop_crosses_arm_boundary(paired):
    plan, ledger, _ = paired
    calls = []

    def dispatch(model, case, wire):
        calls.append(case["arm"])
        return (completion(model), None) if len(calls) == 1 else (None, "Synthetic failure")

    state = run_phase(plan, "candidate", ledger, dispatch)
    assert calls == ["v13", "v15", "v15"]
    assert state["consecutive_failures"] == 2
    with pytest.raises(ValueError, match="next permitted"):
        run_phase(plan, "candidate", ledger, dispatch)


def test_process_loss_before_second_start_leaves_no_unknown_attempt(paired):
    plan, ledger, _ = paired
    checks = 0

    def check():
        nonlocal checks
        checks += 1
        if checks == 2:
            raise ValueError("Synthetic process lost")

    with pytest.raises(ValueError, match="process lost"):
        run_phase(
            plan, "candidate", ledger, lambda m, c, w: (completion(m), None), before_attempt=check
        )
    assert len(list(ledger.glob("*-start.json"))) == 1
    assert len(audit(plan, ledger)["attempts"]) == 1


def test_report_detects_new_api_false_approval_even_with_net_gain(paired):
    plan, ledger, reference = paired
    labels = {r["item_id"]: r["decisions"] for r in reference["labels"]}
    first = plan["cases"][0]["original_item_id"]
    assert labels[first]["D3"] == 0

    def dispatch(model, case, wire):
        raw = completion(model)
        decisions = dict(labels[case["original_item_id"]])
        if case["arm"] == "v13":
            decisions["D1"] = 1 - decisions["D1"]
        elif case["original_item_id"] == first:
            decisions["D3"] = 1
        raw["choices"][0]["message"]["content"] = json.dumps(
            {d: {"decision": v, "justification": "Synthetic."} for d, v in decisions.items()}
        )
        return raw, None

    result = screen.report(plan, run_phase(plan, "candidate", ledger, dispatch), reference)
    assert result["arms"]["v15"]["matching"] > result["arms"]["v13"]["matching"]
    assert result["new_safety_api_false_approvals"]["D3"] == [first]
    assert not result["numerical_advancement_conditions_met"]


def test_changed_draft_rejected(confirmation, tmp_path, monkeypatch):  # noqa: F811
    source, _, packet_dir, _, _ = confirmation
    monkeypatch.setattr(screen, "SOURCE_SHA", source["sha256"])
    draft = tmp_path / "draft.md"
    draft.write_text("Unapproved prompt change")
    with pytest.raises(ValueError, match="draft prompt"):
        screen.derive_plan(source, packet_dir, draft)


def test_changed_source_cannot_be_rehashed_into_approval(confirmation, tmp_path, monkeypatch):  # noqa: F811
    source, _, packet_dir, _, _ = confirmation
    monkeypatch.setattr(screen, "SOURCE_SHA", source["sha256"])
    source["max_starts"] = 100
    source["sha256"] = digest({k: v for k, v in source.items() if k != "sha256"})
    with pytest.raises(ValueError, match="source confirmation"):
        screen.derive_plan(source, packet_dir, tmp_path / "unused")


@pytest.mark.parametrize("change", ["parent", "budget", "model", "host"])
def test_remote_runtime_rejects_unowned_or_changed_process(change):
    remote = sys.modules["v15_remote"]
    command = "/opt/homebrew/bin/llama-server --model /synthetic/model.gguf --host 127.0.0.1 --port 8081 --ctx-size 16384 --parallel 1 --reasoning on --reasoning-format deepseek --reasoning-budget 4096"
    text = "Darwin arm64\n123\n120\n120\n" + command
    assert remote.validate_owned(text, "/synthetic/model.gguf")["pid"] == 123
    text = {
        "parent": text.replace("120\n120", "120\n119"),
        "budget": text.replace("4096", "8192"),
        "model": text.replace("model.gguf", "other.gguf"),
        "host": text.replace("Darwin", "Linux"),
    }[change]
    with pytest.raises(ValueError, match="Mac"):
        remote.validate_owned(text, "/synthetic/model.gguf")
