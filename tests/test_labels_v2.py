"""v2 human labels: the v1 ledger guarantees, the stage rule and a masked interactive session."""

import json

import pytest
from v2_fixtures import (
    REVIEWER,
    build_cohort,
    decisions,
    resign_ledger,
    selected_records,
    v2_config,
)

from aia_mp1 import labels_v2
from aia_mp1.assessment import read_json
from aia_mp1.assessment_v2 import create_assessment_v2, load_assessment_v2
from aia_mp1.labels_v2 import (
    interactive_label_v2,
    label_status_v2,
    load_labels_v2,
    record_label_v2,
)
from aia_mp1.reference_v2 import freeze_reference_v2
from aia_mp1.schemas import CATEGORIES
from aia_mp1.tracing import digest, read_records


@pytest.fixture
def assessment(tmp_path):
    root = build_cohort(v2_config(tmp_path), "arm-a", "cohort-a")
    return root, create_assessment_v2(root, "cohort-a", "v2", declare_no_prior_reviews=True)


def effective_labels(root):
    return load_labels_v2(*load_assessment_v2(root, "v2")[:3])


def test_labels_round_trip_with_explicit_supersedes_and_multiline_notes(assessment):
    root, manifest = assessment
    item = manifest["selected_ids"][0]
    notes = "First observation.\n\nSecond paragraph, indented:\n  detail"
    first = record_label_v2(root, "v2", item, decisions(), REVIEWER, notes=notes)
    assert first["review_stage"] == "unknown" and first["notes"] == notes
    with pytest.raises(ValueError, match="amendment"):
        record_label_v2(root, "v2", item, decisions(tips=0), REVIEWER)
    second = record_label_v2(
        root, "v2", item, decisions(tips=0), REVIEWER, supersedes=first["label_id"]
    )
    with pytest.raises(ValueError, match="current label"):
        record_label_v2(root, "v2", item, decisions(), REVIEWER, supersedes=first["label_id"])
    with pytest.raises(ValueError, match="selection"):
        record_label_v2(root, "v2", "foreign-item", decisions(), REVIEWER)
    ledger = read_records(root / "assessments/v2/human-labels.jsonl")
    assert [envelope["label"] for envelope in ledger] == [first, second]
    assert effective_labels(root) == {item: second}
    status = label_status_v2(root, "v2")
    assert status["completed"] == 1 and status["effective_label_ids"] == {item: second["label_id"]}
    assert status["status"] == "incomplete" and status["reference_frozen"] is False


def test_v1_decisions_are_refused_by_the_v2_ledger(assessment):
    root, manifest = assessment
    with pytest.raises(ValueError):
        record_label_v2(
            root, "v2", manifest["selected_ids"][0], dict.fromkeys(["D1", "D2"], 1), REVIEWER
        )
    assert (root / "assessments/v2/human-labels.jsonl").read_text() == ""


def test_an_automatic_boundary_pass_cannot_be_recorded_as_a_failure(assessment):
    root, manifest = assessment
    item = manifest["selected_ids"][0]
    with pytest.raises(ValueError, match="automatic pass"):
        record_label_v2(root, "v2", item, decisions(professional_boundary=0), REVIEWER)
    assert (root / "assessments/v2/human-labels.jsonl").read_text() == ""


@pytest.mark.parametrize(
    "tamper, message",
    [
        ("edited", "checkpoint"),
        ("resigned-checkpoint", "chain changed"),
        ("count", "checkpoint"),
        ("partial-append", "inspect"),
    ],
)
def test_tampered_ledger_or_checkpoint_is_refused(assessment, tamper, message):
    root, manifest = assessment
    for item in manifest["selected_ids"][:2]:
        record_label_v2(root, "v2", item, decisions(), REVIEWER, notes="Synthetic note")
    path = root / "assessments/v2/human-labels.jsonl"
    checkpoint_path = root / "assessments/v2/labels-checkpoint.json"
    checkpoint = read_json(checkpoint_path)
    if tamper == "partial-append":
        path.write_text(path.read_text() + '{"label":')
    elif tamper == "count":
        checkpoint_path.write_text(json.dumps(checkpoint | {"count": 1}))
    else:
        path.write_text(path.read_text().replace("Synthetic note", "Changed note", 1))
        if tamper == "resigned-checkpoint":
            checkpoint["ledger_sha256"] = digest(path.read_text())
            checkpoint_path.write_text(json.dumps(checkpoint))
    with pytest.raises(ValueError, match=message):
        label_status_v2(root, "v2")


def test_labels_after_the_reference_freeze_are_post_review(assessment):
    root, manifest = assessment
    for item in manifest["selected_ids"]:
        record_label_v2(root, "v2", item, decisions(), REVIEWER, review_stage="blind")
    freeze_reference_v2(root, "v2", REVIEWER, declare_blind=True)
    item = manifest["selected_ids"][0]
    current = effective_labels(root)[item]["label_id"]
    with pytest.raises(ValueError, match="post-review"):
        record_label_v2(
            root, "v2", item, decisions(), REVIEWER, supersedes=current, review_stage="blind"
        )
    amendment = record_label_v2(
        root, "v2", item, decisions(clarity=0), REVIEWER, supersedes=current
    )
    assert amendment["review_stage"] == "post_review"
    assert label_status_v2(root, "v2")["reference_frozen"] is True


def scripted(answers):
    prompts = []

    def respond(prompt):
        prompts.append(prompt)
        if not answers:
            raise EOFError
        return answers.pop(0)

    return respond, prompts


def test_interactive_session_masks_provenance_and_passes_boundary_automatically(assessment):
    root, manifest = assessment
    ratings = ["1", "0", "x", "1", "1", "1", "1", "1"]
    output = []
    respond, _ = scripted(ratings + ["Unfinished note"])
    stopped = interactive_label_v2(root, "v2", REVIEWER, input_fn=respond, output=output.append)
    assert stopped["completed"] == 0
    respond, _ = scripted(["q"])
    assert (
        interactive_label_v2(root, "v2", REVIEWER, input_fn=respond, output=print)["completed"] == 0
    )
    respond, prompts = scripted(ratings + ["First line", "  second line", " . ", "1"])
    result = interactive_label_v2(
        root, "v2", REVIEWER, input_fn=respond, output=output.append, review_stage="blind"
    )
    assert result["completed"] == 1
    [label] = effective_labels(root).values()
    record = next(r for r in selected_records(root, "v2") if r["item_id"] == label["item_id"])
    assert label["decisions"] == decisions(completeness=0)
    assert label["notes"] == "First line\n  second line"
    assert label["review_stage"] == "blind"
    shown = "\n".join(output + prompts)
    assert "Item 1 of 20" in shown
    assert record["reference_context"]["task"]["brief"] in shown
    assert json.dumps(record["item"], ensure_ascii=False, indent=2) in shown
    assert "automatic pass (1) under F3" in shown
    assert not any(prompt.startswith("Professional boundary") for prompt in prompts)
    context = record["reference_context"]
    for hidden in (
        record["item_id"],
        record["run_id"],
        record["trace_id"],
        record["category"],
        "reference_context",
        context["task"]["id"],
        context["sources"][0]["text"],
        context["sources"][0]["url"],
    ):
        assert hidden not in shown


def test_interactive_session_asks_for_a_triggered_boundary(assessment, monkeypatch):
    root, manifest = assessment
    monkeypatch.setattr(labels_v2, "boundary_triggered", lambda rubric, task_id: True)
    respond, prompts = scripted(["1"] * 5 + ["0"] + ["1", "1", "."])
    interactive_label_v2(root, "v2", REVIEWER, input_fn=respond, output=lambda _: None)
    assert prompts[5].startswith("Professional boundary")
    [label] = effective_labels(root).values()
    assert label["decisions"] == decisions(professional_boundary=0)


def test_interactive_order_is_seeded_resumable_and_hides_the_category(assessment):
    root, manifest = assessment
    by_id = {r["item_id"]: r for r in selected_records(root, "v2")}
    shown = []
    for count in (3, 17):  # The second session resumes where the first one stopped.
        respond, _ = scripted((["1"] * 7 + ["."]) * count)
        interactive_label_v2(root, "v2", REVIEWER, input_fn=respond, output=shown.append)
    saved = [t for t in shown if t.startswith("Saved item ")]
    assert saved == [f"Saved item {k} of 20." for k in range(1, 21)]
    ledger = read_records(root / "assessments/v2/human-labels.jsonl")
    order = [by_id[envelope["label"]["item_id"]] for envelope in ledger]  # Save order.
    assert sorted(r["item_id"] for r in order) == sorted(manifest["selected_ids"])
    assert [r["item_id"] for r in order] != manifest["selected_ids"]
    # In the selection order the category is CATEGORIES[k % 5]; positions must not encode it.
    assert [r["category"] for r in order] != [CATEGORIES[k % 5] for k in range(20)]


@pytest.mark.parametrize("separator", ["\u2028", "\u2029", "\u0085"])
def test_unicode_line_separators_are_refused_before_anything_is_written(assessment, separator):
    root, manifest = assessment
    item = manifest["selected_ids"][0]
    with pytest.raises(ValueError, match="line separator"):
        record_label_v2(root, "v2", item, decisions(), REVIEWER, notes=f"one{separator}two")
    with pytest.raises(ValueError, match="line separator"):
        record_label_v2(root, "v2", item, decisions(), f"Synthetic{separator}reviewer")
    respond, _ = scripted(["1"] * 7 + [f"pasted{separator}text", "."])
    with pytest.raises(ValueError, match="line separator"):
        interactive_label_v2(root, "v2", REVIEWER, input_fn=respond, output=lambda _: None)
    assert (root / "assessments/v2/human-labels.jsonl").read_text() == ""
    assert label_status_v2(root, "v2")["completed"] == 0


def test_deleting_a_middle_envelope_breaks_the_chain(assessment):
    root, manifest = assessment
    for item in manifest["selected_ids"][:3]:
        record_label_v2(root, "v2", item, decisions(), REVIEWER)
    path = root / "assessments/v2/human-labels.jsonl"
    first, _, third = path.read_text().splitlines(keepends=True)
    path.write_text(first + third)
    checkpoint = read_json(root / "assessments/v2/labels-checkpoint.json")
    checkpoint |= {"ledger_sha256": digest(first + third), "count": 2}
    (root / "assessments/v2/labels-checkpoint.json").write_text(json.dumps(checkpoint))
    with pytest.raises(ValueError, match="chain changed"):
        label_status_v2(root, "v2")


@pytest.mark.parametrize(
    "index, mutate, message",
    [
        (0, lambda label: label.update(payload_sha256="0" * 64), "identity"),
        (0, lambda label: label.update(trace_id="another-trace"), "identity"),
        (1, lambda label: label.update(supersedes_label_id=None), "supersede"),
    ],
)
def test_loader_rechecks_identity_and_supersedes_in_a_resigned_ledger(
    assessment, index, mutate, message
):
    root, manifest = assessment
    item = manifest["selected_ids"][0]
    first = record_label_v2(root, "v2", item, decisions(), REVIEWER)
    record_label_v2(root, "v2", item, decisions(tips=0), REVIEWER, supersedes=first["label_id"])
    resign_ledger(root / "assessments/v2", mutate, index)
    with pytest.raises(ValueError, match=message):
        label_status_v2(root, "v2")
