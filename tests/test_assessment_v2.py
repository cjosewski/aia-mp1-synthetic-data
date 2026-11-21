"""v2 assessments: eligibility after earlier reviews, frozen selection and full re-verification."""

import json
from collections import Counter

import pytest
from v2_fixtures import (
    REPO,
    REVIEWER,
    RUBRIC_V2,
    OffsetClient,
    build_cohort,
    decisions,
    resign_ledger,
    v2_config,
)

from aia_mp1 import assessment_v2
from aia_mp1.assessment import (
    create_assessment,
    create_cohort_assessment,
    load_assessment,
    read_json,
    select_items,
)
from aia_mp1.assessment_v2 import create_assessment_v2, load_assessment_v2
from aia_mp1.cohort import load_cohort
from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.labels import load_labels, record_label
from aia_mp1.labels_v2 import record_label_v2
from aia_mp1.rubric_v2 import RUBRIC_V2_SHA256
from aia_mp1.schemas import CATEGORIES
from aia_mp1.tracing import digest

V1_RUBRIC = REPO / "config/rubric.json"


@pytest.fixture
def cohort(tmp_path):
    return build_cohort(v2_config(tmp_path), "arm-a", "cohort-a")


def label_v1(root, assessment_id, item_ids):
    for item_id in item_ids:
        record_label(
            root, assessment_id, item_id, dict.fromkeys(DIMENSIONS, 1), REVIEWER, notes="v1"
        )


@pytest.fixture
def reviewed(cohort):
    """Twenty items of the cohort already carry D1-D6 labels in a v1 assessment."""
    prior = create_cohort_assessment(cohort, "cohort-a", "v1-prior", V1_RUBRIC)
    label_v1(cohort, "v1-prior", prior["selected_ids"])
    return cohort, prior


def test_worked_example_excludes_reviewed_items_and_selects_deterministically(reviewed):
    root, prior = reviewed
    members = load_cohort(root, "cohort-a")["summary"]["members"]
    manifest = create_assessment_v2(root, "cohort-a", "v2", exclude_reviewed_in=("v1-prior",))
    eligibility = manifest["eligibility"]
    assert eligibility["rule"] == "exclude-human-labeled-v1"
    assert sorted(eligibility["excluded_ids"]) == sorted(prior["selected_ids"])
    assert eligibility["eligible_ids"] == [
        r["item_id"] for r in members if r["item_id"] not in prior["selected_ids"]
    ]
    assert len(eligibility["eligible_ids"]) == 30
    [record] = eligibility["prior_assessments"]
    ledger = (root / "assessments/v1-prior/human-labels.jsonl").read_text()
    assert record == {
        "assessment_id": "v1-prior",
        "manifest_sha256": prior["manifest_sha256"],
        "ledger_sha256": digest(ledger),
        "ledger_lines": 20,
        "labeled_item_ids": prior["selected_ids"],
    }
    selected = manifest["selected_ids"]
    by_id = {r["item_id"]: r for r in members}
    assert Counter(by_id[i]["category"] for i in selected) == dict.fromkeys(CATEGORIES, 4)
    assert not set(selected) & set(prior["selected_ids"])
    assert selected == select_items([by_id[i] for i in eligibility["eligible_ids"]], 20, "mp1-v1")
    assert manifest["selection"]["applied_after_eligibility"] is True
    again = create_assessment_v2(root, "cohort-a", "v2-again", exclude_reviewed_in=("v1-prior",))
    assert again["selected_ids"] == selected
    directory, loaded, records, rubric = load_assessment_v2(root, "v2")
    assert loaded == manifest and records == members
    assert (manifest["schema_version"], manifest["rubric_schema"]) == ("v2-1", "aec-rubric-v2")
    assert (
        manifest["rubric_sha256"]
        == RUBRIC_V2_SHA256
        == digest((directory / "rubric.json").read_text())
    )
    assert (directory / "human-labels.jsonl").read_text() == ""
    assert rubric["version"] == "aec-rubric-v2"


def test_v2_prior_is_loaded_with_the_v2_loader(cohort):
    first = create_assessment_v2(cohort, "cohort-a", "first", declare_no_prior_reviews=True)
    for item_id in first["selected_ids"][:3]:
        record_label_v2(cohort, "first", item_id, decisions(), REVIEWER, review_stage="blind")
    second = create_assessment_v2(cohort, "cohort-a", "second", exclude_reviewed_in=("first",))
    assert set(second["eligibility"]["excluded_ids"]) == set(first["selected_ids"][:3])
    assert len(second["eligibility"]["eligible_ids"]) == 47
    load_assessment_v2(cohort, "second")


@pytest.mark.parametrize(
    "name, message",
    [("data.jsonl", "content"), ("rubric.json", "rubric"), ("manifest.json", "identity")],
)
def test_tampered_snapshot_is_refused(reviewed, name, message):
    root, _ = reviewed
    create_assessment_v2(root, "cohort-a", "v2", exclude_reviewed_in=("v1-prior",))
    path = root / "assessments/v2" / name
    text = path.read_text()
    changed = {
        "data.jsonl": text.replace("Synthetic", "Changed", 1),
        "rubric.json": text[:-1] + " ",
        "manifest.json": text.replace('"purpose": "baseline"', '"purpose": "corrected"'),
    }[name]
    assert changed != text
    path.write_text(changed)
    with pytest.raises(ValueError, match=message):
        load_assessment_v2(root, "v2")


def test_resigned_manifest_with_another_selection_is_refused(reviewed):
    root, prior = reviewed
    create_assessment_v2(root, "cohort-a", "v2", exclude_reviewed_in=("v1-prior",))
    path = root / "assessments/v2/manifest.json"
    manifest = read_json(path)
    manifest["selected_ids"] = prior["selected_ids"]
    manifest["manifest_sha256"] = digest(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    )
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="selection"):
        load_assessment_v2(root, "v2")


def test_rewritten_prior_ledger_prefix_is_refused(reviewed):
    root, _ = reviewed
    create_assessment_v2(root, "cohort-a", "v2", exclude_reviewed_in=("v1-prior",))
    prior_directory = root / "assessments/v1-prior"
    resign_ledger(prior_directory, lambda label: label.update(notes="rewritten later"))
    _, manifest, records, _ = load_assessment(root, "v1-prior")
    load_labels(prior_directory, manifest, records)  # The rewrite is internally consistent.
    with pytest.raises(ValueError, match="prefix"):
        load_assessment_v2(root, "v2")


def test_appending_to_a_prior_ledger_keeps_the_assessment_valid(reviewed):
    root, prior = reviewed
    created = create_assessment_v2(root, "cohort-a", "v2", exclude_reviewed_in=("v1-prior",))
    effective = load_labels(*load_assessment(root, "v1-prior")[:3])
    item_id = prior["selected_ids"][0]
    record_label(
        root,
        "v1-prior",
        item_id,
        dict.fromkeys(DIMENSIONS, 0),
        REVIEWER,
        supersedes=effective[item_id]["label_id"],
    )
    assert load_assessment_v2(root, "v2")[1] == created


def test_payload_hash_mismatch_with_an_earlier_label_is_refused(reviewed, monkeypatch):
    root, prior = reviewed
    changed_id = prior["selected_ids"][0]

    def changed_cohort(*args):
        cohort = load_cohort(*args)
        for member in cohort["summary"]["members"]:
            if member["item_id"] == changed_id:
                member["item"]["tips"] = ["A different synthetic tip than the one reviewed."]
        return cohort

    monkeypatch.setattr(assessment_v2, "load_cohort", changed_cohort)
    with pytest.raises(ValueError, match="payload"):
        create_assessment_v2(root, "cohort-a", "v2", exclude_reviewed_in=("v1-prior",))
    assert not (root / "assessments/v2").exists()


def test_existing_directory_and_repository_root_are_refused(cohort):
    create_assessment_v2(cohort, "cohort-a", "v2", declare_no_prior_reviews=True)
    before = (cohort / "assessments/v2/manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        create_assessment_v2(cohort, "cohort-a", "v2", declare_no_prior_reviews=True)
    assert (cohort / "assessments/v2/manifest.json").read_bytes() == before
    with pytest.raises(ValueError, match="outside the repository"):
        create_assessment_v2(
            REPO / "v2-evidence-must-not-exist", "cohort-a", "v2", declare_no_prior_reviews=True
        )
    assert not (REPO / "v2-evidence-must-not-exist").exists()


def test_unbalanced_eligible_set_is_refused(cohort):
    create_assessment(
        cohort, "arm-a-b01", "diagnostic", V1_RUBRIC, purpose="diagnostic", label_count=50
    )
    members = load_cohort(cohort, "cohort-a")["summary"]["members"]
    label_v1(
        cohort, "diagnostic", [r["item_id"] for r in members if r["category"] == "cad_apis"][:7]
    )
    with pytest.raises(ValueError, match="4 per category"):
        create_assessment_v2(cohort, "cohort-a", "v2", exclude_reviewed_in=("diagnostic",))
    assert not (cohort / "assessments/v2").exists()


def test_duplicate_or_missing_prior_assessment_is_refused(reviewed):
    root, _ = reviewed
    with pytest.raises(ValueError, match="once"):
        create_assessment_v2(root, "cohort-a", "v2", exclude_reviewed_in=("v1-prior", "v1-prior"))
    with pytest.raises(OSError):
        create_assessment_v2(root, "cohort-a", "v2", exclude_reviewed_in=("never-created",))
    assert not (root / "assessments/v2").exists()


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda s, i: s.update(members=s["members"][:49]), "50"),
        (lambda s, i: s.update(initial_attempt_valid_count=s["planned_slots"] * 94 // 100), "95"),
        (lambda s, i: i["settings"].update(domain="home-diy"), "domain"),
        (lambda s, i: i["settings"].update(purpose="smoke"), "purpose"),
    ],
)
def test_cohort_requirements_are_enforced(cohort, monkeypatch, change, message):
    def changed_cohort(*args):
        value = load_cohort(*args)
        change(value["summary"], value["identity"])
        return value

    monkeypatch.setattr(assessment_v2, "load_cohort", changed_cohort)
    with pytest.raises(ValueError, match=message):
        create_assessment_v2(cohort, "cohort-a", "v2", declare_no_prior_reviews=True)
    assert not (cohort / "assessments/v2").exists()


def test_prior_reviews_are_listed_or_explicitly_declared_absent(cohort):
    for choice in ({}, {"exclude_reviewed_in": ("first",), "declare_no_prior_reviews": True}):
        with pytest.raises(ValueError, match="no prior reviews"):
            create_assessment_v2(cohort, "cohort-a", "v2", **choice)
    assert not (cohort / "assessments/v2").exists()
    declared = create_assessment_v2(cohort, "cohort-a", "declared", declare_no_prior_reviews=True)
    listed = create_assessment_v2(cohort, "cohort-a", "listed", exclude_reviewed_in=["declared"])
    assert declared["eligibility"]["prior_reviews"] == "declared_none"
    assert declared["eligibility"]["prior_review_scan"] == []
    assert listed["eligibility"]["prior_reviews"] == "listed"
    assert listed["eligibility"]["prior_review_scan"] is None
    path = cohort / "assessments/declared/manifest.json"
    manifest = read_json(path)
    manifest["eligibility"]["prior_reviews"] = "listed"
    manifest["eligibility"]["prior_review_scan"] = None  # Consistent with "listed".
    manifest["manifest_sha256"] = digest(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    )
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="eligibility"):
        load_assessment_v2(cohort, "declared")


def resigned(path, change):
    manifest = read_json(path)
    change(manifest)
    manifest["manifest_sha256"] = digest(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    )
    path.write_text(json.dumps(manifest))


def test_a_scan_entry_with_an_extra_key_is_refused(cohort):
    create_assessment_v2(cohort, "cohort-a", "first", declare_no_prior_reviews=True)
    second = create_assessment_v2(cohort, "cohort-a", "second", declare_no_prior_reviews=True)
    assert [e["assessment_id"] for e in second["eligibility"]["prior_review_scan"]] == ["first"]
    resigned(
        cohort / "assessments/second/manifest.json",
        lambda m: m["eligibility"]["prior_review_scan"][0].update(note="added later"),
    )
    with pytest.raises(ValueError, match="recorded ledger scan"):
        load_assessment_v2(cohort, "second")


def payload_twins(tmp_path):
    """cohort-b repeats cohort-a's payloads slot by slot; one cohort-b item is labeled."""
    config = v2_config(tmp_path)
    root = build_cohort(config, "arm-a", "cohort-a")
    build_cohort(config, "arm-b", "cohort-b", purpose="corrected")
    other = create_assessment_v2(root, "cohort-b", "other", declare_no_prior_reviews=True)
    labeled = other["selected_ids"][0]
    record_label_v2(root, "other", labeled, decisions(), REVIEWER)
    payload = next(
        digest(r["item"]) for r in load_assessment_v2(root, "other")[2] if r["item_id"] == labeled
    )
    members = load_cohort(root, "cohort-a")["summary"]["members"]
    twin = next(r["item_id"] for r in members if digest(r["item"]) == payload)
    return root, labeled, twin


def test_listing_a_prior_review_also_excludes_its_payload_twins(tmp_path):
    root, labeled, twin = payload_twins(tmp_path)
    created = create_assessment_v2(root, "cohort-a", "v2", exclude_reviewed_in=["other"])
    eligibility = created["eligibility"]
    assert eligibility["payload_twin_ids"] == [twin] and eligibility["excluded_ids"] == [twin]
    assert twin not in eligibility["eligible_ids"] and twin not in created["selected_ids"]
    assert load_assessment_v2(root, "v2")[1] == created
    resigned(
        root / "assessments/v2/manifest.json",
        lambda m: m["eligibility"].update(payload_twin_ids=[]),
    )
    with pytest.raises(ValueError, match="eligibility"):
        load_assessment_v2(root, "v2")


def test_a_payload_match_names_the_prior_item_and_its_twin(tmp_path):
    root, labeled, twin = payload_twins(tmp_path)
    with pytest.raises(ValueError) as refused:
        create_assessment_v2(root, "cohort-a", "v2", declare_no_prior_reviews=True)
    message = str(refused.value)
    assert f"assessment other already labeled {labeled}" in message
    assert f"payload equals cohort member {twin}" in message
    assert "--exclude-reviewed-in" in message and "a member of this cohort" not in message


def test_declaring_no_prior_reviews_is_checked_against_every_ledger(reviewed):
    root, _ = reviewed
    with pytest.raises(ValueError, match="v1-prior .*--exclude-reviewed-in"):
        create_assessment_v2(root, "cohort-a", "v2", declare_no_prior_reviews=True)
    assert not (root / "assessments/v2").exists()


def test_the_declared_scan_matches_payloads_and_is_rechecked_on_load(tmp_path):
    config = v2_config(tmp_path)
    root = build_cohort(config, "arm-a", "cohort-a")
    build_cohort(config, "arm-b", "cohort-b", purpose="corrected")  # Same payloads per slot.
    build_cohort(config, "arm-c", "cohort-c", client=OffsetClient(100), purpose="corrected")
    other = create_assessment_v2(root, "cohort-b", "other", declare_no_prior_reviews=True)
    record_label_v2(root, "other", other["selected_ids"][0], decisions(), REVIEWER)
    with pytest.raises(ValueError, match="other .*--exclude-reviewed-in"):
        create_assessment_v2(root, "cohort-a", "v2", declare_no_prior_reviews=True)
    created = create_assessment_v2(root, "cohort-c", "v2", declare_no_prior_reviews=True)
    ledger = root / "assessments/other/human-labels.jsonl"
    assert created["eligibility"]["prior_review_scan"] == [
        {"assessment_id": "other", "ledger_sha256": digest(ledger.read_text()), "ledger_lines": 1}
    ]
    record_label_v2(root, "other", other["selected_ids"][1], decisions(), REVIEWER)
    assert load_assessment_v2(root, "v2")[1] == created  # A scanned ledger may grow.
    resign_ledger(root / "assessments/other", lambda label: label.update(notes="rewritten"))
    with pytest.raises(ValueError, match="prefix"):
        load_assessment_v2(root, "v2")


def test_a_rescanned_prefix_must_still_hold_no_matching_label(tmp_path):
    config = v2_config(tmp_path)
    root = build_cohort(config, "arm-c", "cohort-c", client=OffsetClient(100))
    created = create_assessment_v2(root, "cohort-c", "v2", declare_no_prior_reviews=True)
    later = create_assessment_v2(root, "cohort-c", "later", exclude_reviewed_in=["v2"])
    record_label_v2(root, "later", later["selected_ids"][0], decisions(), REVIEWER)
    path = root / "assessments/v2/manifest.json"
    manifest = read_json(path)
    ledger = (root / "assessments/later/human-labels.jsonl").read_text()
    manifest["eligibility"]["prior_review_scan"] = [
        {"assessment_id": "later", "ledger_sha256": digest(ledger), "ledger_lines": 1}
    ]
    manifest["manifest_sha256"] = digest(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    )
    path.write_text(json.dumps(manifest))
    assert created["eligibility"]["prior_review_scan"] == []
    with pytest.raises(ValueError, match="later .*--exclude-reviewed-in"):
        load_assessment_v2(root, "v2")


@pytest.mark.parametrize("valid", [95, 94])
def test_validity_of_exactly_95_percent_is_enough(cohort, monkeypatch, valid):
    def changed_cohort(*args):
        value = load_cohort(*args)
        value["summary"].update(planned_slots=100, initial_attempt_valid_count=valid)
        return value

    monkeypatch.setattr(assessment_v2, "load_cohort", changed_cohort)
    if valid == 95:
        created = create_assessment_v2(cohort, "cohort-a", "v2", declare_no_prior_reviews=True)
        assert created["structural_validity"]["initial_attempt_valid_count"] == 95
    else:
        with pytest.raises(ValueError, match="0.95"):
            create_assessment_v2(cohort, "cohort-a", "v2", declare_no_prior_reviews=True)


def test_v1_and_v2_loaders_refuse_each_others_directories(reviewed):
    root, prior = reviewed
    create_assessment_v2(root, "cohort-a", "v2", exclude_reviewed_in=["v1-prior"])
    directory, manifest, records, rubric = load_assessment(root, "v1-prior")
    assert manifest == prior and len(load_labels(directory, manifest, records)) == 20
    assert [d["id"] for d in rubric["dimensions"]] == list(DIMENSIONS)
    with pytest.raises(ValueError, match="v1 loader"):
        load_assessment_v2(root, "v1-prior")
    with pytest.raises(ValueError, match="D1-D6"):
        load_assessment(root, "v2")
    assert (root / "assessments/v2/rubric.json").read_bytes() == RUBRIC_V2.read_bytes()
