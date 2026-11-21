"""AEC rubric v2 assessments: frozen eligibility after earlier reviews, then selection."""

import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

from .assessment import (
    assessment_directory,
    exclusive,
    item_identity,
    load_assessment,
    read_json,
    read_text,
    save_new,
    select_items,
)
from .cohort import load_cohort
from .generate import implementation_identity
from .labels import load_labels
from .rubric_v2 import RUBRIC_V2_PATH, RUBRIC_V2_SHA256, RUBRIC_V2_VERSION, load_rubric_v2
from .schemas import CATEGORIES, DOMAIN
from .tracing import digest, now, read_records

SCHEMA_VERSION = "v2-1"
ELIGIBILITY_RULE = "exclude-human-labeled-v1"
SELECTION_ALGORITHM = "sha256-stratified-round-robin-v1"
SELECTION_COUNT = 20
DOMAINS = {"engineering", "aec-course"}

# The v1 identity shape, bound to the v2 manifest's own assessment and rubric fields.
item_identity_v2 = item_identity


def is_v2(manifest: dict) -> bool:
    return (
        manifest.get("schema_version") == SCHEMA_VERSION
        and manifest.get("rubric_schema") == RUBRIC_V2_VERSION
    )


def _population(cohort: dict, rubric: dict) -> tuple[str, list[dict]]:
    settings, summary = cohort["identity"]["settings"], cohort["summary"]
    purpose = settings["purpose"]
    if purpose not in {"baseline", "corrected"} or summary["purpose"] != purpose:
        raise ValueError("v2 assessment requires a baseline or corrected cohort purpose")
    if settings.get("domain", "engineering") not in DOMAINS or DOMAIN not in DOMAINS:
        raise ValueError("v2 assessment requires the engineering or aec-course domain")
    members = summary["members"]
    minimum = rubric["dataset"]["minimum_items_per_run"]
    if len(members) < minimum:
        raise ValueError(f"v2 assessment requires at least {minimum} retained cohort members")
    planned = summary["planned_slots"]
    validity = Fraction(summary["initial_attempt_valid_count"], planned) if planned else 0
    if validity < Fraction(str(rubric["structural_validity_minimum"])):
        raise ValueError(
            "cohort initial-attempt schema validity is below the structural_validity_minimum "
            f"{rubric['structural_validity_minimum']}"
        )
    return purpose, members


def _earlier_review(root: Path, assessment_id: str) -> tuple[dict, list[str]]:
    """Verify an earlier assessment with its own loader; return its manifest and ledger lines."""
    manifest = read_json(assessment_directory(root, assessment_id) / "manifest.json")
    if is_v2(manifest):
        from .labels_v2 import load_labels_v2

        directory, manifest, records, _ = load_assessment_v2(root, assessment_id)
        load_labels_v2(directory, manifest, records)
    else:
        directory, manifest, records, _ = load_assessment(root, assessment_id)
        load_labels(directory, manifest, records)
    return manifest, read_text(directory / "human-labels.jsonl").splitlines(keepends=True)


def _prior_record(assessment_id: str, manifest: dict, lines: list[str]) -> tuple[dict, list]:
    labels = [json.loads(line)["label"] for line in lines]
    record = {
        "assessment_id": assessment_id,
        "manifest_sha256": manifest["manifest_sha256"],
        "ledger_sha256": digest("".join(lines)),
        "ledger_lines": len(lines),
        "labeled_item_ids": list(dict.fromkeys(label["item_id"] for label in labels)),
    }
    return record, labels


def _refuse_matching_labels(assessment_id: str, lines: list[str], population: list[dict]) -> None:
    """Refuse when a ledger already labels a population member, by item ID or payload hash."""
    ids = {record["item_id"] for record in population}
    owners = {digest(record["item"]): record["item_id"] for record in population}
    payloads = set(owners)
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            envelope = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"cannot read line {number} of the label ledger of assessment {assessment_id}; "
                "inspect it before declaring no prior reviews"
            ) from error
        label = envelope.get("label") if isinstance(envelope, dict) else None
        label = label if isinstance(label, dict) else {}
        if label.get("item_id") in ids or label.get("payload_sha256") in payloads:
            item_id = label.get("item_id")
            relation = (
                "which is in this cohort"
                if item_id in ids
                else f"whose payload equals cohort member {owners[label['payload_sha256']]}"
            )
            raise ValueError(
                f"assessment {assessment_id} already labeled {item_id}, {relation}; list it "
                "with --exclude-reviewed-in instead of declaring no prior reviews"
            )


def _scan_ledgers(root: Path, population: list[dict]) -> list[dict]:
    """Check a declaration of no prior reviews against every label ledger in the root.

    A plain JSON read of each envelope's label, because assessments of any version may be
    present. The scan records each ledger's hash and line count for the loader to re-check.
    """
    folder = root / "assessments"
    scanned = []
    for path in sorted(folder.glob("*/human-labels.jsonl")) if folder.is_dir() else []:
        assessment_id = path.parent.name
        text = read_text(assessment_directory(root, assessment_id) / "human-labels.jsonl")
        lines = text.splitlines(keepends=True)
        _refuse_matching_labels(assessment_id, lines, population)
        scanned.append(
            {
                "assessment_id": assessment_id,
                "ledger_sha256": digest(text),
                "ledger_lines": len(lines),
            }
        )
    return scanned


def _rechecked_scan(root: Path, scan, population: list[dict]) -> list[dict]:
    """A recorded scan still holds: each ledger may have grown, but its prefix is unchanged."""
    keys = {"assessment_id", "ledger_sha256", "ledger_lines"}
    if not isinstance(scan, list) or any(not isinstance(e, dict) or set(e) != keys for e in scan):
        raise ValueError("declared no prior reviews without a recorded ledger scan")
    for entry in scan:
        path = assessment_directory(root, entry["assessment_id"]) / "human-labels.jsonl"
        lines = read_text(path).splitlines(keepends=True)
        count = entry["ledger_lines"]
        if (
            type(count) is not int
            or not 0 <= count <= len(lines)
            or digest("".join(lines[:count])) != entry["ledger_sha256"]
        ):
            raise ValueError(
                f"the label ledger of assessment {entry['assessment_id']}, scanned at creation, "
                "no longer starts with its recorded prefix; ledgers are append-only"
            )
        _refuse_matching_labels(entry["assessment_id"], lines[:count], population)
    return scan


def _derived(cohort: dict, rubric: dict, rubric_text: str, priors: list, labels: list, seed, scan):
    """Every manifest field that follows from the cohort, the rubric and earlier ledgers."""
    purpose, population = _population(cohort, rubric)
    by_id = {record["item_id"]: record for record in population}
    excluded, seen = set(), set()
    for label in (label for group in labels for label in group):
        seen.add(label["payload_sha256"])
        member = by_id.get(label["item_id"])
        if member is not None and digest(member["item"]) != label["payload_sha256"]:
            raise ValueError(
                f"cohort member {label['item_id']} differs from the payload labeled earlier"
            )
        if member is not None:
            excluded.add(label["item_id"])
    # A member under another item ID whose exact content a listed review already labeled.
    twins = {
        r["item_id"]
        for r in population
        if r["item_id"] not in excluded and digest(r["item"]) in seen
    }
    excluded |= twins
    eligible = [record for record in population if record["item_id"] not in excluded]
    if len(eligible) < SELECTION_COUNT:
        raise ValueError(
            f"only {len(eligible)} cohort members remain eligible; "
            f"{SELECTION_COUNT}, 4 per category, are required"
        )
    selected = select_items(eligible, SELECTION_COUNT, seed)
    counts = Counter(by_id[item_id]["category"] for item_id in selected)
    if counts != dict.fromkeys(CATEGORIES, SELECTION_COUNT // len(CATEGORIES)):
        raise ValueError(
            "eligible set cannot give 4 per category: "
            + ", ".join(f"{category} {counts.get(category, 0)}" for category in CATEGORIES)
        )
    settings, summary = cohort["identity"]["settings"], cohort["summary"]
    data = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in population)
    fields = {
        "purpose": purpose,
        "cohort_id": cohort["cohort_id"],
        "cohort_sha256": cohort["sha256"],
        "generator_model": settings["model"],
        "generator_temperature": settings["temperature"],
        "generator_model_identity": settings["model_identity"],
        "generator_model_sha256": settings["model_sha256"],
        "reference_pack_sha256": digest(cohort["identity"]["sources"]),
        "population_ids": [record["item_id"] for record in population],
        "eligibility": {
            "rule": ELIGIBILITY_RULE,
            # Creation needs an explicit choice, so no listed priors means declared none.
            "prior_reviews": "listed" if priors else "declared_none",
            "prior_review_scan": scan,  # Every ledger checked when none is declared.
            "prior_assessments": priors,
            "excluded_ids": [r["item_id"] for r in population if r["item_id"] in excluded],
            "payload_twin_ids": [r["item_id"] for r in population if r["item_id"] in twins],
            "eligible_ids": [record["item_id"] for record in eligible],
        },
        "selected_ids": selected,
        "selection": {
            "algorithm": SELECTION_ALGORITHM,
            "seed": seed,
            "count": SELECTION_COUNT,
            "applied_after_eligibility": True,
        },
        "rubric_version": rubric["version"],
        "rubric_sha256": digest(rubric_text),
        "data_sha256": digest(data),
        "structural_validity": {
            "initial_attempt_valid_count": summary["initial_attempt_valid_count"],
            "planned_slots": summary["planned_slots"],
            "initial_attempt_schema_pass_rate": summary["initial_attempt_schema_pass_rate"],
            "minimum": rubric["structural_validity_minimum"],
        },
    }
    return fields, data


def create_assessment_v2(
    root: Path,
    cohort_id: str,
    assessment_id: str,
    *,
    exclude_reviewed_in=(),
    declare_no_prior_reviews: bool = False,
    seed: str = "mp1-v1",
) -> dict:
    directory = assessment_directory(root, assessment_id)
    if directory.exists() or directory.is_symlink():
        raise FileExistsError(f"assessment {assessment_id} already exists; choose a new ID")
    if isinstance(exclude_reviewed_in, str):
        raise ValueError("exclude_reviewed_in takes a list of assessment IDs")
    prior_ids = list(exclude_reviewed_in)
    if bool(prior_ids) == bool(declare_no_prior_reviews):
        raise ValueError(
            "choose exactly one: list the earlier assessments whose labeled items are "
            "excluded, or declare that there are no prior reviews"
        )
    if len(set(prior_ids)) != len(prior_ids):
        raise ValueError("list each earlier assessment once")
    rubric_text = read_text(Path(__file__).resolve().parents[2] / RUBRIC_V2_PATH)
    rubric = load_rubric_v2(rubric_text)
    cohort = load_cohort(root, cohort_id)
    scan = _scan_ledgers(root, _population(cohort, rubric)[1]) if declare_no_prior_reviews else None
    priors, labels = [], []
    for prior_id in prior_ids:
        record, prior_labels = _prior_record(prior_id, *_earlier_review(root, prior_id))
        priors.append(record)
        labels.append(prior_labels)
    fields, data = _derived(cohort, rubric, rubric_text, priors, labels, seed, scan)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "rubric_schema": RUBRIC_V2_VERSION,
        "source_type": "cohort",
        "assessment_id": assessment_id,
        "created_at": now(),
        **fields,
        "implementation": implementation_identity(),
    }
    manifest["manifest_sha256"] = digest(manifest)
    directory.mkdir(parents=True, exist_ok=False)
    with exclusive(directory):
        for name, text in (("data.jsonl", data), ("rubric.json", rubric_text)):
            with (directory / name).open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
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


def load_assessment_v2(root: Path, assessment_id: str) -> tuple[Path, dict, list[dict], dict]:
    directory = assessment_directory(root, assessment_id)
    manifest = read_json(directory / "manifest.json")
    if not is_v2(manifest) or manifest.get("source_type") != "cohort":
        raise ValueError(
            f"assessment {assessment_id} is not an aec-rubric-v2 cohort assessment; "
            "load D1-D6 assessments with the v1 loader"
        )
    if manifest["assessment_id"] != assessment_id or manifest["manifest_sha256"] != digest(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    ):
        raise ValueError("assessment manifest identity changed")
    rubric_text = read_text(directory / "rubric.json")
    if not digest(rubric_text) == manifest["rubric_sha256"] == RUBRIC_V2_SHA256:
        raise ValueError("assessment rubric differs from the frozen aec-rubric-v2")
    rubric = load_rubric_v2(rubric_text)
    cohort = load_cohort(root, manifest["cohort_id"])
    priors, labels = [], []
    for recorded in manifest["eligibility"]["prior_assessments"]:
        prior_manifest, lines = _earlier_review(root, recorded["assessment_id"])
        count = recorded["ledger_lines"]
        if (
            prior_manifest["manifest_sha256"] != recorded["manifest_sha256"]
            or type(count) is not int
            or not 0 <= count <= len(lines)
            or digest("".join(lines[:count])) != recorded["ledger_sha256"]
        ):
            raise ValueError(
                f"earlier assessment {recorded['assessment_id']} no longer has its recorded "
                "manifest and ledger prefix; ledgers are append-only"
            )
        record, prior_labels = _prior_record(
            recorded["assessment_id"], prior_manifest, lines[:count]
        )
        priors.append(record)
        labels.append(prior_labels)
    scan = None
    if manifest["eligibility"].get("prior_reviews") == "declared_none":
        recorded = manifest["eligibility"].get("prior_review_scan")
        scan = _rechecked_scan(root, recorded, _population(cohort, rubric)[1])
    seed = manifest["selection"]["seed"]
    fields, _ = _derived(cohort, rubric, rubric_text, priors, labels, seed, scan)
    if fields["selected_ids"] != manifest["selected_ids"]:
        raise ValueError("assessment selection changed")
    records = read_records(directory / "data.jsonl")
    if (
        any(manifest.get(key) != value for key, value in fields.items())
        or digest(read_text(directory / "data.jsonl")) != manifest["data_sha256"]
        or records != cohort["summary"]["members"]
    ):
        raise ValueError("assessment content, eligibility or metadata differs from its sources")
    return directory, manifest, records, rubric
