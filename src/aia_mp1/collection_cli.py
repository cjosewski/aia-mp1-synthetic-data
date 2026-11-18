"""Independent assessed source, collection and cohort commands."""

from pathlib import Path

from .cohort import freeze_cohort, load_cohort
from .collection import collect, collection_status
from .config import load_config, load_inputs
from .model_client import InstructorClient
from .sources import load_pack
from .tracing import digest

COMMANDS = {"source-check", "collect", "collection-status", "cohort", "cohort-status"}


def add_commands(commands):
    source = commands.add_parser(
        "source-check", help="validate permissions and reference content offline"
    )
    source.add_argument("--pack", type=Path, required=True)
    collect_cmd = commands.add_parser("collect", help="generate bounded assessed batches")
    collect_cmd.add_argument("--config", type=Path, required=True)
    collect_cmd.add_argument("--resume", action="store_true")
    collect_cmd.add_argument("--collection-id", required=True)
    status = commands.add_parser(
        "collection-status", help="validate collection and show quota/budget status"
    )
    status.add_argument("--collection-id", required=True)
    freeze = commands.add_parser(
        "cohort", help="freeze a ready collection into an immutable cohort"
    )
    freeze.add_argument("--collection-id", required=True)
    freeze.add_argument("--cohort-id", required=True)
    cohort_status = commands.add_parser("cohort-status", help="validate frozen cohort lineage")
    cohort_status.add_argument("--cohort-id", required=True)
    for command in (status, freeze, cohort_status):
        command.add_argument(
            "--artifact-root", type=Path, default=Path("../artifacts/evidence/P1-03")
        )


def compact(summary):
    return {k: v for k, v in summary.items() if k not in {"members", "decisions", "batches"}}


def run_command(args):
    if args.command == "source-check":
        pack = load_pack(args.pack)
        return {
            "status": "ready",
            "pack_id": pack["pack_id"],
            "sha256": digest(pack),
            "tasks": sum(map(len, pack["topics"].values()))
            if "topics" in pack
            else len(pack["tasks"]),
            "sources": len(pack.get("sources", [])),
        }, 0
    if args.command == "collect":
        config = load_config(args.config)
        load_inputs(config)  # Permission failures precede credential lookup/client creation.
        with InstructorClient(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key(),
            mode=config.mode,
            timeout_seconds=config.timeout_seconds,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        ) as client:
            summary = collect(config, args.collection_id, client, resume=args.resume)
    elif args.command == "collection-status":
        summary = collection_status(args.artifact_root, args.collection_id)
    elif args.command == "cohort":
        manifest = freeze_cohort(args.artifact_root, args.collection_id, args.cohort_id)
        return {
            "cohort_id": manifest["cohort_id"],
            "sha256": manifest["sha256"],
            **compact(manifest["summary"]),
        }, 0
    else:
        manifest = load_cohort(args.artifact_root, args.cohort_id)
        return {
            "cohort_id": manifest["cohort_id"],
            "sha256": manifest["sha256"],
            **compact(manifest["summary"]),
        }, 0
    return compact(summary), 0 if summary["status"] == "ready" else 1
