"""Freeze committed code, original confirmation inputs and the approved paired plan."""

import argparse
import io
import json
import shutil
import tarfile
import zipfile
from pathlib import Path

from prepare_confirmation_bundle import REPOSITORY, git
from v14_comparison import derive_plan, verify

from aia_mp1.assessment import read_json
from aia_mp1.canonical_development import save
from aia_mp1.confirmation_review import byte_hash
from aia_mp1.confirmation_transport import load_plan
from aia_mp1.tracing import now


def prepare(source_root, destination, approval_path):
    source = load_plan(source_root / "plan.json", source_root / "packet", source_root / "review")
    plan = derive_plan(
        source, source_root / "packet", REPOSITORY / "prompts/judge-v14-claims-draft.md"
    )
    if (
        destination.resolve().is_relative_to(REPOSITORY)
        or git("diff", "HEAD", "--name-only").strip()
    ):
        raise ValueError("commit code and use external evidence destination")
    archive_path = destination.with_name(destination.name + ".zip")
    if destination.exists() or archive_path.exists():
        raise ValueError("new immutable destination required")
    approval = read_json(approval_path)
    if approval.get("owner_statement") != "Approved" or approval.get("source") != "user_message":
        raise ValueError("attributed approval required")
    approval["plan_sha256"] = plan["sha256"]
    destination.mkdir(parents=True)
    project = destination / "project"
    project.mkdir()
    with tarfile.open(fileobj=io.BytesIO(git("archive", "HEAD"))) as archive:
        archive.extractall(project, filter="data")
    for name in ("packet", "review"):
        shutil.copytree(source_root / name, destination / name)
    shutil.copyfile(source_root / "plan.json", destination / "source-plan.json")
    shutil.copyfile(project / "tools/run_v14_comparison_on_mac.sh", destination / "run-on-mac.sh")
    save(destination / "plan.json", plan)
    save(destination / "owner-approval.json", approval)
    files = {
        p.relative_to(destination).as_posix(): byte_hash(p)
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }
    save(
        destination / "bundle-manifest.json",
        {
            "created_at": now(),
            "commit": git("rev-parse", "HEAD").decode().strip(),
            "plan_sha256": plan["sha256"],
            "files_sha256": files,
            "scope": "Approved known-case development; no automatic assessed follow-on",
        },
    )
    verify(destination)
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(destination.rglob("*")):
            if path.is_file():
                archive.write(
                    path, destination.name + "/" + path.relative_to(destination).as_posix()
                )
    return {
        "bundle": str(destination),
        "archive_sha256": byte_hash(archive_path),
        "plan_sha256": plan["sha256"],
        "frozen_files": len(files),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("approval", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination, args.approval), indent=2))
