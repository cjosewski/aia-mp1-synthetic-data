"""Freeze committed V15 code, selected qualification and original baseline evidence."""

import argparse
import io
import json
import shutil
import tarfile
import zipfile
from pathlib import Path

from prepare_v15_confirmation import REPOSITORY, git
from v15_baseline import (
    ASSESSMENT_ID,
    BUNDLE_NAME,
    ENDPOINT,
    PRIOR_RUNS,
    RECOVERY_SHA,
    make_plan,
    verify,
)

from aia_mp1.assessed_native import NativeJudgeConfig
from aia_mp1.assessment import load_assessment, read_json, save_new
from aia_mp1.confirmation_review import byte_hash
from aia_mp1.tracing import now


def copy_regular(source, target):
    if source.is_symlink():
        raise ValueError("symlink input is not supported")
    if source.is_dir():
        target.mkdir(parents=True, exist_ok=False)
        for child in sorted(source.iterdir()):
            if child.name == ".writer.lock":
                raise ValueError("active or interrupted source writer requires inspection")
            copy_regular(child, target / child.name)
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(source.read_bytes())
    else:
        raise ValueError("only regular input files are supported")


def prepare(evidence, qualification, destination, recovery):
    if destination.name != BUNDLE_NAME or destination.resolve().is_relative_to(REPOSITORY):
        raise ValueError("use the designated external baseline bundle")
    if byte_hash(recovery) != RECOVERY_SHA:
        raise ValueError("replacement requires the inspected zero-request interruption")
    receipt = read_json(qualification / "qualification.json")
    config = NativeJudgeConfig(
        **{
            k: receipt[k]
            for k in ("model", "model_identity", "model_sha256", "stronger_model_basis")
        },
        **receipt["settings"],
        base_url=ENDPOINT,
        purpose="baseline",
        max_attempts=2,
        artifact_root=str(evidence),
        prompt_path=str(REPOSITORY / "prompts/judge-v15-task-contract.md"),
        prompt_variant="judge-v15-task-contract",
        qualification_path=str(qualification / "qualification.json"),
    )
    plan = make_plan(config)
    parent, assessment, _, _ = load_assessment(evidence, ASSESSMENT_ID)
    if {p.name for p in (parent / "judges").iterdir()} != PRIOR_RUNS:
        raise ValueError("final baseline version has already been allocated")
    if git("diff", "HEAD", "--name-only").strip():
        raise ValueError("commit reviewed code before packaging")
    commit = git("rev-parse", "HEAD").decode().strip()
    archive_path = destination.with_name(destination.name + ".zip")
    if archive_path.exists() or destination.exists():
        raise FileExistsError(destination)
    # Reject active source writers before creating a partial package.
    cohort = read_json(evidence / "cohorts" / assessment["cohort_id"] / "manifest.json")
    collection_id = cohort["collection_id"]
    inputs = [
        parent,
        evidence / "cohorts" / assessment["cohort_id"],
        evidence / "collections" / collection_id,
    ]
    inputs.extend(sorted(evidence.glob(collection_id + "-b[0-9][0-9]")))
    for source in [*inputs, qualification]:
        if any(p.name == ".writer.lock" or p.is_symlink() for p in source.rglob("*")):
            raise ValueError("source writer or symlink requires inspection")
    destination.mkdir(parents=True)
    project = destination / "project"
    project.mkdir()
    with tarfile.open(fileobj=io.BytesIO(git("archive", "HEAD"))) as archive:
        for member in archive.getmembers():
            target = project / member.name
            if not target.resolve().is_relative_to(project.resolve()) or not (
                member.isdir() or member.isfile()
            ):
                raise ValueError("unsafe committed archive entry")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    shutil.copyfileobj(archive.extractfile(member), stream)
    for relative in (
        "tools/prepare_v15_baseline.py",
        "tools/v15_baseline.py",
        "tools/v15_remote.py",
        "tools/run_v15_confirmation_on_mac.sh",
    ):
        if byte_hash(REPOSITORY / relative) != byte_hash(project / relative):
            raise ValueError("packaging code differs from committed snapshot")
    for source in inputs:
        copy_regular(source, destination / "evidence" / source.relative_to(evidence))
    copy_regular(qualification, destination / "qualification")
    copy_regular(recovery, destination / "preflight-interruption.json")
    save_new(
        destination / "judge-config.json",
        config.model_dump()
        | {
            "artifact_root": "../evidence",
            "prompt_path": "prompts/judge-v15-task-contract.md",
            "qualification_path": "../qualification/qualification.json",
        },
    )
    save_new(destination / "plan.json", plan)
    copy_regular(project / "tools/run_v15_confirmation_on_mac.sh", destination / "run-on-mac.sh")
    frozen = {
        p.relative_to(destination).as_posix(): byte_hash(p)
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }
    save_new(
        destination / "bundle-manifest.json",
        {
            "schema_version": "1",
            "created_at": now(),
            "commit": commit,
            "plan_sha256": plan["sha256"],
            "files_sha256": frozen,
            "scope": "Final original-baseline assessment; local noncommercial evidence only",
        },
    )
    verify(destination)
    # Verify copied evidence still matches its canonical source after packaging.
    for relative, expected in frozen.items():
        if (
            relative.startswith("evidence/")
            and byte_hash(evidence / relative.removeprefix("evidence/")) != expected
        ):
            raise ValueError("canonical evidence changed during packaging")
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(destination.rglob("*")):
            if path.is_file():
                archive.write(
                    path, destination.name + "/" + path.relative_to(destination).as_posix()
                )
    return {
        "bundle": str(destination),
        "commit": commit,
        "plan_sha256": plan["sha256"],
        "frozen_files": len(frozen),
        "archive_sha256": byte_hash(archive_path),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--preflight-recovery", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            prepare(
                args.evidence_root.resolve(),
                args.qualification.resolve(),
                args.destination.resolve(),
                args.preflight_recovery.resolve(),
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
