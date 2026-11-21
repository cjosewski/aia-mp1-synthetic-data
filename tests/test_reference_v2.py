"""v2 blind references: freeze preconditions, the frozen prefix and withdrawal from scoring."""

import json
import shutil

import pytest
from v2_fixtures import REVIEWER, build_cohort, decisions, v2_config

from aia_mp1.assessment_v2 import create_assessment_v2, load_assessment_v2
from aia_mp1.labels_v2 import load_labels_v2, record_label_v2
from aia_mp1.reference_v2 import freeze_reference_v2, load_reference_v2
from aia_mp1.tracing import digest


@pytest.fixture
def assessment(tmp_path):
    root = build_cohort(v2_config(tmp_path), "arm-a", "cohort-a")
    return root, create_assessment_v2(root, "cohort-a", "v2", declare_no_prior_reviews=True)


@pytest.fixture
def frozen(assessment):
    root, manifest = assessment
    for item in manifest["selected_ids"]:
        record_label_v2(root, "v2", item, decisions(), REVIEWER, review_stage="blind")
    return root, manifest, freeze_reference_v2(root, "v2", REVIEWER, declare_blind=True)


def test_freeze_requires_complete_blind_single_reviewer_labels_and_no_judges(assessment):
    root, manifest = assessment
    directory = root / "assessments/v2"
    *first, last = manifest["selected_ids"]
    for item in first:
        record_label_v2(root, "v2", item, decisions(), REVIEWER, review_stage="blind")
    with pytest.raises(ValueError, match="20"):
        freeze_reference_v2(root, "v2", REVIEWER, declare_blind=True)
    unknown = record_label_v2(root, "v2", last, decisions(), REVIEWER)
    with pytest.raises(ValueError, match="blind"):
        freeze_reference_v2(root, "v2", REVIEWER, declare_blind=True)
    other = record_label_v2(
        root,
        "v2",
        last,
        decisions(),
        "Another synthetic reviewer",
        supersedes=unknown["label_id"],
        review_stage="blind",
    )
    with pytest.raises(ValueError, match="reviewer"):
        freeze_reference_v2(root, "v2", REVIEWER, declare_blind=True)
    record_label_v2(
        root, "v2", last, decisions(), REVIEWER, supersedes=other["label_id"], review_stage="blind"
    )
    with pytest.raises(ValueError, match="declare"):
        freeze_reference_v2(root, "v2", REVIEWER, declare_blind=False)
    (directory / "judges/synthetic").mkdir(parents=True)
    with pytest.raises(ValueError, match="judge"):
        freeze_reference_v2(root, "v2", REVIEWER, declare_blind=True)
    shutil.rmtree(directory / "judges")
    assert not (directory / "human-reference.json").exists()
    reference = freeze_reference_v2(root, "v2", REVIEWER, declare_blind=True)
    loaded = load_assessment_v2(root, "v2")
    assert reference["labels"] == load_labels_v2(*loaded[:3])
    assert reference["ledger_prefix_lines"] == 22 and reference["packet_ids"] == []
    assert load_reference_v2(*loaded[:3], for_scoring=True) == reference
    with pytest.raises(FileExistsError):
        freeze_reference_v2(root, "v2", REVIEWER, declare_blind=True)


def forge(directory, reference, **changes):
    forged = reference | changes
    forged["sha256"] = digest({k: v for k, v in forged.items() if k != "sha256"})
    (directory / "human-reference.json").write_text(json.dumps(forged))


def test_post_freeze_amendment_never_enters_the_reference(frozen):
    root, manifest, reference = frozen
    directory, loaded, records, _ = load_assessment_v2(root, "v2")
    item = manifest["selected_ids"][0]
    amendment = record_label_v2(
        root,
        "v2",
        item,
        decisions(tips=0),
        REVIEWER,
        supersedes=reference["labels"][item]["label_id"],
    )
    assert load_reference_v2(directory, loaded, records, for_scoring=True) == reference
    ledger = (directory / "human-labels.jsonl").read_text()
    forge(
        directory,
        reference,
        ledger_prefix_lines=21,
        ledger_prefix_sha256=digest(ledger),
        labels=reference["labels"] | {item: amendment},
    )
    with pytest.raises(ValueError, match="prefix"):
        load_reference_v2(directory, loaded, records)


@pytest.mark.parametrize(
    "change",
    [
        {"ledger_prefix_lines": 19},
        {"ledger_prefix_lines": 40},
        {"ledger_prefix_sha256": "0" * 64},
        {"packet_ids": ["packet-x"]},
    ],
)
def test_tampered_reference_is_refused(frozen, change):
    root, _, reference = frozen
    directory, loaded, records, _ = load_assessment_v2(root, "v2")
    forge(directory, reference, **change)
    with pytest.raises(ValueError, match="prefix"):
        load_reference_v2(directory, loaded, records)
    unsigned = reference | change
    (directory / "human-reference.json").write_text(json.dumps(unsigned))
    with pytest.raises(ValueError, match="prefix"):
        load_reference_v2(directory, loaded, records)


def test_resigned_reference_with_one_changed_decision_is_refused(frozen):
    root, manifest, reference = frozen
    directory, loaded, records, _ = load_assessment_v2(root, "v2")
    labels = json.loads(json.dumps(reference["labels"]))
    labels[manifest["selected_ids"][0]]["decisions"]["tips"] = 0
    forge(directory, reference, labels=labels)
    with pytest.raises(ValueError, match="prefix"):
        load_reference_v2(directory, loaded, records)


def test_withdrawal_refuses_scoring_but_keeps_the_record(frozen):
    root, _, reference = frozen
    directory, loaded, records, _ = load_assessment_v2(root, "v2")
    notice = directory / "human-reference-withdrawal.json"
    notice.write_text(json.dumps({"human_reference_sha256": "0" * 64, "reason": "Synthetic"}))
    with pytest.raises(ValueError, match="does not match"):
        load_reference_v2(directory, loaded, records, for_scoring=True)
    notice.write_text(
        json.dumps({"human_reference_sha256": reference["sha256"], "reason": "Synthetic exposure"})
    )
    with pytest.raises(ValueError, match="withdrawn from scoring: Synthetic exposure"):
        load_reference_v2(directory, loaded, records, for_scoring=True)
    assert load_reference_v2(directory, loaded, records) == reference
