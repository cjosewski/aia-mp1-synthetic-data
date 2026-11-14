"""Package committed code and a verified human reference for the authorized Mac."""

import argparse
import io
import json
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

from aia_mp1.canonical_development import save
from aia_mp1.confirmation_review import byte_hash, load_review, verify_packet
from aia_mp1.confirmation_transport import make_plan
from aia_mp1.tracing import now

REPOSITORY = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={REPOSITORY}", *args], cwd=REPOSITORY
    )


def prepare(packet, manifest_sha256, review, destination, models_root):
    manifest, _ = verify_packet(packet, manifest_sha256)
    reference = load_review(packet, manifest_sha256, review)
    if destination.resolve().is_relative_to(REPOSITORY):
        raise ValueError("confirmation bundle must stay outside the repository")
    if git("diff", "HEAD", "--name-only").strip():
        raise ValueError("commit reviewed code before freezing a comparison bundle")
    commit = git("rev-parse", "HEAD").decode().strip()
    models = {
        "candidate": str(
            models_root
            / "Qwen3.5-122B-A10B-Q4_K_M"
            / "Qwen_Qwen3.5-122B-A10B-Q4_K_M-00001-of-00002.gguf"
        ),
        "comparator": str(models_root / "Qwen3-30B-A3B-Q4_K_M.gguf"),
    }
    plan = make_plan(packet, manifest_sha256, review, models)
    archive_path = destination.with_name(destination.name + ".zip")
    if archive_path.exists():
        raise FileExistsError(archive_path)
    destination.mkdir(parents=True, exist_ok=False)
    project = destination / "project"
    project.mkdir()
    with tarfile.open(fileobj=io.BytesIO(git("archive", "HEAD"))) as archive:
        for member in archive.getmembers():
            if not member.isdir() and not member.isfile():
                raise ValueError("only regular committed files may enter the bundle")
            target = project / member.name
            if not target.resolve().is_relative_to(project.resolve()):
                raise ValueError("invalid committed archive path")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    shutil.copyfileobj(archive.extractfile(member), stream)
    # The builder and runtime must be the committed implementation, not untracked substitutes.
    for relative in (
        "tools/prepare_confirmation_bundle.py",
        "tools/run_confirmation_on_mac.sh",
        "tools/verify_confirmation_bundle.py",
        "src/aia_mp1/confirmation_transport.py",
    ):
        if byte_hash(REPOSITORY / relative) != byte_hash(project / relative):
            raise ValueError("packaging implementation differs from the committed snapshot")
    (destination / "packet").mkdir()
    for name in ["manifest.json", *manifest["files_sha256"]]:
        shutil.copyfile(packet / name, destination / "packet" / name)
    (destination / "review").mkdir()
    for name in ("submitted-answers.md", "human-reference.json"):
        shutil.copyfile(review / name, destination / "review" / name)
    save(destination / "plan.json", plan)
    shutil.copyfile(project / "tools/run_confirmation_on_mac.sh", destination / "run-on-mac.sh")
    frozen = {
        p.relative_to(destination).as_posix(): byte_hash(p)
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }
    save(
        destination / "bundle-manifest.json",
        {
            "schema_version": "1",
            "created_at": now(),
            "commit": commit,
            "plan_sha256": plan["sha256"],
            "human_reference_sha256": reference["sha256"],
            "files_sha256": frozen,
            "model_requests_at_preparation": 0,
            "scope": "Local noncommercial coursework; no public export or automatic qualification",
        },
    )
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(destination.rglob("*")):
            if path.is_file():
                archive.write(
                    path, destination.name + "/" + path.relative_to(destination).as_posix()
                )
    return {
        "bundle": str(destination),
        "archive": str(archive_path),
        "archive_sha256": byte_hash(archive_path),
        "frozen_files": len(frozen),
        "commit": commit,
        "plan_sha256": plan["sha256"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--models-root", type=Path, default=Path("/Users/chadjosewski/Models/MP1"))
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                prepare(
                    args.packet,
                    args.manifest_sha256,
                    args.review,
                    args.destination,
                    args.models_root,
                ),
                indent=2,
            )
        )
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"Bundle not prepared: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
