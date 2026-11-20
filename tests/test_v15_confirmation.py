"""Synthetic reviewed cases and fake runtime only; never model or human evidence."""

# ruff: noqa: F811 -- imported pytest fixtures

import importlib
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest
from test_confirmation_review import packet  # noqa: F401
from test_confirmation_transport import completion

from aia_mp1.canonical_development import QWEN_MODEL_SHA, QWEN_SETTINGS
from aia_mp1.confirmation_review import byte_hash, freeze_review, load_review
from aia_mp1.confirmation_transport import (
    GENERATOR_SHA,
    RUNTIME,
    audit,
    comparison_report,
    initialize,
    run_phase,
    wire_for,
)

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
try:
    runner = importlib.import_module("v15_confirmation")
    builder = importlib.import_module("prepare_v15_confirmation")
    remote = importlib.import_module("v15_remote")
finally:
    sys.path.pop(0)


@pytest.fixture
def fresh(packet, tmp_path, monkeypatch):
    packet_dir, _, answers = packet
    path = packet_dir / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest.update(
        settings=QWEN_SETTINGS,
        candidate_model_sha256=QWEN_MODEL_SHA,
        comparison_model_sha256=GENERATOR_SHA,
        prior_starts=318,
        maximum_new_starts=40,
        maximum_attempts_per_case_model=2,
        runtime={**RUNTIME, "reasoning_budget": 4096},
    )
    path.write_text(json.dumps(manifest))
    sha = byte_hash(path)
    monkeypatch.setattr(runner, "PACKET_SHA", sha)
    monkeypatch.setattr(builder, "PACKET_SHA", sha)
    monkeypatch.setattr(runner, "PACKET_ID", manifest["packet_id"])
    monkeypatch.setattr(runner, "PROMPT_SHA", manifest["prompt_sha256"])
    review = tmp_path / "review"
    freeze_review(packet_dir, sha, answers, review)
    models = {
        "candidate": "/synthetic/Qwen_Qwen3.5-122B-A10B-Q4_K_M-00001-of-00002.gguf",
        "comparator": "/synthetic/Qwen3-30B-A3B-Q4_K_M.gguf",
    }
    return packet_dir, review, models


def test_two_models_share_inputs_and_count_from_318(fresh, tmp_path):
    packet_dir, review, models = fresh
    plan = runner.make_plan(packet_dir, review, models)
    wires = [wire_for(plan, model, plan["cases"][0]) for model in plan["models"]]
    assert {k: v for k, v in wires[0].items() if k != "model"} == {
        k: v for k, v in wires[1].items() if k != "model"
    }
    assert "Synthetic test reviewer" not in json.dumps(wires)
    ledger = tmp_path / "ledger"
    initialize(plan, ledger)
    for phase in ("candidate", "comparator"):
        state = run_phase(plan, phase, ledger, lambda model, case, wire: (completion(model), None))
    result = comparison_report(plan, state, load_review(packet_dir, runner.PACKET_SHA, review))
    assert result["starts"] == 20 and result["cumulative_starts"] == 338
    assert all(value["initial_valid"] == 10 for value in result["models"].values())


@pytest.mark.parametrize(
    "field,value",
    [
        ("prior_starts", 190),
        ("maximum_new_starts", 41),
        ("maximum_attempts_per_case_model", 3),
        ("packet_id", "other"),
    ],
)
def test_protocol_changes_rejected_even_with_rehashed_manifest(fresh, monkeypatch, field, value):
    packet_dir, review, models = fresh
    original = runner.verify_packet

    def changed(*args):
        manifest, ids = original(*args)
        manifest[field] = value
        return manifest, ids

    monkeypatch.setattr(runner, "verify_packet", changed)
    with pytest.raises(ValueError, match="distributed protocol"):
        runner.make_plan(packet_dir, review, models)


def test_missing_review_prevents_bundle_and_all_remote_work(fresh, tmp_path, monkeypatch):
    packet_dir, _, _ = fresh
    destination = tmp_path / runner.BUNDLE_NAME
    monkeypatch.setattr(builder, "git", lambda *a: pytest.fail("must check review before Git"))
    monkeypatch.setattr(
        remote, "remote", lambda *a, **k: pytest.fail("no remote work before review")
    )
    with pytest.raises((OSError, ValueError)):
        builder.prepare(
            packet_dir, runner.PACKET_SHA, tmp_path / "missing", destination, Path("/synthetic")
        )
    assert not destination.exists() and not destination.with_suffix(".zip").exists()


def test_shared_failures_stop_comparator(fresh, tmp_path):
    packet_dir, review, models = fresh
    plan = runner.make_plan(packet_dir, review, models)
    ledger = tmp_path / "ledger"
    initialize(plan, ledger)
    state = run_phase(plan, "candidate", ledger, lambda *a: (None, "Synthetic connection failure"))
    assert len(state["attempts"]) == 2
    with pytest.raises(ValueError, match="next permitted"):
        run_phase(plan, "comparator", ledger, lambda *a: pytest.fail("must not reset failures"))
    assert len(audit(plan, ledger)["attempts"]) == 2


@pytest.fixture
def packaged(fresh, tmp_path, monkeypatch):
    packet_dir, review, _ = fresh
    names = [
        "uv.lock",
        "pyproject.toml",
        "src/aia_mp1/confirmation_transport.py",
        "tools/prepare_v15_confirmation.py",
        "tools/v15_confirmation.py",
        "tools/v15_remote.py",
        "tools/run_v15_confirmation_on_mac.sh",
    ]
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name in names:
            archive.add(REPO / name, arcname=name)

    def fake_git(*args):
        return {"diff": b"", "rev-parse": b"synthetic-commit\n", "archive": buffer.getvalue()}[
            args[0]
        ]

    monkeypatch.setattr(builder, "git", fake_git)
    destination = tmp_path / runner.BUNDLE_NAME
    result = builder.prepare(packet_dir, runner.PACKET_SHA, review, destination, Path("/synthetic"))
    return destination, result


def test_package_preserves_submission_and_rejects_recovery_or_changed_code(packaged):
    root, result = packaged
    plan = runner.verify(root)
    assert result["plan_sha256"] == plan["sha256"]
    assert not (root / "packet/MY-ANSWERS.md").exists()
    (root / "results").mkdir()
    recovery = root / "results" / runner.RECOVERY_FILE
    recovery.write_text("Synthetic unauthorized recovery")
    with pytest.raises(ValueError, match="does not authorize"):
        runner.verify(root)
    recovery.unlink()
    (root / "project/tools/v15_remote.py").write_text("Synthetic altered code")
    with pytest.raises(ValueError, match="file differs"):
        runner.verify(root)


def test_changed_owned_process_stops_before_recording_a_start(packaged, monkeypatch):
    root, _ = packaged
    plan = runner.verify(root)
    project = root / "project"
    monkeypatch.setattr(runner, "__file__", str(project / "tools/v15_confirmation.py"))
    monkeypatch.setattr(runner.aia_mp1, "__file__", str(project / "src/aia_mp1/__init__.py"))
    monkeypatch.setattr(remote, "__file__", str(project / "tools/v15_remote.py"))
    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runner.platform, "release", lambda: "synthetic-microsoft")

    def preflight(plan, directory, *, phase, remote_root):
        (directory / f"{phase}-runtime.json").write_text(
            json.dumps(
                {"plan_sha256": plan["sha256"], "phase": phase, "owned_process": {"pid": 123}}
            )
        )

    monkeypatch.setattr(runner, "preflight", preflight)
    monkeypatch.setattr(runner, "owned", lambda *a: {"pid": 124})
    monkeypatch.setattr(runner, "client_for", lambda *a: pytest.fail("must not dispatch"))
    with pytest.raises(ValueError, match="process changed"):
        runner.execute(root, plan, "candidate")
    assert not list((root / "results").glob("*-start.json"))


def test_unfrozen_client_rejected_before_ledger_creation(packaged, monkeypatch):
    root, _ = packaged
    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runner.platform, "release", lambda: "synthetic-microsoft")
    with pytest.raises(ValueError, match="frozen bundle project"):
        runner.execute(root, runner.verify(root), "candidate")
    assert not (root / "results").exists()


@pytest.mark.parametrize("defect", [None, "weight", "template", "budget", "overflow"])
@pytest.mark.parametrize("endpoint", ["http://127.0.0.1:18081/v1", "http://127.0.0.1:18083/v1"])
def test_comparator_remote_preflight_uses_its_own_identity(
    fresh, tmp_path, monkeypatch, defect, endpoint
):
    packet_dir, review, models = fresh
    plan = runner.make_plan(packet_dir, review, models)
    template = "Synthetic comparator template"
    import hashlib

    monkeypatch.setattr(remote, "QWEN3_TEMPLATE_SHA", hashlib.sha256(template.encode()).hexdigest())
    monkeypatch.setattr(remote.platform, "system", lambda: "Linux")
    monkeypatch.setattr(remote.platform, "release", lambda: "synthetic-microsoft")
    monkeypatch.setattr(
        remote,
        "remote",
        lambda *a, **k: (
            "42\n" + ("wrong" if defect == "weight" else GENERATOR_SHA) + " model.gguf\n"
        ),
    )
    roots = []

    def owned(model, root):
        roots.append(root)
        command = f"/opt/homebrew/bin/llama-server --model {model} --host 127.0.0.1 --port 8081 --ctx-size 16384 --parallel 1 --reasoning on --reasoning-format deepseek --reasoning-budget {8192 if defect == 'budget' else 4096}"
        return remote.validate_owned("Darwin arm64\n123\n120\n120\n" + command, model)

    monkeypatch.setattr(remote, "owned", owned)

    class Server:
        def __init__(self, *a):
            assert a[0] == endpoint

        def json(self, path, wire=None):
            return {
                "/props": {
                    "build_info": RUNTIME["build_info"],
                    "total_slots": 1,
                    "default_generation_settings": {"n_ctx": 16384},
                    "model_path": models["comparator"],
                    "chat_template": "changed" if defect == "template" else template,
                },
                "/v1/models": {"data": [{"id": models["comparator"]}]},
                "/health": {"status": "ok"},
                "/apply-template": {"prompt": "<|im_start|>assistant"},
            }[path]

        def token_fit(self, *a):
            return {"fits": defect != "overflow"}

        def close(self):
            pass

    monkeypatch.setattr(remote, "LocalServer", Server)
    # Keep the real phase-specific prefix validator, but pin its test template.
    monkeypatch.setattr(
        sys.modules["aia_mp1.confirmation_transport"],
        "QWEN3_TEMPLATE_SHA",
        remote.QWEN3_TEMPLATE_SHA,
    )
    output = tmp_path / "runtime"
    output.mkdir()
    if defect:
        with pytest.raises(ValueError):
            remote.preflight(
                plan,
                output,
                phase="comparator",
                remote_root="/synthetic/comparator",
                endpoint=endpoint,
            )
        assert not (output / "comparator-runtime.json").exists()
    else:
        remote.preflight(
            plan, output, phase="comparator", remote_root="/synthetic/comparator", endpoint=endpoint
        )
        assert roots == ["/synthetic/comparator"]
        result = json.loads((output / "comparator-runtime.json").read_text())
        assert result["phase"] == "comparator" and len(result["token_checks"]) == 10
