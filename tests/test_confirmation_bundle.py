"""Exercise portable packaging using a synthetic committed snapshot and review."""

# ruff: noqa: F811 -- pytest resolves the deliberately imported shared fixtures

import importlib.util
import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest
from test_confirmation_review import packet  # noqa: F401
from test_confirmation_transport import confirmation  # noqa: F401

from aia_mp1.confirmation_review import byte_hash

REPO = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, REPO / "tools" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


builder = module("confirmation_bundle_builder", "prepare_confirmation_bundle.py")
verifier = module("confirmation_bundle_verifier", "verify_confirmation_bundle.py")


@pytest.fixture
def synthetic_repo(tmp_path, monkeypatch):
    repo = tmp_path / "synthetic-repo"
    paths = (
        "tools/prepare_confirmation_bundle.py",
        "tools/run_confirmation_on_mac.sh",
        "tools/verify_confirmation_bundle.py",
        "src/aia_mp1/confirmation_transport.py",
        "uv.lock",
        "pyproject.toml",
    )
    for name in paths:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((REPO / name).read_bytes())
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name in paths:
            archive.add(repo / name, arcname=name)

    def fake_git(*args):
        if args[0] == "diff":
            return b""
        if args[0] == "rev-parse":
            return b"synthetic-test-commit-only\n"
        if args[0] == "archive":
            return buffer.getvalue()
        pytest.fail(f"unexpected git operation: {args}")

    monkeypatch.setattr(builder, "REPOSITORY", repo)
    monkeypatch.setattr(builder, "git", fake_git)
    return repo


def test_bundle_freezes_code_review_inputs_and_zip(confirmation, synthetic_repo, tmp_path):  # noqa: F811
    plan, _, packet_dir, review, _ = confirmation
    destination = tmp_path / "synthetic-bundle"
    result = builder.prepare(
        packet_dir, plan["packet_manifest_sha256"], review, destination, Path("/synthetic/Models")
    )
    assert result["commit"] == "synthetic-test-commit-only"
    assert verifier.verify(destination) == result["frozen_files"]
    assert (destination / "review/submitted-answers.md").read_bytes() == (
        review / "submitted-answers.md"
    ).read_bytes()
    assert "MY-ANSWERS.md" not in [p.name for p in (destination / "packet").iterdir()]
    assert byte_hash(Path(result["archive"])) == result["archive_sha256"]
    with zipfile.ZipFile(result["archive"]) as archive:
        for name in archive.namelist():
            assert archive.read(name) == (tmp_path / name).read_bytes()
    with pytest.raises(FileExistsError):
        builder.prepare(
            packet_dir,
            plan["packet_manifest_sha256"],
            review,
            destination,
            Path("/synthetic/Models"),
        )
    (destination / "project/src/aia_mp1/confirmation_transport.py").write_text("changed")
    with pytest.raises(ValueError, match="file differs"):
        verifier.verify(destination)


def test_bundle_rejects_dirty_code_before_creating_output(
    confirmation, synthetic_repo, tmp_path, monkeypatch
):  # noqa: F811
    plan, _, packet_dir, review, _ = confirmation
    destination = tmp_path / "dirty-bundle"
    monkeypatch.setattr(builder, "git", lambda *args: b"changed.py")
    with pytest.raises(ValueError, match="commit reviewed code"):
        builder.prepare(
            packet_dir,
            plan["packet_manifest_sha256"],
            review,
            destination,
            Path("/synthetic/Models"),
        )
    assert not destination.exists()


def test_bundle_verifier_rejects_manifest_escape(confirmation, synthetic_repo, tmp_path):  # noqa: F811
    plan, _, packet_dir, review, _ = confirmation
    root = tmp_path / "bundle"
    builder.prepare(
        packet_dir, plan["packet_manifest_sha256"], review, root, Path("/synthetic/Models")
    )
    outside = tmp_path / "outside"
    outside.write_text("Synthetic external file must not be accepted.")
    manifest = json.loads((root / "bundle-manifest.json").read_text())
    manifest["files_sha256"]["../outside"] = byte_hash(outside)
    (root / "bundle-manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="unsafe bundle path"):
        verifier.verify(root)
