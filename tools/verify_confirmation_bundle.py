"""Verify the local comparison bundle before any server or model request starts."""

import argparse
from pathlib import Path

from aia_mp1.assessment import read_json
from aia_mp1.confirmation_review import byte_hash
from aia_mp1.confirmation_transport import load_plan


def verify(root):
    manifest = read_json(root / "bundle-manifest.json")
    required = {
        "plan.json",
        "run-on-mac.sh",
        "project/uv.lock",
        "project/pyproject.toml",
        "project/src/aia_mp1/confirmation_transport.py",
        "packet/manifest.json",
        "review/human-reference.json",
        "review/submitted-answers.md",
    }
    if not required <= set(manifest["files_sha256"]):
        raise ValueError("bundle manifest is missing required files")
    for relative, expected in manifest["files_sha256"].items():
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
            raise ValueError("unsafe bundle path")
        if byte_hash(path) != expected:
            raise ValueError(f"frozen bundle file differs: {relative}")
    plan = load_plan(root / "plan.json", root / "packet", root / "review")
    if (
        plan["sha256"] != manifest["plan_sha256"]
        or plan["human_reference_sha256"] != manifest["human_reference_sha256"]
    ):
        raise ValueError("bundle plan or review identity differs")
    return len(manifest["files_sha256"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        print(f"Verified {verify(args.root)} frozen bundle files and human review.")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f"Bundle verification failed: {exc}\n")
