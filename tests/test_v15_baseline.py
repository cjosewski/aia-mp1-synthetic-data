"""Synthetic baseline and fake runtime only; no human or live model evidence."""

import importlib
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest
from assessed_fixtures import GoodClient, fixture_config, qualified_judge

from aia_mp1 import assessed_native
from aia_mp1.assessment import create_cohort_assessment
from aia_mp1.cohort import freeze_cohort
from aia_mp1.collection import collect
from aia_mp1.confirmation_review import byte_hash
from aia_mp1.human_reference import freeze_reference
from aia_mp1.labels import record_label
from aia_mp1.tracing import digest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
try:
    runner = importlib.import_module("v15_baseline")
    builder = importlib.import_module("prepare_v15_baseline")
finally:
    sys.path.pop(0)


@pytest.fixture
def baseline(tmp_path, monkeypatch):
    generator = fixture_config(tmp_path)
    root = Path(generator.artifact_root)
    collect(generator, "baseline", GoodClient())
    freeze_cohort(root, "baseline", "frozen")
    manifest = create_cohort_assessment(
        root, "frozen", runner.ASSESSMENT_ID, REPO / "config/rubric.json"
    )
    for item in manifest["selected_ids"]:
        record_label(
            root,
            runner.ASSESSMENT_ID,
            item,
            dict.fromkeys([f"D{i}" for i in range(1, 7)], 1),
            "Synthetic reviewer",
            review_stage="blind",
        )
    reference = freeze_reference(
        root, runner.ASSESSMENT_ID, "Synthetic reviewer", declare_blind=True
    )
    monkeypatch.setattr(runner, "ASSESSMENT_SHA", manifest["manifest_sha256"])
    monkeypatch.setattr(runner, "REFERENCE_SHA", reference["sha256"])
    for name in runner.PRIOR_RUNS:
        directory = root / "assessments" / runner.ASSESSMENT_ID / "judges" / name
        directory.mkdir(parents=True)
        (directory / "synthetic-marker.txt").write_text("Synthetic prior allocation only")
    selection = tmp_path / "selection"
    selection.mkdir()
    old = qualified_judge(selection, generator)
    config = runner.NativeJudgeConfig(
        **(
            old.model_dump()
            | runner.QWEN_SETTINGS
            | {
                "base_url": runner.ENDPOINT,
                "model_sha256": runner.QWEN_MODEL_SHA,
                "purpose": "baseline",
                "server_reasoning_budget": 4096,
                "prompt_variant": "judge-v15-task-contract",
                "prompt_path": str(REPO / "prompts/judge-v15-task-contract.md"),
            }
        )
    )
    receipt = json.loads(Path(config.qualification_path).read_text())
    receipt.update(
        model_sha256=config.model_sha256,
        settings=runner.QWEN_SETTINGS | {"server_reasoning_budget": 4096},
        prompt_variant=config.prompt_variant,
        prompt_sha256_bytes=runner.PROMPT_SHA,
        native_runtime=runner.RUNTIME | {"reasoning_budget": 4096},
    )
    Path(config.qualification_path).write_text(json.dumps(receipt))
    return root, config, selection


def test_original_fifty_inputs_and_no_labels_in_requests(baseline):
    _, config, _ = baseline
    plan = runner.make_plan(config)
    assert len(plan["cases"]) == 50 and plan["maximum_starts"] == 100
    assert plan["prior_starts"] == 338
    assert "Synthetic reviewer" not in json.dumps(plan["cases"])
    assert plan["acceptance_policy"] == "course-per-dimension-80-v1"


@pytest.mark.parametrize("change", ["prompt", "reference", "budget", "version", "selection"])
def test_changed_evidence_or_protocol_stops_before_remote(baseline, monkeypatch, change):
    root, config, _ = baseline
    monkeypatch.setattr(runner.v15_remote, "remote", lambda *a, **k: pytest.fail("no network"))
    if change == "prompt":
        config = config.model_copy(
            update={"prompt_path": str(REPO / "prompts/judge-v13-hazards.md")}
        )
    elif change == "reference":
        monkeypatch.setattr(runner, "REFERENCE_SHA", "0" * 64)
    elif change == "budget":
        config = config.model_copy(update={"max_attempts": 3})
    elif change == "version":
        (root / "assessments" / runner.ASSESSMENT_ID / "judges" / "unauthorized-fourth").mkdir()
    else:
        path = Path(config.qualification_path).parent / "qualification-evidence.txt"
        path.write_text("tampered synthetic selection evidence")
    with pytest.raises(ValueError):
        runner.make_plan(config)


@pytest.fixture
def bundle(baseline, tmp_path, monkeypatch):
    root, _, selection = baseline
    names = [
        "uv.lock",
        "pyproject.toml",
        "prompts/judge-v15-task-contract.md",
        "tools/v15_baseline.py",
        "tools/v15_remote.py",
        "tools/v15_confirmation.py",
        "tools/prepare_v15_baseline.py",
        "tools/run_v15_confirmation_on_mac.sh",
    ]
    names.extend(p.relative_to(REPO).as_posix() for p in (REPO / "src/aia_mp1").glob("*.py"))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name in names:
            archive.add(REPO / name, arcname=name)

    def git(*args):
        return (
            buffer.getvalue()
            if args[0] == "archive"
            else (b"synthetic-commit" if args[0] == "rev-parse" else b"")
        )

    monkeypatch.setattr(builder, "git", git)
    destination = tmp_path / runner.BUNDLE_NAME
    recovery = tmp_path / "synthetic-interruption.json"
    recovery.write_text(json.dumps({"synthetic": True, "model_request_starts": 0}))
    monkeypatch.setattr(runner, "RECOVERY_SHA", byte_hash(recovery))
    monkeypatch.setattr(builder, "RECOVERY_SHA", byte_hash(recovery))
    receipt = builder.prepare(root, selection, destination, recovery)
    assert byte_hash(destination.with_name(destination.name + ".zip")) == receipt["archive_sha256"]
    return destination


def test_bundle_preserves_old_allocations_and_rejects_tampering(bundle):
    config, plan = runner.verify(bundle)
    assert runner.make_plan(config) == plan
    old = (
        bundle
        / "evidence/assessments"
        / runner.ASSESSMENT_ID
        / "judges"
        / sorted(runner.PRIOR_RUNS)[0]
        / "synthetic-marker.txt"
    )
    old.write_text("changed")
    with pytest.raises(ValueError, match="bundle changed"):
        runner.verify(bundle)


def test_rehashed_plan_cannot_lower_acceptance(bundle):
    path = bundle / "plan.json"
    plan = json.loads(path.read_text())
    plan["acceptance_policy"] = "owner-overall-70-20261116"
    plan["sha256"] = digest({k: v for k, v in plan.items() if k != "sha256"})
    path.write_text(json.dumps(plan))
    manifest_path = bundle / "bundle-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files_sha256"]["plan.json"] = byte_hash(path)
    manifest["plan_sha256"] = plan["sha256"]
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="plan differs"):
        runner.verify(bundle)


def test_changed_owned_process_prevents_first_request_start(bundle, monkeypatch):
    monkeypatch.setattr(runner, "__file__", str(bundle / "project/tools/v15_baseline.py"))
    monkeypatch.setattr(runner.aia_mp1, "__file__", str(bundle / "project/src/aia_mp1/__init__.py"))
    monkeypatch.setattr(runner.v15_remote, "__file__", str(bundle / "project/tools/v15_remote.py"))
    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runner.platform, "release", lambda: "synthetic-microsoft")

    def preflight(plan, directory, **kwargs):
        assert kwargs["endpoint"] == "http://127.0.0.1:18083/v1"
        (directory / "candidate-runtime.json").write_text(
            json.dumps({"properties": {}, "owned_process": {"pid": 123}})
        )

    monkeypatch.setattr(runner.v15_remote, "preflight", preflight)
    monkeypatch.setattr(runner.v15_remote, "owned", lambda *a: {"pid": 999})

    class Server:
        def __init__(self, *args):
            pass

        def close(self):
            pass

        def json(self, *args):
            pytest.fail("changed process must stop before HTTP")

    monkeypatch.setattr(assessed_native, "LocalServer", Server)
    assert runner.execute(bundle) == 1
    path = bundle / "evidence/assessments" / runner.ASSESSMENT_ID / "judges" / runner.RUN_ID
    assert (path / "events.jsonl").read_text() == ""
    assert (path / "attempts.jsonl").read_text() == ""
    with pytest.raises(ValueError, match="already started"):
        runner.execute(bundle)


def test_non_wsl_or_nonfrozen_client_never_contacts_mac(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.v15_remote, "remote", lambda *a, **k: pytest.fail("no network"))
    monkeypatch.setattr(runner.platform, "system", lambda: "Darwin")
    with pytest.raises(ValueError, match="WSL"):
        runner.execute(tmp_path)
    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runner.platform, "release", lambda: "synthetic-microsoft")
    with pytest.raises(ValueError, match="frozen baseline project"):
        runner.execute(tmp_path)


def test_recovery_receipt_required_before_packaging(tmp_path):
    wrong = tmp_path / "wrong.json"
    wrong.write_text('{"synthetic": true}')
    destination = tmp_path / runner.BUNDLE_NAME
    with pytest.raises(ValueError, match="zero-request interruption"):
        builder.prepare(tmp_path / "missing", tmp_path / "missing", destination, wrong)
    assert not destination.exists()
