"""Read-only source validation and immutable assessment snapshots."""

import json
from contextlib import contextmanager
from pathlib import Path

from .evaluation_schemas import DIMENSIONS
from .gate import evaluate_gate
from .generate import generation_metrics, implementation_identity, validate_evidence
from .schemas import CATEGORIES, GeneratedItem
from .tracing import digest, now, read_records, run_directory

SOURCE_FILES = (
    "manifest.json",
    "events.jsonl",
    "attempts.jsonl",
    "data.jsonl",
    "gate-report.json",
    "gate-items.jsonl",
)


def read_text(path: Path) -> str:
    if path.is_symlink():
        raise ValueError(f"symlink evidence is not supported: {path.name}")
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict:
    value = json.loads(read_text(path))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path.name}")
    return value


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


@contextmanager
def exclusive(directory: Path):
    lock = directory / ".writer.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(now())
    try:
        yield
    finally:
        lock.unlink()


def assessment_directory(root: Path, assessment_id: str) -> Path:
    root = root.resolve()
    repository = Path(__file__).resolve().parents[2]
    if root.is_relative_to(repository):
        raise ValueError("assessment evidence must stay outside the repository")
    directory = root / "assessments"
    if directory.is_symlink():
        raise ValueError("symlink assessment root is not supported")
    return run_directory(directory, assessment_id)


def source_snapshot(root: Path, run_id: str) -> tuple[dict, list[dict], dict, dict]:
    directory = run_directory(root, run_id)
    hashes = {name: digest(read_text(directory / name)) for name in SOURCE_FILES}
    manifest = read_json(directory / "manifest.json")
    if manifest["run_id"] != run_id or manifest["status"] != "complete":
        raise ValueError("assessment requires the requested completed generation run")
    records = read_records(directory / "data.jsonl")
    starts = read_records(directory / "events.jsonl")
    attempts = read_records(directory / "attempts.jsonl")
    validate_evidence(manifest, directory, starts, attempts, records)
    metrics = generation_metrics(manifest["count"], starts, attempts, records)
    if metrics != manifest["metrics"] or metrics["unresolved_slots"]:
        raise ValueError("generation counts or completeness differ from evidence")
    typed = [GeneratedItem.model_validate(record) for record in records]
    if any(record.run_id != run_id for record in typed):
        raise ValueError("foreign run in assessment input")
    gate = read_json(directory / "gate-report.json")
    computed = evaluate_gate(typed, expected_count=manifest["count"])
    # Validate recorded decisions, not the CLI's current implementation fingerprint.
    # This permits read-only assessment of a frozen gate after CLI extensions.
    if any(gate.get(key) != value for key, value in computed.items()):
        raise ValueError("stored gate decisions differ from the unchanged gate rules")
    if (
        gate.get("run_id") != run_id
        or gate.get("input_sha256") != hashes["data.jsonl"]
        or gate.get("generation_metrics") != metrics
        or gate.get("purpose") != manifest["purpose"]
        or not gate.get("gate_implementation_sha256")
        or read_records(directory / "gate-items.jsonl") != gate["items"]
    ):
        raise ValueError("gate lineage or item evidence differs")
    return manifest, records, gate, hashes


def validate_rubric(rubric: dict) -> None:
    dimensions = rubric["dimensions"]
    if [row["id"] for row in dimensions] != list(DIMENSIONS):
        raise ValueError("rubric must contain ordered D1-D6 exactly once")
    if rubric.get("label_values") != [0, 1] or not rubric.get("version"):
        raise ValueError("rubric must define binary decisions and a version")
    for row in dimensions:
        if not all(
            isinstance(row.get(k), str) and row[k].strip()
            for k in ("name", "pass_anchor", "fail_anchor")
        ):
            raise ValueError("rubric anchors must be nonblank")
    if rubric["human_judge_agreement"]["per_dimension_minimum"] != 0.8:
        raise ValueError("course agreement threshold must remain 80%")


def select_items(records: list[dict], count: int, seed: str) -> list[str]:
    if type(count) is not int or count < 1 or count > len(records):
        raise ValueError("label count must be between one and the population size")
    buckets = {
        category: sorted(
            [r for r in records if r["category"] == category],
            key=lambda r: digest({"seed": seed, "item_id": r["item_id"]}),
        )
        for category in CATEGORIES
    }
    ordered = []
    for index in range(max(map(len, buckets.values()), default=0)):
        ordered.extend(buckets[c][index]["item_id"] for c in CATEGORIES if index < len(buckets[c]))
    return ordered[:count]


def population_for(
    source: dict, records: list[dict], gate: dict, purpose: str, label_count: int
) -> list[dict]:
    if purpose == "diagnostic":
        return records
    if purpose not in {"baseline", "corrected"}:
        raise ValueError("unknown assessment purpose")
    if source["purpose"] != purpose or gate["status"] != "passed":
        raise ValueError("smoke or failed gate evidence cannot become assessed data")
    sources = {s["id"]: s for s in source["source_manifest"]["sources"]}
    used = set(source["settings"]["source_refs"])
    if not used or any("assessed_generation" not in sources[s]["allowed_uses"] for s in used):
        raise ValueError("sources are not cleared for assessed generation")
    population = [r for r in records if r["item_id"] in gate["accepted_item_ids"]]
    if len(population) < 50 or label_count < 20:
        raise ValueError("assessment requires at least 50 retained items and 20 labels")
    if source["metrics"]["initial_attempt_schema_pass_rate"] < 0.95:
        raise ValueError("assessed input requires at least 95% initial schema validity")
    return population


def create_assessment(
    root: Path,
    run_id: str,
    assessment_id: str,
    rubric_path: Path,
    *,
    purpose: str = "diagnostic",
    label_count: int = 5,
    seed: str = "mp1-v1",
) -> dict:
    if purpose not in {"diagnostic", "baseline", "corrected"}:
        raise ValueError("unknown assessment purpose")
    directory = assessment_directory(root, assessment_id)
    source, all_records, gate, hashes = source_snapshot(root, run_id)
    rubric_text = read_text(rubric_path)
    rubric = json.loads(rubric_text)
    validate_rubric(rubric)
    population = population_for(source, all_records, gate, purpose, label_count)
    selected = select_items(population, label_count, seed)
    data = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in population)
    manifest = {
        "schema_version": "1",
        "assessment_id": assessment_id,
        "created_at": now(),
        "purpose": purpose,
        "assessment_eligible": purpose != "diagnostic",
        "source_run_id": run_id,
        "source_files_sha256": hashes,
        "generator_model": source["settings"]["model"],
        "generator_temperature": source["settings"]["temperature"],
        "population_ids": [r["item_id"] for r in population],
        "selected_ids": selected,
        "selection": {
            "algorithm": "sha256-stratified-round-robin-v1",
            "seed": seed,
            "count": label_count,
        },
        "rubric_version": rubric["version"],
        "rubric_sha256": digest(rubric_text),
        "data_sha256": digest(data),
        "implementation": implementation_identity(),
    }
    manifest["manifest_sha256"] = digest(manifest)
    directory.mkdir(parents=True, exist_ok=False)
    with (directory / "data.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data)
    with (directory / "rubric.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(rubric_text)
    (directory / "human-labels.jsonl").touch(exist_ok=False)
    save_new(
        directory / "labels-checkpoint.json",
        {
            "assessment_sha256": manifest["manifest_sha256"],
            "ledger_sha256": digest(""),
            "count": 0,
        },
    )
    save_new(directory / "manifest.json", manifest)
    return manifest


def load_assessment(root: Path, assessment_id: str) -> tuple[Path, dict, list[dict], dict]:
    directory = assessment_directory(root, assessment_id)
    manifest = read_json(directory / "manifest.json")
    fingerprint = manifest["manifest_sha256"]
    if manifest["assessment_id"] != assessment_id or fingerprint != digest(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    ):
        raise ValueError("assessment manifest identity changed")
    source, source_records, gate, hashes = source_snapshot(root, manifest["source_run_id"])
    if hashes != manifest["source_files_sha256"]:
        raise ValueError("assessment source evidence changed")
    data = read_text(directory / "data.jsonl")
    rubric_text = read_text(directory / "rubric.json")
    if digest(data) != manifest["data_sha256"] or digest(rubric_text) != manifest["rubric_sha256"]:
        raise ValueError("assessment data or rubric changed")
    rubric = json.loads(rubric_text)
    validate_rubric(rubric)
    records = read_records(directory / "data.jsonl")
    by_id = {r["item_id"]: r for r in source_records}
    if records != [by_id[i] for i in manifest["population_ids"]]:
        raise ValueError("assessment population differs from source")
    selection = manifest["selection"]
    expected = population_for(source, source_records, gate, manifest["purpose"], selection["count"])
    if (
        records != expected
        or manifest["assessment_eligible"] is not (manifest["purpose"] != "diagnostic")
        or manifest["rubric_version"] != rubric["version"]
        or manifest["generator_model"] != source["settings"]["model"]
        or manifest["generator_temperature"] != source["settings"]["temperature"]
        or selection["algorithm"] != "sha256-stratified-round-robin-v1"
    ):
        raise ValueError("assessment eligibility or metadata differs from source")
    if select_items(records, selection["count"], selection["seed"]) != manifest["selected_ids"]:
        raise ValueError("assessment selection changed")
    return directory, manifest, records, rubric


def item_identity(manifest: dict, record: dict) -> dict:
    return {
        "assessment_id": manifest["assessment_id"],
        "item_id": record["item_id"],
        "trace_id": record["trace_id"],
        "payload_sha256": digest(record["item"]),
        "rubric_version": manifest["rubric_version"],
        "rubric_sha256": manifest["rubric_sha256"],
    }
