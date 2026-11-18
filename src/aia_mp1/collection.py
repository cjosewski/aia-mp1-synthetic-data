"""Bounded assessed collection; failed sub-batches remain immutable evidence."""

from pathlib import Path

from .assessment import exclusive, read_json, read_text
from .config import RunConfig, load_inputs
from .gate import _normalized, evaluate_gate
from .generate import generate_run, generation_metrics, implementation_identity, validate_evidence
from .schemas import CATEGORIES, GeneratedItem
from .tracing import digest, now, read_records, run_directory, write_checkpoint

POLICY = {"batch_size": 50, "max_batches": 5, "max_attempts": 2, "target_per_category": 10}


def rule_identity() -> str:
    return digest(Path(__file__).with_name("gate.py").read_text(encoding="utf-8"))


def collection_directory(root: Path, collection_id: str) -> Path:
    if root.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError("collection evidence must stay outside the repository")
    if len(collection_id) > 55:
        raise ValueError("collection ID must be at most 55 characters")
    if (root / "collections").is_symlink():
        raise ValueError("symlink collection root is not supported")
    return run_directory(root / "collections", collection_id)


def checkpoint(directory: Path, manifest: dict) -> None:
    manifest["sha256"] = digest({k: v for k, v in manifest.items() if k != "sha256"})
    write_checkpoint(directory / "manifest.json", manifest)


def load_collection(root: Path, collection_id: str) -> tuple[Path, dict]:
    directory = collection_directory(root, collection_id)
    manifest = read_json(directory / "manifest.json")
    if manifest["sha256"] != digest({k: v for k, v in manifest.items() if k != "sha256"}):
        raise ValueError("collection checkpoint changed")
    if manifest["collection_id"] != collection_id or manifest["identity"]["policy"] != POLICY:
        raise ValueError("collection identity or budget differs")
    if manifest["identity"]["gate_rules_sha256"] != rule_identity():
        raise ValueError("collection gate rules changed")
    batches = manifest["batches"]
    if len(batches) > POLICY["max_batches"] or batches != [
        f"{collection_id}-b{i + 1:02d}" for i in range(len(batches))
    ]:
        raise ValueError("collection batch membership or budget changed")
    return directory, manifest


def inspect_batch(root: Path, run_id: str, identity: dict) -> dict:
    directory = run_directory(root, run_id)
    if (directory / ".generation.lock").exists():
        raise ValueError("batch has an active or interrupted writer; preserve for inspection")
    manifest = read_json(directory / "manifest.json")
    settings = identity["settings"]
    if (
        manifest["run_id"] != run_id
        or manifest["count"] != POLICY["batch_size"]
        or manifest["settings"] != settings
        or manifest["purpose"] != settings["purpose"]
        or manifest["source_manifest"] != identity["sources"]
        or manifest["implementation"] != identity["implementation"]
        or manifest["prompt_sha256"] != digest(identity["prompt"])
        or read_text(directory / "prompt.md") != identity["prompt"]
    ):
        raise ValueError("batch differs from frozen collection inputs")
    expected = digest(
        {
            "settings": settings,
            "prompt": identity["prompt"],
            "sources": identity["sources"],
            "count": POLICY["batch_size"],
            "implementation": identity["implementation"]["source_tree_sha256"],
        }
    )
    if manifest["fingerprint"] != expected:
        raise ValueError("batch fingerprint differs")
    starts = read_records(directory / "events.jsonl")
    attempts = read_records(directory / "attempts.jsonl")
    records = read_records(directory / "data.jsonl")
    validate_evidence(manifest, directory, starts, attempts, records)
    metrics = generation_metrics(manifest["count"], starts, attempts, records)
    terminal = manifest["status"] in {"complete", "incomplete"}
    if terminal and metrics != manifest["metrics"]:
        raise ValueError("batch metrics differ from ledger")
    if terminal:
        successful_ids = {a["record"]["item_id"] for a in attempts if a["schema_valid"]}
        if successful_ids != {r["item_id"] for r in records}:
            raise ValueError("terminal batch data does not include every successful attempt")
        if (manifest["status"] == "complete") != (len(records) == manifest["count"]):
            raise ValueError("terminal batch completion status differs from records")
        resolved_slots = {a["slot"] for a in attempts if a["schema_valid"]}
        for slot in set(range(manifest["count"])) - resolved_slots:
            if sum(e["slot"] == slot for e in starts) != POLICY["max_attempts"]:
                raise ValueError("terminal unresolved slot has unconsumed attempt budget")
    gate = None
    if (directory / "gate-report.json").exists():
        gate = read_json(directory / "gate-report.json")
        computed = evaluate_gate(
            [GeneratedItem.model_validate(r) for r in records], expected_count=50
        )
        if any(gate.get(k) != v for k, v in computed.items()) or (
            gate["generation_metrics"] != metrics
            or gate["purpose"] != settings["purpose"]
            or gate["input_sha256"] != digest(read_text(directory / "data.jsonl"))
            or gate["run_id"] != run_id
            or read_records(directory / "gate-items.jsonl") != gate["items"]
        ):
            raise ValueError("batch gate lineage differs")
    return {
        "manifest": manifest,
        "metrics": metrics,
        "records": records,
        "gate": gate,
        "terminal": terminal,
        "hashes": {
            p.name: digest(read_text(p))
            for p in sorted(directory.iterdir())
            if p.is_file() and p.name != ".generation.lock"
        },
    }


def summarize(root: Path, manifest: dict) -> dict:
    counts = dict.fromkeys(CATEGORIES, 0)
    previously_judged = set(manifest.get("baseline_replay", {}).get("excluded_item_ids", []))
    members, decisions, batches, seen, reasons = [], [], [], {}, []
    initial_valid = requests = planned = 0
    for run_id in manifest["batches"]:
        planned += 50
        if not (root / run_id / "manifest.json").exists():
            reasons.append("batch_not_started")
            continue
        batch = inspect_batch(root, run_id, manifest["identity"])
        metrics = batch["metrics"]
        initial_valid += metrics["initial_attempt_valid_count"]
        requests += metrics["started_attempts"]
        if not batch["terminal"] or batch["gate"] is None:
            reasons.append("batch_not_terminal_or_gated")
        if metrics["unresolved_attempt_ids"]:
            reasons.append("requests_with_unknown_outcome")
        if metrics["initial_attempt_valid_count"] * 100 < 95 * 50:
            reasons.append("batch_schema_validity_below_95_percent")
        batches.append(
            {
                "run_id": run_id,
                "hashes": batch["hashes"],
                "metrics": metrics,
                "status": batch["manifest"]["status"],
                "gate_status": batch["gate"]["status"] if batch["gate"] else None,
            }
        )
        if batch["gate"] is None:
            continue
        by_item = {i["item_id"]: i for i in batch["gate"]["items"]}
        for record in batch["records"]:
            question = _normalized(record["item"]["question"])
            previous = seen.get(question)
            duplicate_of = previous[1] if previous else None
            seen.setdefault(question, (run_id, record["item_id"]))
            rejection = list(by_item[record["item_id"]]["reasons"])
            if record["item_id"] in previously_judged:
                rejection.append("prior_judge_exposure")
            if previous and previous[0] != run_id:
                rejection.append("cross_batch_duplicate")
            category = record["category"]
            if not rejection and counts[category] >= 10:
                rejection.append("quota_excess")
            if not rejection:
                members.append(record)
                counts[category] += 1
            decisions.append(
                {
                    "item_id": record["item_id"],
                    "run_id": run_id,
                    "category": category,
                    "retained": not rejection,
                    "reasons": rejection,
                    "duplicate_of": duplicate_of,
                }
            )
    if requests > 500:
        raise ValueError("collection request budget exceeded")
    if any(n != 10 for n in counts.values()):
        reasons.append("category_deficits")
    if not planned or initial_valid * 100 < planned * 95:
        reasons.append("aggregate_schema_validity_below_95_percent")
    return {
        "collection_id": manifest["collection_id"],
        "purpose": manifest["identity"]["settings"]["purpose"],
        "status": "ready" if not reasons else "incomplete",
        "reasons": sorted(set(reasons)),
        "counts": counts,
        "planned_slots": planned,
        "started_attempts": requests,
        "remaining_batch_budget": 5 - len(manifest["batches"]),
        "initial_attempt_valid_count": initial_valid,
        "initial_attempt_schema_pass_rate": initial_valid / planned if planned else None,
        "batches": batches,
        "members": members,
        "decisions": decisions,
    }


def collection_status(root: Path, collection_id: str) -> dict:
    directory, manifest = load_collection(root, collection_id)
    with exclusive(directory):
        return summarize(root, manifest)


def collect(config: RunConfig, collection_id: str, client, *, resume=False) -> dict:
    from .cli import gate_run

    if config.purpose == "smoke" or config.max_attempts != 2:
        raise ValueError("collection requires assessed purpose and exactly two attempts per slot")
    prompt, sources = load_inputs(config)
    root = Path(config.artifact_root)
    directory = collection_directory(root, collection_id)
    identity = {
        "settings": config.public_settings(),
        "prompt": prompt,
        "sources": sources,
        "policy": POLICY,
        "implementation": implementation_identity(),
        "gate_rules_sha256": rule_identity(),
    }
    if not resume:
        directory.mkdir(parents=True, exist_ok=False)
        checkpoint(
            directory,
            {
                "schema_version": "1",
                "collection_id": collection_id,
                "created_at": now(),
                "identity": identity,
                "batches": [],
            },
        )
    with exclusive(directory):
        _, manifest = load_collection(root, collection_id)
        if manifest["identity"] != identity:
            raise ValueError(
                "resume requires identical collection inputs, policy and implementation"
            )
        if (directory / "frozen.json").exists():
            raise ValueError("frozen collection cannot resume")
        while True:
            summary = summarize(root, manifest)
            if summary["status"] == "ready":
                return summary
            last = manifest["batches"][-1] if manifest["batches"] else None
            batch = (
                inspect_batch(root, last, identity)
                if last and (root / last / "manifest.json").exists()
                else None
            )
            if batch and batch["metrics"]["unresolved_attempt_ids"]:
                raise ValueError("unknown request outcome; preserve collection for inspection")
            if batch and batch["terminal"] and batch["gate"] is not None:
                if batch["metrics"]["initial_attempt_valid_count"] * 100 < 95 * 50:
                    return summary
                last = None
            if last is None:
                if len(manifest["batches"]) == 5:
                    return summary
                last = f"{collection_id}-b{len(manifest['batches']) + 1:02d}"
                manifest["batches"].append(last)
                checkpoint(directory, manifest)  # Commit budget before starting a request.
                batch = None
            if not batch or not batch["terminal"]:
                generate_run(
                    config,
                    prompt,
                    sources,
                    count=50,
                    run_id=last,
                    client=client,
                    resume=batch is not None,
                )
            gate_run(root, last)
