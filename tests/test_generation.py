"""Exercise retry accounting, on-disk evidence, restart boundaries and independent gating."""

import json
import re
from pathlib import Path

import pytest

from aia_mp1.cli import gate_run, main
from aia_mp1.config import RunConfig, load_inputs
from aia_mp1.generate import generate_run
from aia_mp1.model_client import AttemptResult
from aia_mp1.schemas import QAItem
from aia_mp1.tracing import read_records, run_directory


def valid_item(number: int) -> QAItem:
    return QAItem(
        question=f"How do I validate the coordinate units of standalone test layer {number}?",
        answer="Inspect the declared coordinate system, compare a known distance, and save a copy after validation.",
        equipment_problem="Coordinate units need validation in a standalone synthetic fixture.",
        tools_required=["QGIS"],
        steps=[
            "Read the layer coordinate system.",
            "Measure the known reference distance.",
            "Save the validated copy.",
        ],
        safety_info="Incorrect coordinate units can corrupt measurement results; verify a known reference distance before saving.",
        tips=[
            "Keep the reference feature in a separate layer so later reprojection can be checked independently."
        ],
    )


class FakeClient:
    def __init__(self, *, fail_first=False, fail_all=False, interrupt_call=None):
        self.calls = 0
        self.fail_first = fail_first
        self.fail_all = fail_all
        self.interrupt_call = interrupt_call

    def generate(self, messages):
        self.calls += 1
        if self.calls == self.interrupt_call:
            raise KeyboardInterrupt
        message = messages[-1]["content"]
        slot = int(re.search(r"slot (\d+)", message).group(1))
        attempt = int(re.search(r"Attempt: (\d+)", message).group(1))
        if self.fail_all or (self.fail_first and attempt == 1):
            return AttemptResult(None, "{broken-json", "invalid JSON", "ValidationError")
        item = valid_item(slot)
        return AttemptResult(
            item,
            {"choices": [{"message": {"content": item.model_dump_json()}}]},
            None,
            None,
            "actual-local-model",
        )


@pytest.fixture
def config(tmp_path):
    return RunConfig(
        base_url="http://127.0.0.1:8080/v1",
        model="local-test-model",
        artifact_root=str(tmp_path / "evidence"),
    )


def execute(config, client=None, *, resume=False, count=5):
    return generate_run(
        config,
        "Standalone task in {category}",
        {"sources": []},
        count=count,
        run_id="test-run",
        client=client or FakeClient(),
        resume=resume,
    )


def test_retry_recovery_does_not_erase_initial_failure(config):
    client = FakeClient(fail_first=True)
    manifest = execute(config, client)
    assert client.calls == 10
    assert manifest["status"] == "complete"
    metrics = manifest["metrics"]
    assert metrics["initial_attempt_schema_pass_rate"] == 0
    assert metrics["all_completed_attempts_schema_pass_rate"] == 0.5
    assert metrics["successful_retries"] == 5
    assert metrics["schema_valid_items"] == 5
    directory = Path(config.artifact_root) / "test-run"
    attempts = read_records(directory / "attempts.jsonl")
    assert attempts[0]["raw_response"] == "{broken-json"
    assert attempts[1]["parent_attempt_id"] == attempts[0]["attempt_id"]
    assert attempts[1]["trace_id"] == attempts[0]["trace_id"]
    assert len(read_records(directory / "data.jsonl")) == 5
    gate = gate_run(Path(config.artifact_root), "test-run")
    assert gate["status"] == "passed"
    assert gate["quality_status"] == "pending"
    assert gate["course_acceptance"] == "not_evaluated"
    assert not gate["minimum_assessed_size_met"]
    assert gate_run(Path(config.artifact_root), "test-run") == gate


def test_exhaustion_is_finite_and_visible(config):
    client = FakeClient(fail_all=True)
    manifest = execute(config, client)
    assert client.calls == 15
    assert manifest["status"] == "incomplete"
    assert manifest["metrics"]["unresolved_slots"] == 5
    assert manifest["metrics"]["initial_attempt_schema_pass_rate"] == 0
    assert gate_run(Path(config.artifact_root), "test-run")["status"] == "failed"


def test_completed_run_cannot_be_overwritten_or_resumed(config):
    execute(config)
    path = Path(config.artifact_root) / "test-run" / "data.jsonl"
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        execute(config)
    with pytest.raises(ValueError, match="completed runs"):
        execute(config, resume=True)
    assert path.read_bytes() == original


def test_resume_preserves_data_and_charges_interrupted_attempt_to_budget(config):
    with pytest.raises(KeyboardInterrupt):
        execute(config, FakeClient(interrupt_call=2))
    directory = Path(config.artifact_root) / "test-run"
    first_data = (directory / "data.jsonl").read_bytes()
    assert not (directory / ".generation.lock").exists()
    client = FakeClient()
    manifest = execute(config, client, resume=True)
    assert client.calls == 4
    assert (directory / "data.jsonl").read_bytes().startswith(first_data)
    assert manifest["metrics"]["initial_attempt_schema_pass_rate"] == 0.8
    assert len(manifest["metrics"]["unresolved_attempt_ids"]) == 1
    events = read_records(directory / "events.jsonl")
    slot_two = [event for event in events if event["slot"] == 1]
    assert [event["attempt_number"] for event in slot_two] == [1, 2]
    assert slot_two[1]["parent_attempt_id"] == slot_two[0]["attempt_id"]


def test_resume_refuses_changed_settings_and_existing_lock(config):
    execute(config, FakeClient(fail_all=True))
    with pytest.raises(ValueError, match="original settings"):
        execute(config.model_copy(update={"model": "different"}), resume=True)
    lock = Path(config.artifact_root) / "test-run" / ".generation.lock"
    lock.write_text("another process")
    with pytest.raises(FileExistsError):
        execute(config, resume=True)
    assert lock.read_text() == "another process"


def test_gate_refuses_changed_data(config):
    execute(config)
    path = Path(config.artifact_root) / "test-run" / "data.jsonl"
    path.write_text(path.read_text().replace("actual-local-model", "tampered"))
    with pytest.raises(ValueError, match="changed"):
        gate_run(Path(config.artifact_root), "test-run")


@pytest.mark.parametrize("count", [0, 1, 6, 501, True])
def test_invalid_batch_size_makes_no_requests(config, count):
    client = FakeClient()
    with pytest.raises(ValueError, match="multiple of five"):
        execute(config, client, count=count)
    assert client.calls == 0


@pytest.mark.parametrize("run_id", ["../escape", "a/b", "", "x" * 65])
def test_run_id_cannot_escape_artifact_root(tmp_path, run_id):
    with pytest.raises(ValueError):
        run_directory(tmp_path, run_id)


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://api.openai.com/v1",
        "http://8.8.8.8/v1",
        "http://127.0.0.1:8080/v1?key=secret",
        "http://user:secret@127.0.0.1:8080/v1",
        "http://0.0.0.0/v1",
        "http://127.0.0.1/api",
    ],
)
def test_only_explicit_local_uncredentialed_endpoints(config, endpoint):
    with pytest.raises(ValueError):
        RunConfig.model_validate(config.model_dump() | {"base_url": endpoint})


def test_config_secrets_never_enter_public_settings(config, monkeypatch):
    monkeypatch.setenv("AIA_MP1_API_KEY", "test-secret-value")
    assert config.api_key() == "test-secret-value"
    assert "test-secret-value" not in json.dumps(config.public_settings())
    monkeypatch.delenv("AIA_MP1_API_KEY")
    with pytest.raises(ValueError, match="missing"):
        config.api_key()


def test_source_permission_is_required(config, tmp_path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("A task in {category}")
    sources = tmp_path / "sources.json"
    sources.write_text(
        json.dumps({"sources": [{"id": "public-is-not-licensed", "permission_status": "pending"}]})
    )
    config = config.model_copy(
        update={
            "prompt_path": str(prompt),
            "sources_path": str(sources),
            "source_refs": ["public-is-not-licensed"],
        }
    )
    with pytest.raises(ValueError, match="not cleared"):
        load_inputs(config)


def test_cli_reports_bad_config_without_echoing_input(tmp_path, capsys):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"base_url": "http://secret-user:secret-pass@127.0.0.1/v1", "model": "local"})
    )
    assert main(["generate", "--config", str(config_path), "--run-id", "bad-config"]) == 2
    captured = capsys.readouterr()
    assert "secret-pass" not in captured.err
    assert "Traceback" not in captured.err


def test_cli_exhaustion_returns_one_with_retained_evidence(config, monkeypatch, capsys):
    from aia_mp1 import cli

    class Client(FakeClient):
        def __init__(self, **kwargs):
            super().__init__(fail_all=True)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(cli, "load_config", lambda _: config)
    monkeypatch.setattr(cli, "load_inputs", lambda _: ("Task in {category}", {}))
    monkeypatch.setattr(cli, "InstructorClient", Client)
    monkeypatch.setenv("AIA_MP1_API_KEY", "test-key")
    assert main(["generate", "--config", "unused.json", "--run-id", "test-run"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "incomplete"
    assert len(read_records(Path(config.artifact_root) / "test-run" / "attempts.jsonl")) == 15


@pytest.mark.parametrize("filename", ["events.jsonl", "attempts.jsonl", "data.jsonl"])
def test_resume_refuses_tampered_or_deleted_evidence(config, filename):
    with pytest.raises(KeyboardInterrupt):
        execute(config, FakeClient(interrupt_call=2))
    directory = Path(config.artifact_root) / "test-run"
    original_manifest = (directory / "manifest.json").read_bytes()
    target = directory / filename
    if filename == "data.jsonl":
        target.write_text(target.read_text().replace("QGIS", "InventedAPI"))
    else:
        target.unlink()
    client = FakeClient()
    with pytest.raises(ValueError, match="changed or missing"):
        execute(config, client, resume=True)
    assert client.calls == 0
    assert (directory / "manifest.json").read_bytes() == original_manifest


def test_resume_checks_payload_against_completed_attempt(config):
    from aia_mp1.tracing import artifact_hashes

    with pytest.raises(KeyboardInterrupt):
        execute(config, FakeClient(interrupt_call=2))
    directory = Path(config.artifact_root) / "test-run"
    target = directory / "data.jsonl"
    target.write_text(target.read_text().replace("QGIS", "InventedAPI"))
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts_sha256"] = artifact_hashes(directory)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="differs from its successful attempt"):
        execute(config, resume=True)


@pytest.mark.parametrize("change", ["delete", "truncate", "alter"])
def test_cached_gate_never_hides_missing_or_modified_item_evidence(config, change):
    execute(config)
    gate_run(Path(config.artifact_root), "test-run")
    path = Path(config.artifact_root) / "test-run" / "gate-items.jsonl"
    if change == "delete":
        path.unlink()
    elif change == "truncate":
        path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
    else:
        path.write_text(path.read_text().replace('"accepted": true', '"accepted": false'))
    with pytest.raises(ValueError, match="missing or changed"):
        gate_run(Path(config.artifact_root), "test-run")


def test_gate_report_commits_only_after_per_item_output(config, monkeypatch):
    from aia_mp1 import cli

    execute(config)

    def fail_write(*args):
        raise OSError("synthetic interrupted write")

    monkeypatch.setattr(cli, "append_record", fail_write)
    with pytest.raises(OSError):
        gate_run(Path(config.artifact_root), "test-run")
    assert not (Path(config.artifact_root) / "test-run" / "gate-report.json").exists()
    monkeypatch.undo()
    with pytest.raises(ValueError, match="incomplete gate item evidence"):
        gate_run(Path(config.artifact_root), "test-run")


def test_gated_incomplete_run_is_frozen(config):
    execute(config, FakeClient(fail_all=True))
    gate_run(Path(config.artifact_root), "test-run")
    with pytest.raises(ValueError, match="gated runs are frozen"):
        execute(config, resume=True)


@pytest.mark.parametrize(
    "body",
    [
        [],
        {"sources": [{"id": "personal-task-briefs-v1", "allowed_uses": "local_smoke_generation"}]},
    ],
)
def test_source_manifest_shape_errors_are_controlled(config, tmp_path, body):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Task {category}")
    sources = tmp_path / "sources.json"
    sources.write_text(json.dumps(body))
    config = config.model_copy(update={"prompt_path": str(prompt), "sources_path": str(sources)})
    with pytest.raises(ValueError):
        load_inputs(config)


def test_raw_evidence_cannot_be_configured_inside_repository(config):
    import aia_mp1.config as config_module

    repository = Path(config_module.__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="outside the implementation"):
        RunConfig.model_validate(config.model_dump() | {"artifact_root": str(repository / "data")})


@pytest.mark.parametrize("filename", ["events.jsonl", "attempts.jsonl"])
@pytest.mark.parametrize("cached", [False, True])
def test_gate_requires_intact_attempt_evidence_even_with_valid_data(config, filename, cached):
    execute(config)
    if cached:
        gate_run(Path(config.artifact_root), "test-run")
    (Path(config.artifact_root) / "test-run" / filename).unlink()
    with pytest.raises(ValueError, match="changed or missing"):
        gate_run(Path(config.artifact_root), "test-run")
