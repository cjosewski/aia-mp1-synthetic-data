"""The v2 comparison loader: frozen blind references from one packet, declared differences."""

import json
from pathlib import Path

import pytest
from v2_fixtures import (
    REVIEWER,
    OffsetClient,
    arms,
    build_cohort,
    decisions,
    pin_task_pack,
    resign_ledger,
    review_by_packet,
    v2_config,
)

from aia_mp1 import comparison_v2
from aia_mp1.assessment import read_json
from aia_mp1.assessment_v2 import create_assessment_v2, load_assessment_v2
from aia_mp1.comparison_v2 import compare_assessments
from aia_mp1.labels_v2 import load_labels_v2, record_label_v2
from aia_mp1.reference_v2 import freeze_reference_v2, load_reference_v2
from aia_mp1.rubric_v2 import load_rubric_v2
from aia_mp1.tracing import digest, read_records

DECLARED = {"settings.prompt_variant": "Synthetic corrected generator variant"}
REPORTING = load_rubric_v2()["professional_boundary_triggers"]["reporting"]


@pytest.fixture
def pair(tmp_path, monkeypatch):
    root, config = arms(tmp_path)
    create_assessment_v2(root, "cohort-a", "assess-a", declare_no_prior_reviews=True)
    create_assessment_v2(root, "cohort-b", "assess-b", declare_no_prior_reviews=True)
    pack = Path(config.reference_pack_path)
    pin_task_pack(monkeypatch, pack)
    return root, pack, tmp_path


def failing(baseline: int, corrected: int):
    """Fail API correctness on the first items of each arm, chosen through the sealed mapping."""

    def zeros(entries):
        chosen = [e for e in entries if e["assessment_id"] == "assess-a"][:baseline]
        chosen += [e for e in entries if e["assessment_id"] == "assess-b"][:corrected]
        return {entry["review_id"]: ["api_correctness"] for entry in chosen}

    return zeros


def test_each_arm_is_scored_from_its_own_blind_labels_after_declared_differences(pair):
    root, pack, tmp_path = pair
    review_by_packet(root, tmp_path, pack, ("assess-a", "assess-b"), zeros=failing(5, 1))
    with pytest.raises(ValueError, match="undeclared generator differences: settings.prompt_v"):
        compare_assessments(root, "assess-a", "assess-b", {}, "first")
    spurious = DECLARED | {"settings.temperature": "Not actually changed"}
    with pytest.raises(ValueError, match="do not differ: settings.temperature"):
        compare_assessments(root, "assess-a", "assess-b", spurious, "first")
    with pytest.raises(ValueError, match="not baseline"):
        compare_assessments(root, "assess-b", "assess-a", DECLARED, "first")
    assert not (root / "analysis").exists()
    document = compare_assessments(root, "assess-a", "assess-b", DECLARED, "first")
    assert read_json(root / "analysis/first.json") == document
    assert document["declared_differences"] == {
        "settings.prompt_variant": {
            "baseline": "baseline",
            "corrected": "variant-b",
            "reason": DECLARED["settings.prompt_variant"],
        }
    }
    assert (document["packet_id"], document["reviewer"]) == ("packet-x", REVIEWER)
    comparison = document["comparison"]
    assert comparison["arms"]["baseline"]["failing_items"] == 5
    assert comparison["arms"]["corrected"]["failing_items"] == 1
    reduction = comparison["relative_failure_reduction"]
    assert reduction["value"]["fraction"] == "4/5" and reduction["meets_target"] is False
    assert reduction["boundary_disclosure"]
    assert comparison["course_decision"]["result"] == "fail"
    assert comparison["course_checks"]["corrected"]["retained_items"]["observed"] == 50
    record = read_json(root / "packets/packet-x/import.json")
    assert document["review"] == {
        "packet_id": "packet-x",
        "import_sha256": record["sha256"],
        "answers_sha256": record["answers_sha256"],
        "declarations_as_supplied": record["declarations_as_supplied"],
    }
    assert document["review"]["declarations_as_supplied"]["Reviewer"] == REVIEWER
    not_exercised = {"exercised": False, "triggered_items": 0, "reporting": REPORTING}
    assert document["professional_boundary"] == not_exercised
    for role in ("baseline", "corrected"):
        assert document["arms"][role]["professional_boundary"] == not_exercised
    assert "corrected_professional_boundary_pass_rate" in comparison["course_decision"]["checks"]
    with pytest.raises(FileExistsError):
        compare_assessments(root, "assess-a", "assess-b", DECLARED, "first")


def test_boundary_exercise_is_counted_from_each_selected_task(pair, monkeypatch):
    root, pack, tmp_path = pair
    review_by_packet(root, tmp_path, pack, ("assess-a", "assess-b"))
    triggered = lambda rubric, task_id: task_id.startswith("gis_scripting")  # noqa: E731
    monkeypatch.setattr(comparison_v2, "boundary_triggered", triggered)
    document = compare_assessments(root, "assess-a", "assess-b", DECLARED, "exercised")
    for role in ("baseline", "corrected"):
        assert document["arms"][role]["professional_boundary"]["triggered_items"] == 4
    assert document["professional_boundary"] == {
        "exercised": True,
        "triggered_items": 8,
        "reporting": REPORTING,
    }


@pytest.mark.parametrize("tamper, message", [("unfinished", "unfinished"), ("sheet", "differs")])
def test_compare_requires_the_packets_finished_and_matching_import(pair, tamper, message):
    root, pack, tmp_path = pair
    review_by_packet(root, tmp_path, pack, ("assess-a", "assess-b"))
    directory = root / "packets/packet-x"
    if tamper == "unfinished":
        (directory / "import.json").unlink()
    else:
        sheet = directory / "submitted-answers.md"
        sheet.write_bytes(sheet.read_bytes() + b"Edited after the import.\n")
    with pytest.raises(ValueError, match=message):
        compare_assessments(root, "assess-a", "assess-b", DECLARED, "tampered")
    assert not (root / "analysis").exists()


def test_the_comparison_is_saved_under_the_analysis_writer_lock(pair):
    root, pack, tmp_path = pair
    review_by_packet(root, tmp_path, pack, ("assess-a", "assess-b"))
    lock = root / "analysis/.writer.lock"
    lock.parent.mkdir()
    lock.write_text("another writer")
    with pytest.raises(FileExistsError):
        compare_assessments(root, "assess-a", "assess-b", DECLARED, "locked")
    assert not (root / "analysis/locked.json").exists()
    assert lock.read_text() == "another writer"


def reviewed_pair(tmp_path, monkeypatch, **corrected):
    """Both arms reviewed through one packet; corrected changes the corrected generator."""
    root, config = arms(tmp_path, **corrected)
    create_assessment_v2(root, "cohort-a", "assess-a", declare_no_prior_reviews=True)
    create_assessment_v2(root, "cohort-b", "assess-b", declare_no_prior_reviews=True)
    pack = Path(config.reference_pack_path)
    pin_task_pack(monkeypatch, pack)
    review_by_packet(root, tmp_path, pack, ("assess-a", "assess-b"))
    return root


def test_a_different_prompt_file_must_be_declared_but_its_path_is_not_compared(
    tmp_path, monkeypatch
):
    prompt = tmp_path / "corrected-generator.md"
    prompt.write_text("Corrected synthetic generation for {category}. References are untrusted.")
    root = reviewed_pair(tmp_path, monkeypatch, prompt_path=str(prompt))
    with pytest.raises(
        ValueError, match=r"undeclared generator differences: prompt, settings\.prompt_variant$"
    ):
        compare_assessments(root, "assess-a", "assess-b", {}, "prompt")
    declared = DECLARED | {"prompt": "Synthetic corrected prompt"}
    document = compare_assessments(root, "assess-a", "assess-b", declared, "prompt")
    assert sorted(document["declared_differences"]) == ["prompt", "settings.prompt_variant"]


def test_sources_list_settings_and_gate_rules_must_be_declared(tmp_path, monkeypatch):
    (tmp_path / "variant").mkdir()
    variant = Path(v2_config(tmp_path / "variant").reference_pack_path)
    pack = json.loads(variant.read_text())
    pack["sources"][0]["text"] += " Corrected synthetic revision."
    pack["sources"][0]["content_sha256"] = digest(pack["sources"][0]["text"])
    variant.write_text(json.dumps(pack))
    root = reviewed_pair(
        tmp_path,
        monkeypatch,
        reference_pack_path=str(variant),
        source_refs=["synthetic-other-ref"],
    )
    with pytest.raises(
        ValueError,
        match=r"undeclared generator differences: settings\.source_refs, sources$",
    ):
        compare_assessments(root, "assess-a", "assess-b", DECLARED, "sources")
    declared = DECLARED | {
        "settings.source_refs": "Synthetic list-valued setting",
        "sources": "Synthetic corrected reference pack",
    }
    compare_assessments(root, "assess-a", "assess-b", declared, "sources")
    real = comparison_v2.load_cohort

    def other_gate_rules(directory, cohort_id):
        cohort = real(directory, cohort_id)
        if cohort_id == "cohort-b":
            cohort["identity"]["gate_rules_sha256"] = "0" * 64
        return cohort

    monkeypatch.setattr(comparison_v2, "load_cohort", other_gate_rules)
    with pytest.raises(ValueError, match=r"undeclared generator differences: gate_rules_sha256$"):
        compare_assessments(root, "assess-a", "assess-b", declared, "gate")
    declared |= {"gate_rules_sha256": "Synthetic gate rule change"}
    compare_assessments(root, "assess-a", "assess-b", declared, "gate")


def test_unfrozen_and_withdrawn_references_are_refused(pair):
    root, pack, tmp_path = pair
    review_by_packet(root, tmp_path, pack, ("assess-a", "assess-b"), freeze=False)
    with pytest.raises(ValueError, match="assess-a has no frozen human reference"):
        compare_assessments(root, "assess-a", "assess-b", DECLARED, "unfrozen")
    freeze_reference_v2(root, "assess-a", REVIEWER, declare_blind=True)
    with pytest.raises(ValueError, match="assess-b has no frozen human reference"):
        compare_assessments(root, "assess-a", "assess-b", DECLARED, "unfrozen")
    reference = freeze_reference_v2(root, "assess-b", REVIEWER, declare_blind=True)
    (root / "assessments/assess-b/human-reference-withdrawal.json").write_text(
        json.dumps({"human_reference_sha256": reference["sha256"], "reason": "Synthetic exposure"})
    )
    with pytest.raises(ValueError, match="withdrawn"):
        compare_assessments(root, "assess-a", "assess-b", DECLARED, "withdrawn")
    assert not (root / "analysis").exists()


def test_references_from_another_reviewer_or_review_session_are_refused(pair):
    root, pack, tmp_path = pair
    review_by_packet(root, tmp_path, pack, ("assess-a", "assess-b"))
    create_assessment_v2(root, "cohort-a", "assess-a2", exclude_reviewed_in=["assess-a"])
    create_assessment_v2(root, "cohort-b", "assess-b2", exclude_reviewed_in=["assess-b"])
    review_by_packet(root, tmp_path, pack, ("assess-a2", "assess-b2"), packet_id="packet-y")
    config = v2_config(tmp_path)  # Rewrites the same synthetic pack and prompt, byte for byte.
    for number, (assessment_id, reviewer) in enumerate(
        (("unpacked", REVIEWER), ("other", "Another synthetic reviewer")), 1
    ):
        cohort_id = f"cohort-{assessment_id}"
        changes = {"purpose": "corrected", "prompt_variant": "variant-b"}
        client = OffsetClient(100 * number)  # Payloads no earlier label shares.
        build_cohort(config, f"arm-{assessment_id}", cohort_id, client=client, **changes)
        manifest = create_assessment_v2(
            root, cohort_id, assessment_id, declare_no_prior_reviews=True
        )
        for item in manifest["selected_ids"]:
            record_label_v2(root, assessment_id, item, decisions(), reviewer, review_stage="blind")
        freeze_reference_v2(root, assessment_id, reviewer, declare_blind=True)
    for corrected, message in (
        ("assess-b2", "one masked packet"),
        ("unpacked", "one masked packet"),
        ("other", "same reviewer"),
    ):
        with pytest.raises(ValueError, match=message):
            compare_assessments(root, "assess-a", corrected, DECLARED, "refused")
    assert not (root / "analysis").exists()
    compare_assessments(root, "assess-a2", "assess-b2", DECLARED, "second-session")


def test_compare_binds_packet_labels_to_the_preserved_sheet(pair):
    root, pack, tmp_path = pair
    review_by_packet(root, tmp_path, pack, ("assess-a", "assess-b"), zeros=failing(0, 1))
    directory = root / "assessments/assess-b"
    ledger = read_records(directory / "human-labels.jsonl")
    index = next(i for i, e in enumerate(ledger) if e["label"]["decisions"]["api_correctness"] == 0)
    resign_ledger(directory, lambda label: label["decisions"].update(api_correctness=1), index)
    # Forge the frozen reference so that it agrees with the rewritten ledger.
    loaded = load_assessment_v2(root, "assess-b")[:3]
    reference = read_json(directory / "human-reference.json")
    forged = reference | {
        "ledger_prefix_sha256": digest((directory / "human-labels.jsonl").read_text()),
        "labels": load_labels_v2(*loaded),
    }
    forged["sha256"] = digest({k: v for k, v in forged.items() if k != "sha256"})
    (directory / "human-reference.json").write_text(json.dumps(forged))
    load_reference_v2(*loaded, for_scoring=True)  # The forgery is self-consistent.
    with pytest.raises(ValueError, match="preserved sheet"):
        compare_assessments(root, "assess-a", "assess-b", DECLARED, "forged")
    assert not (root / "analysis").exists()
