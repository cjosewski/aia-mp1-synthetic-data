"""Assessed behavior is verified with temporary synthetic evidence only."""

import json
from pathlib import Path

import pytest
from assessed_fixtures import REPO, GoodClient, fixture_config

from aia_mp1.assessment import create_cohort_assessment, load_assessment
from aia_mp1.cli import main
from aia_mp1.cohort import freeze_cohort, load_cohort
from aia_mp1.collection import collect, collection_status
from aia_mp1.human_reference import freeze_reference
from aia_mp1.labels import record_label
from aia_mp1.model_client import AttemptResult
from aia_mp1.tracing import digest


def test_replenishes_failed_batch_without_rewriting_it(tmp_path):
    config = fixture_config(tmp_path)
    client = GoodClient(reject_first_category=True)
    summary = collect(config, "baseline", client)
    assert client.calls == 100 and summary["status"] == "ready"
    assert summary["batches"][0]["gate_status"] == "failed"
    assert summary["counts"] == dict.fromkeys(summary["counts"], 10)
    assert len(summary["members"]) == 50
    assert sum("quota_excess" in d["reasons"] for d in summary["decisions"]) == 40
    root = Path(config.artifact_root)
    before = (root / "baseline-b01/gate-report.json").read_bytes()
    freeze_cohort(root, "baseline", "frozen")
    assert load_cohort(root, "frozen")["summary"] == summary
    assert (root / "baseline-b01/gate-report.json").read_bytes() == before
    with pytest.raises(ValueError, match="frozen"):
        collect(config, "baseline", client, resume=True)


@pytest.mark.parametrize("kind", ["permission", "hash", "category", "duplicate", "uses"])
def test_bad_sources_prevent_all_calls(tmp_path, kind):
    config = fixture_config(tmp_path)
    path = Path(config.reference_pack_path)
    pack = json.loads(path.read_text())
    if kind == "permission":
        pack["permission_status"] = "pending"
    if kind == "hash":
        pack["sources"][0]["text"] += " changed"
    if kind == "category":
        pack["tasks"].pop()
    if kind == "duplicate":
        pack["tasks"][1]["brief"] = pack["tasks"][0]["brief"]
    if kind == "uses":
        pack["sources"][0]["allowed_uses"].remove("judge_context")
    path.write_text(json.dumps(pack))
    client = GoodClient()
    with pytest.raises(ValueError):
        collect(config, "blocked", client)
    assert client.calls == 0
    assert not (Path(config.artifact_root) / "collections/blocked").exists()


def test_collection_budget_cannot_be_reset_by_resume(tmp_path):
    config = fixture_config(tmp_path)
    client = GoodClient(all_rejected=True)
    summary = collect(config, "bounded", client)
    assert client.calls == 250 and summary["remaining_batch_budget"] == 0
    assert summary["status"] == "incomplete"
    assert collect(config, "bounded", client, resume=True) == summary
    assert client.calls == 250


def test_cross_batch_duplicate_reserves_first_rejected_question(tmp_path):
    config = fixture_config(tmp_path)
    summary = collect(config, "duplicates", GoodClient(duplicates=True))
    assert len(summary["members"]) == 1
    assert any(d["duplicate_of"] for d in summary["decisions"] if d["run_id"].endswith("b02"))


def test_unknown_requests_cannot_be_hidden_by_resume(tmp_path):
    config = fixture_config(tmp_path)
    client = GoodClient(interrupt=3)
    with pytest.raises(KeyboardInterrupt):
        collect(config, "interrupted", client)
    with pytest.raises(ValueError, match="unknown request"):
        collect(config, "interrupted", client, resume=True)
    assert client.calls == 3


def test_cohort_tampering_and_changed_inputs_are_rejected(tmp_path):
    config = fixture_config(tmp_path)
    collect(config, "baseline", GoodClient())
    root = Path(config.artifact_root)
    freeze_cohort(root, "baseline", "frozen")
    create_cohort_assessment(root, "frozen", "review", REPO / "config/rubric.json")
    manifest = load_assessment(root, "review")[1]
    assert len(manifest["selected_ids"]) == 20
    assert manifest["reference_pack_sha256"]
    path = root / "baseline-b01/attempts.jsonl"
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError):
        load_assessment(root, "review")


def test_labels_freeze_requires_declared_blind_complete_reviews(tmp_path):
    config = fixture_config(tmp_path)
    collect(config, "baseline", GoodClient())
    root = Path(config.artifact_root)
    freeze_cohort(root, "baseline", "frozen")
    manifest = create_cohort_assessment(root, "frozen", "review", REPO / "config/rubric.json")
    with pytest.raises(ValueError, match="20"):
        freeze_reference(root, "review", "Synthetic reviewer", declare_blind=True)
    for item_id in manifest["selected_ids"]:
        record_label(
            root,
            "review",
            item_id,
            dict.fromkeys([f"D{i}" for i in range(1, 7)], 1),
            "Synthetic reviewer",
            review_stage="blind",
        )
    with pytest.raises(ValueError, match="declare"):
        freeze_reference(root, "review", "Synthetic reviewer", declare_blind=False)
    reference = freeze_reference(root, "review", "Synthetic reviewer", declare_blind=True)
    assert len(reference["labels"]) == 20
    with pytest.raises(FileExistsError):
        freeze_reference(root, "review", "Synthetic reviewer", declare_blind=True)


def test_cli_source_check_and_no_credentials_on_invalid_pack(tmp_path, capsys):
    config = fixture_config(tmp_path)
    assert main(["source-check", "--pack", config.reference_pack_path]) == 0
    assert json.loads(capsys.readouterr().out)["tasks"] == 50
    path = Path(config.reference_pack_path)
    path.write_text("{}")
    config_path = tmp_path / "config.json"
    config_path.write_text(config.model_dump_json())
    assert main(["collect", "--config", str(config_path), "--collection-id", "invalid"]) == 2
    assert "reference pack" in capsys.readouterr().err


def test_schema_failure_batch_stops_collection_without_replacement(tmp_path):
    config = fixture_config(tmp_path)

    class RetryClient(GoodClient):
        def generate(self, messages):
            if self.calls % 2 == 0:
                self.calls += 1
                return AttemptResult(None, "invalid", "invalid JSON", "ValidationError")
            return super().generate(messages)

    client = RetryClient()
    summary = collect(config, "low-schema", client)
    assert client.calls == 100
    assert summary["initial_attempt_schema_pass_rate"] == 0
    assert summary["remaining_batch_budget"] == 4
    assert "batch_schema_validity_below_95_percent" in summary["reasons"]
    with pytest.raises(ValueError, match="not ready"):
        freeze_cohort(Path(config.artifact_root), "low-schema", "bad")


def test_scores_cannot_enter_reference_context(tmp_path):
    config = fixture_config(tmp_path)
    path = Path(config.reference_pack_path)
    pack = json.loads(path.read_text())
    pack["tasks"][0]["human_labels"] = {"D1": 1}
    path.write_text(json.dumps(pack))
    with pytest.raises(ValueError, match="scores"):
        collect(config, "leak", GoodClient())


def test_collection_refuses_changed_pack_and_concurrent_writer(tmp_path):
    config = fixture_config(tmp_path)
    collect(config, "original", GoodClient())
    root = Path(config.artifact_root)
    lock = root / "collections/original/.writer.lock"
    lock.write_text("another writer")
    with pytest.raises(FileExistsError):
        collection_status(root, "original")
    assert lock.read_text() == "another writer"
    lock.unlink()
    path = Path(config.reference_pack_path)
    pack = json.loads(path.read_text())
    pack["sources"][0]["text"] += " New synthetic revision."
    pack["sources"][0]["content_sha256"] = digest(pack["sources"][0]["text"])
    path.write_text(json.dumps(pack))
    with pytest.raises(ValueError, match="identical"):
        collect(config, "original", GoodClient(), resume=True)


def test_wrong_generator_model_is_a_recorded_failure(tmp_path):
    config = fixture_config(tmp_path)

    class AliasClient(GoodClient):
        def generate(self, messages):
            result = super().generate(messages)
            return AttemptResult(result.item, result.raw_response, None, None, "wrong-model")

    summary = collect(config, "alias", AliasClient())
    assert summary["started_attempts"] == 100
    assert len(summary["members"]) == 0
    assert summary["status"] == "incomplete"


def test_terminal_exhausted_slot_can_contribute_without_erasing_failures(tmp_path):
    config = fixture_config(tmp_path)

    class ExhaustOneSlot(GoodClient):
        def generate(self, messages):
            if self.calls < 2:
                self.calls += 1
                return AttemptResult(None, "invalid fixture", "schema error", "ValidationError")
            return super().generate(messages)

    client = ExhaustOneSlot()
    summary = collect(config, "exhaust-one", client)
    assert summary["status"] == "ready" and client.calls == 101
    assert summary["batches"][0]["status"] == "incomplete"
    assert summary["batches"][0]["metrics"]["unresolved_slots"] == 1
    assert summary["initial_attempt_valid_count"] == 99
    assert summary["planned_slots"] == 100
    root = Path(config.artifact_root)
    freeze_cohort(root, "exhaust-one", "frozen")
    assert load_cohort(root, "frozen")["summary"]["started_attempts"] == 101
