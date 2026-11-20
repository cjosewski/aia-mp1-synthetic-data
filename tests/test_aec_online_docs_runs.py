"""Synthetic run lineage and fake saved judgments; no real labels or inference."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_aec_development as development
import screen_aec_online_docs as runner

from aia_mp1.assessment import read_json, save_new
from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.judge import JudgeConfig
from aia_mp1.tracing import digest

FOLLOWUP = "api-development-qwen-online-docs-002"


def saved_start(directory, item_id, stage, messages, cfg):
    target = directory / stage / item_id
    target.mkdir(parents=True)
    start = target / "start.json"
    save_new(
        start,
        {
            "identity": {
                "item_id": item_id,
                "stage": stage,
                "protocol_sha256": runner.file_hash(directory / "protocol.json"),
                "messages_sha256": digest({"messages": messages}),
                "model": cfg.model,
            },
            "started_at": "synthetic",
            "messages": messages,
        },
    )
    return start


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    root = tmp_path / "evidence"
    root.mkdir()
    cfg = JudgeConfig(
        base_url="http://127.0.0.1:18082/v1",
        model="/synthetic/qwen.gguf",
        model_sha256=runner.QWEN_MODEL_SHA,
        **runner.QWEN_SETTINGS,
    )
    (root / "judge-preparation-v1").mkdir()
    save_new(root / "judge-preparation-v1/judge.json", cfg.model_dump())
    ids = [f"synthetic-case-{i}" for i in range(10)]
    assessment = {"selected_ids": ids}
    records = [{"item_id": key} for key in ids]
    ratings = {d: {"decision": 1, "justification": "Synthetic only."} for d in DIMENSIONS}
    checkpoint = {"synthetic_reference": "not human evidence"}
    monkeypatch.setattr(
        runner,
        "load_assessment",
        lambda *args: (root / "synthetic-review", assessment, records, {}),
    )

    def freeze(directory, *args):
        runner.pin(directory / "review-checkpoint.json", checkpoint)
        return {key: {"decisions": dict.fromkeys(DIMENSIONS, 1)} for key in ids}

    def no_network(*args, **kwargs):
        pytest.fail("Preparation or retained-attempt validation must not dispatch")

    monkeypatch.setattr(runner, "freeze_development_labels", freeze)
    monkeypatch.setattr(runner, "LocalServer", no_network)
    monkeypatch.setattr(development, "LocalServer", no_network)
    monkeypatch.setattr(development, "InstructorClient", no_network)
    monkeypatch.setattr(runner, "open_page", no_network)
    control = root / runner.CONTROL
    control.mkdir()
    save_new(control / "protocol.json", {"synthetic": True})
    save_new(control / "control-report.json", {"synthetic": True})
    save_new(control / "review-checkpoint.json", checkpoint)
    originals = {}
    for i, key in enumerate(ids):
        originals[key] = runner.wire(
            "Synthetic judge prompt",
            {
                "untrusted_reference_context": {
                    "task": {"category": list(runner.PAGES)[i % 5], "brief": key}
                }
            },
        )
        start = saved_start(control, key, "control", originals[key], cfg)
        body = {
            "start_sha256": runner.file_hash(start),
            "completed_at": "synthetic",
            "raw": {
                "model": cfg.model,
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(ratings)}}],
            },
            "model": cfg.model,
            "error_type": None,
            "error": None,
            "parsed": ratings,
        }
        save_new(start.with_name("return.json"), body | {"sha256": digest(body)})
    (root / runner.SCREEN_MODEL).mkdir()
    save_new(root / runner.SCREEN_MODEL / "requests.json", originals)
    assert runner.run(root, "prepare") == {"prepared": 10}
    prior = root / runner.DIRECTORY
    protocol = read_json(prior / "protocol.json")
    protocol["source"]["tools/screen_aec_online_docs.py"] = "0" * 64
    (prior / "protocol.json").write_text(json.dumps(protocol))
    (prior / ".writer.lock").write_text("Synthetic interrupted writer")
    saved_start(prior, ids[0], "documented", originals[ids[0]], cfg)
    return root, cfg, ids


def test_followup_prepare_preserves_interrupted_parent_and_makes_no_requests(inputs):
    root, _, ids = inputs
    prior = root / runner.DIRECTORY
    original = runner.snapshot(prior)
    for _ in range(2):
        assert runner.run(root, "prepare", run_id=FOLLOWUP, predecessor=prior.name) == {
            "prepared": 10
        }
    output = root / FOLLOWUP
    protocol = read_json(output / "protocol.json")
    assert protocol["run_id"] == FOLLOWUP
    assert protocol["predecessor"] == {"run_id": prior.name, "files_sha256": original}
    assert protocol["cases"] == ids
    assert protocol["max_model_starts"] == 20 and protocol["max_page_requests"] == 30
    assert runner.snapshot(prior) == original
    assert set(runner.snapshot(output)) == {
        "protocol.json",
        "review-checkpoint.json",
        "lookup-requests.json",
    }


@pytest.mark.parametrize("stage", ["prepare", "score", "replay"])
@pytest.mark.parametrize("change", ["lock", "unknown_start", "deleted_start", "extra_file"])
def test_each_invocation_rejects_changed_predecessor_before_output_writes(inputs, stage, change):
    root, _, ids = inputs
    prior = root / runner.DIRECTORY
    runner.run(root, "prepare", run_id=FOLLOWUP, predecessor=prior.name)
    output_before = runner.snapshot(root / FOLLOWUP)
    target = {
        "lock": prior / ".writer.lock",
        "unknown_start": prior / "documented" / ids[0] / "start.json",
        "deleted_start": prior / "documented" / ids[0] / "start.json",
        "extra_file": prior / "unexpected.json",
    }[change]
    if change == "deleted_start":
        target.unlink()
    else:
        target.write_text("Synthetic tampering")
    with pytest.raises(ValueError, match="predecessor linkage differs"):
        runner.run(root, stage, run_id=FOLLOWUP, predecessor=prior.name)
    assert runner.snapshot(root / FOLLOWUP) == output_before


@pytest.mark.parametrize(
    "field,value",
    [
        ("cases", None),
        ("judge", {}),
        ("reference", "0" * 64),
        ("lookup_inputs", "0" * 64),
        ("control_report", "0" * 64),
        ("selectors", "Different selector"),
        ("final_instruction", "Different scoring instruction"),
        ("stages", {}),
        ("max_model_starts", 21),
        ("max_page_requests", 31),
    ],
)
def test_different_parent_comparison_rejected_before_creating_output(inputs, field, value):
    root, _, _ = inputs
    path = root / runner.DIRECTORY / "protocol.json"
    protocol = read_json(path)
    if field == "cases":
        value = list(reversed(protocol["cases"]))
    path.write_text(json.dumps(protocol | {field: value}))
    with pytest.raises(ValueError, match="comparison inputs differ"):
        runner.run(root, "prepare", run_id=FOLLOWUP, predecessor=runner.DIRECTORY)
    assert not (root / FOLLOWUP).exists()


@pytest.mark.parametrize("bad_id", ["../escape", "/tmp/escape", ".", "a/b", "a\\b", ""])
@pytest.mark.parametrize("field", ["run_id", "predecessor"])
def test_unsafe_ids_rejected_before_creating_anything(tmp_path, bad_id, field):
    options = {"run_id": FOLLOWUP, "predecessor": runner.DIRECTORY, field: bad_id}
    with pytest.raises(ValueError):
        runner.run(tmp_path, "prepare", **options)
    assert not list(tmp_path.iterdir())


def test_followup_requires_distinct_predecessor(tmp_path):
    with pytest.raises(ValueError, match="requires its predecessor"):
        runner.run(tmp_path, "prepare", run_id=FOLLOWUP)
    with pytest.raises(ValueError, match="must be different"):
        runner.run(tmp_path, "prepare", run_id=FOLLOWUP, predecessor=FOLLOWUP)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("where", ["output", "predecessor", "nested_predecessor", "nested_output"])
def test_symlink_run_targets_and_entries_rejected(inputs, where):
    root, _, _ = inputs
    prior = root / runner.DIRECTORY
    output = root / FOLLOWUP
    predecessor = prior.name
    if where == "output":
        output.symlink_to(prior, target_is_directory=True)
    elif where == "predecessor":
        predecessor = "symlink-parent"
        (root / predecessor).symlink_to(prior, target_is_directory=True)
    elif where == "nested_predecessor":
        (prior / "linked").symlink_to(root / runner.CONTROL, target_is_directory=True)
    else:
        runner.run(root, "prepare", run_id=FOLLOWUP, predecessor=predecessor)
        (output / "linked").symlink_to(prior, target_is_directory=True)
    with pytest.raises(ValueError, match="within the artifact root|Symlink"):
        runner.run(root, "prepare", run_id=FOLLOWUP, predecessor=predecessor)
    if where != "output":
        assert not (output / ".writer.lock").exists()


def test_copied_attempt_without_protocol_is_not_a_prepared_followup(inputs):
    root, _, _ = inputs
    target = root / FOLLOWUP / "lookup/synthetic-case-0"
    target.mkdir(parents=True)
    (target / "start.json").write_text("Synthetic copied attempt")
    before = runner.snapshot(root / FOLLOWUP)
    with pytest.raises(ValueError, match="Populated output has no frozen protocol"):
        runner.run(root, "prepare", run_id=FOLLOWUP, predecessor=runner.DIRECTORY)
    assert runner.snapshot(root / FOLLOWUP) == before


@pytest.mark.parametrize("stage", ["score", "replay"])
def test_unknown_followup_outcome_consumes_allocation_without_retry(inputs, monkeypatch, stage):
    root, cfg, ids = inputs
    runner.run(root, "prepare", run_id=FOLLOWUP, predecessor=runner.DIRECTORY)
    output = root / FOLLOWUP
    save_new(
        output / "deployment.json",
        {
            "parts": runner.QWEN_FILES,
            "model": cfg.model,
            "reasoning_budget": 4096,
            "build": "synthetic",
        },
    )
    messages = read_json(output / "lookup-requests.json")[ids[0]]
    saved_start(output, ids[0], "lookup", messages, cfg)
    before = runner.snapshot(output)

    class FakeServer:
        def __init__(self, *args):
            pass

        def json(self, route):
            assert route == "/props"
            return {
                "model_path": cfg.model,
                "build_info": "synthetic",
                "total_slots": 1,
                "default_generation_settings": {"n_ctx": 16384},
            }

        def close(self):
            pass

    monkeypatch.setattr(runner, "LocalServer", FakeServer)
    with pytest.raises(ValueError, match="Unknown outcome consumes"):
        runner.run(root, stage, run_id=FOLLOWUP, predecessor=runner.DIRECTORY)
    assert runner.snapshot(output) == before
