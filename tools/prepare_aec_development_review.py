"""Prepare ten unscored AEC development cases from surplus baseline answers."""

import json
from collections import Counter

from prepare_aec_api_evaluation import ROOT

from aia_mp1.assessment import (
    create_assessment,
    load_assessment,
    read_json,
    save_new,
    select_items,
)
from aia_mp1.cohort import load_cohort
from aia_mp1.gate import _normalized
from aia_mp1.schemas import CATEGORIES, DOMAIN
from aia_mp1.tracing import digest, read_records

REVIEW = "aec-api-development-001"
RUN = "baseline-001-b04"


def prepare_review(root=ROOT):
    if DOMAIN != "aec-course":
        raise ValueError("Set AIA_MP1_DOMAIN=aec-course")
    root = root.resolve()
    cohort = load_cohort(root, "aec-course-baseline")
    summary = cohort["summary"]
    eligible = {
        d["item_id"]
        for d in summary["decisions"]
        if d["run_id"] == RUN and d["reasons"] == ["quota_excess"] and not d["duplicate_of"]
    }
    known = list(summary["members"])
    previous = {}
    for name in ("baseline-cohort-001", "corrected-cohort-001"):
        archived = read_json(root.parent / "cohorts" / name / "manifest.json")
        if archived["sha256"] != digest({k: v for k, v in archived.items() if k != "sha256"}):
            raise ValueError("Archived cohort fingerprint differs")
        previous[name] = archived["sha256"]
        known.extend(archived["summary"]["members"])
    used_questions = {_normalized(r["item"]["question"]) for r in known}
    used_payloads = {digest(r["item"]) for r in known}
    records = read_records(root / RUN / "data.jsonl")
    candidates = {
        r["item_id"]: r
        for r in records
        if r["item_id"] in eligible
        and _normalized(r["item"]["question"]) not in used_questions
        and digest(r["item"]) not in used_payloads
    }
    # Use the existing assessment selector. Seed eligibility depends only on
    # disjointness, category balance and distinct tasks, never on ratings.
    for index in range(10000):
        seed = f"{REVIEW}-{index}"
        ids = select_items(records, 10, seed)
        if (
            set(ids) <= candidates.keys()
            and len({candidates[i]["reference_context"]["task"]["id"] for i in ids}) == 10
        ):
            break
    else:
        raise ValueError("No balanced, disjoint development sample found")
    if Counter(candidates[i]["category"] for i in ids) != {c: 2 for c in CATEGORIES}:
        raise ValueError("Development sample must have two items per category")
    rubric = root / "api-correctness-v1-inputs/rubric.json"
    packet = read_json(root / "api-correctness-v1-inputs/manifest.json")
    if digest(read_json(rubric)) != packet["rubric_sha256"]:
        raise ValueError("Frozen AEC rubric differs")
    directory = root / "assessments" / REVIEW
    if not directory.exists():
        create_assessment(
            root, RUN, REVIEW, rubric, purpose="diagnostic", label_count=10, seed=seed
        )
    _, manifest, _, frozen_rubric = load_assessment(root, REVIEW)
    if (
        manifest["selected_ids"] != ids
        or manifest["assessment_eligible"]
        or frozen_rubric != read_json(rubric)
        or manifest["source_run_id"] != RUN
    ):
        raise ValueError("Existing development assessment differs")
    receipt = {
        "purpose": "Development only. Two quota-surplus items per category, ten distinct tasks.",
        "assessment_sha256": manifest["manifest_sha256"],
        "aec_cohort_sha256": cohort["sha256"],
        "excluded_historical_cohorts": previous,
        "rubric_sha256": packet["rubric_sha256"],
        "selection_seed": seed,
        "selected_ids": ids,
        "eligible_count": len(candidates),
    }
    path = directory / "development-selection.json"
    if not path.exists():
        save_new(path, receipt)
    if read_json(path) != receipt:
        raise ValueError("Development selection receipt differs")
    return receipt


if __name__ == "__main__":
    print(json.dumps(prepare_review(), indent=2))
