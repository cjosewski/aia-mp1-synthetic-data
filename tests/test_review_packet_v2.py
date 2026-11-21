"""One masked packet over both arms: opaque order, no provenance, whole-sheet intake."""

import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import pytest
from test_generation import valid_item
from v2_fixtures import (
    REPO,
    REVIEWER,
    RUBRIC_V2,
    arms,
    decisions,
    pin_task_pack,
    resign_ledger,
    selected_records,
    v2_config,
)
from v2_fixtures import complete_sheet as completed

from aia_mp1 import review_packet_v2
from aia_mp1.assessment import exclusive, read_json
from aia_mp1.assessment_v2 import create_assessment_v2, load_assessment_v2
from aia_mp1.evaluation_v2_cli import main as evaluation_main
from aia_mp1.labels_v2 import (
    append_label_v2,
    interactive_label_v2,
    load_labels_v2,
    record_label_v2,
)
from aia_mp1.reference_v2 import freeze_reference_v2
from aia_mp1.review_packet_v2 import (
    ADOPTION,
    MARKER,
    PARSER_VERSION,
    TEMPLATE,
    import_packet_answers,
    load_packet,
    packet_label_records,
    parse_packet_answers,
    pinned_briefs,
    pinned_task_pack_sha256,
    prepare_masked_packet,
    render_answers,
    render_item,
)
from aia_mp1.rubric_v2 import load_rubric_v2
from aia_mp1.schemas import CATEGORIES, QAItem
from aia_mp1.tracing import digest, read_records

FROZEN = json.loads(RUBRIC_V2.read_text(encoding="utf-8"))
TARGET_LINES = [
    f"- {category}: {target}"
    for category, target in FROZEN["target_version"]["category_targets"].items()
]
REVIEWER_FILES = [
    "MY-ANSWERS.md",
    "MY-ANSWERS.template.md",
    "REVIEW-PACKET.md",
    "RUNBOOK.md",
    "manifest.json",
    "rubric-v2.json",
]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def ready(tmp_path, monkeypatch):
    """Both arms frozen and unreviewed; the synthetic pack stands in for the pinned one."""
    root, config = arms(tmp_path)
    create_assessment_v2(root, "cohort-a", "assess-a", declare_no_prior_reviews=True)
    create_assessment_v2(root, "cohort-b", "assess-b", declare_no_prior_reviews=True)
    pack = Path(config.reference_pack_path)
    pin_task_pack(monkeypatch, pack)
    return root, pack, tmp_path


def prepare(ready, packet_id="packet-x", output="reviewer", ids=("assess-a", "assess-b"), **kw):
    root, pack, tmp_path = ready
    return prepare_masked_packet(root, packet_id, list(ids), pack, tmp_path / output, **kw)


def records_by_entry(root):
    return {
        (assessment_id, record["item_id"]): record
        for assessment_id in ("assess-a", "assess-b")
        for record in selected_records(root, assessment_id)
    }


def mapping(root, packet_id="packet-x"):
    return read_json(root / "packets" / packet_id / "sealed-mapping.json")["entries"]


def sections(text: str) -> dict[str, str]:
    parts = text.split("\n## Item ")[1:]
    return {part[:3]: "## Item " + part for part in parts}


def test_forty_opaque_items_in_a_seeded_order_that_mixes_both_arms(ready):
    root, pack, tmp_path = ready
    copy, other = tmp_path / "copy", tmp_path / "other"
    shutil.copytree(root, copy)
    shutil.copytree(root, other)
    packet = prepare(ready)
    prepare_masked_packet(copy, "packet-x", ["assess-b", "assess-a"], pack, tmp_path / "again")
    prepare_masked_packet(
        other, "packet-x", ["assess-a", "assess-b"], pack, tmp_path / "seed", seed="another"
    )
    entries = mapping(root)
    assert [e["review_id"] for e in entries] == [f"R{n:02d}" for n in range(1, 41)]
    assert [item["review_id"] for item in packet["items"]] == [e["review_id"] for e in entries]
    assert {(e["assessment_id"], e["item_id"]) for e in entries} == set(records_by_entry(root))
    assert Counter(e["assessment_id"] for e in entries) == {"assess-a": 20, "assess-b": 20}
    order = [e["assessment_id"] for e in entries]
    assert order[:20] != ["assess-a"] * 20 and order[:20] != ["assess-b"] * 20
    assert mapping(copy) == entries
    assert [(e["assessment_id"], e["item_id"]) for e in mapping(other)] != [
        (e["assessment_id"], e["item_id"]) for e in entries
    ]
    assert all(
        e["payload_sha256"]
        == digest(records_by_entry(root)[(e["assessment_id"], e["item_id"])]["item"])
        for e in entries
    )


def test_reviewer_files_never_reveal_provenance(ready):
    root, _, tmp_path = ready
    prepare(ready)
    output = tmp_path / "reviewer"
    assert sorted(path.name for path in output.iterdir()) == REVIEWER_FILES
    assert (output / "rubric-v2.json").read_bytes() == RUBRIC_V2.read_bytes()
    forbidden = {
        "baseline",
        "corrected",
        "reference_context",
        "purpose",
        "assess-a",
        "assess-b",
        "cohort-a",
        "cohort-b",
        "arm-a",
        "arm-b",
        "variant-b",
        "actual-local-model",
        "test-source",
        "example.invalid",
        "Synthetic reference text",
        *CATEGORIES,
        *(task["task_id"] for task in FROZEN["professional_boundary_triggers"]["tasks"]),
    }
    for (assessment_id, _), record in records_by_entry(root).items():
        _, manifest, _, _ = load_assessment_v2(root, assessment_id)
        forbidden |= {
            manifest["manifest_sha256"],
            record["item_id"],
            record["run_id"],
            record["trace_id"],
            record["attempt_id"],
            record["prompt_hash"],
            record["reference_context"]["task"]["id"],
            record["reference_context"]["pack_sha256"],
            digest(record["item"]),
        }
    for name in REVIEWER_FILES:
        if name == "rubric-v2.json":
            continue  # Byte-identical to the frozen rubric for every packet.
        text = (output / name).read_text()
        if name == "REVIEW-PACKET.md":
            # Category IDs may appear only as the labels of the item-independent target list.
            for line in TARGET_LINES:
                assert text.count(line) == 1
                text = text.replace(line, "")
        text = text.casefold()
        assert not sorted(word for word in forbidden if word.casefold() in text), name


def test_global_rules_are_quoted_in_order_before_the_dimensions(ready):
    _, _, tmp_path = ready
    prepare(ready)
    lines = (tmp_path / "reviewer/REVIEW-PACKET.md").read_text().splitlines()
    target, boundary = FROZEN["target_version"], FROZEN["professional_boundary_triggers"]
    expected = [
        "## Global rules",
        FROZEN["reader"],
        FROZEN["evidence_standard"],
        f"rule: {target['rule']}",
        "category_targets:",
        *TARGET_LINES,
        f"helper_software: {target['helper_software']}",
        f"off_target_items: {target['off_target_items']}",
        f"meaning: {FROZEN['task_brief']['meaning']}",
        FROZEN["terms"],
        FROZEN["fields_rule"],
        FROZEN["anchor_reading"],
        FROZEN["label_rule"],
        f"rule: {boundary['rule']}",
        f"reporting: {boundary['reporting']}",
        "## Rubric (aec-rubric-v2)",
        "### fidelity: Task fidelity",
    ]
    positions = [lines.index(line) for line in expected]
    assert positions == sorted(positions)
    section = lines[positions[0] : lines.index("## Rubric (aec-rubric-v2)")]
    keys = [line[4:].split(":")[0] for line in section if line.startswith("### ")]
    assert keys == [
        "reader",
        "evidence_standard",
        "target_version",
        "task_brief",
        "terms",
        "fields_rule",
        "anchor_reading",
        "label_rule",
        "professional_boundary_triggers",
    ]


def test_per_task_lists_and_unrendered_sub_keys_stay_out_of_the_packet(ready):
    _, _, tmp_path = ready
    prepare(ready)
    text = (tmp_path / "reviewer/REVIEW-PACKET.md").read_text()
    target, brief = FROZEN["target_version"], FROZEN["task_brief"]
    boundary = FROZEN["professional_boundary_triggers"]
    closest = boundary["closest_wording_not_triggering"]
    omitted = [
        "briefs_stating_a_version",
        "closest_wording_not_triggering",
        "trigger_phrase",
        target["source"]["path"],
        target["source"]["sha256"],
        brief["definition"],
        brief["wording"],
        boundary["summary"],
        *target["briefs_stating_a_version"],
        *(row[key] for row in closest for key in ("task_id", "phrase", "reason")),
        *(task["task_id"] for task in boundary["tasks"]),
    ]
    assert not [value for value in omitted if value in text]


def test_both_arms_render_through_one_function(ready):
    root, _, tmp_path = ready
    prepare(ready)
    output = tmp_path / "reviewer"
    packet = sections((output / "REVIEW-PACKET.md").read_text())
    answers = sections((output / "MY-ANSWERS.md").read_text())
    records = records_by_entry(root)
    by_content = {}
    for entry in mapping(root):
        record = records[(entry["assessment_id"], entry["item_id"])]
        section = packet[entry["review_id"]]
        brief = record["reference_context"]["task"]["brief"]
        assert brief in section
        assert json.dumps(record["item"], ensure_ascii=False, indent=2) in section
        key = (brief, json.dumps(record["item"], sort_keys=True))
        by_content.setdefault(key, []).append(entry)
    pairs = [
        g
        for g in by_content.values()
        if {e["assessment_id"] for e in g} == {"assess-a", "assess-b"}
    ]
    assert pairs
    for first, second in pairs:
        for rendered in (packet, answers):
            one = rendered[first["review_id"]].replace(first["review_id"], "Rnn")
            assert one == rendered[second["review_id"]].replace(second["review_id"], "Rnn")
    issued = read_json(output / "manifest.json")
    assert issued["review_ids"] == [f"R{n:02d}" for n in range(1, 41)]
    for name, expected in issued["files_sha256"].items():
        assert file_sha256(output / name) == expected
    committed = read_json(root / "packets/packet-x/packet.json")["reviewer_files_sha256"]
    assert committed == {name: file_sha256(output / name) for name in REVIEWER_FILES}


def replace_section(text, review_id, new):
    current = sections(text)[review_id]
    return text.replace(current, new, 1)


def in_section(review_id, old, new):
    """Replace the first occurrence of old inside one item's section."""

    def mutate(text):
        current = sections(text)[review_id]
        return text.replace(current, current.replace(old, new, 1), 1)

    return mutate


COMMENT = "Comments: Synthetic comment.\nSecond synthetic line.\n"
INVALID = {
    "missing section": (lambda t: replace_section(t, "R07", ""), "each once and in order"),
    "extra section": (
        lambda t: t + "\n## Item R41\n" + t.split("## Item R40\n")[1],
        "each once and in order",
    ),
    "out of order": (
        lambda t: (
            t.replace("## Item R02\n", "## Item RXX\n")
            .replace("## Item R03\n", "## Item R02\n")
            .replace("## Item RXX\n", "## Item R03\n")
        ),
        "each once and in order",
    ),
    "underscore": (lambda t: t.replace("fidelity=1", "fidelity=_", 1), "replace every _"),
    "non-binary": (lambda t: t.replace("tips=1", "tips=2", 1), "must be 0 or 1"),
    "empty comment": (lambda t: t.replace(COMMENT, "Comments: \n", 1), "write a comment"),
    "underscore comment": (lambda t: t.replace(COMMENT, "Comments: _\n", 1), "write a comment"),
    "missing declaration": (
        lambda t: t.replace("Review date: 2026-11-21\n", ""),
        "declaration once: Review date",
    ),
    "adoption not yes": (
        lambda t: t.replace("ratings/comments: Yes", "ratings/comments: No"),
        "Yes declaration required: I personally",
    ),
    "blind not yes": (
        lambda t: t.replace("for these items: Yes", "for these items: Partly"),
        "Yes declaration required: I completed",
    ),
    "exposure": (
        lambda t: t.replace(
            "before this review (NONE or describe): NONE",
            "before this review (NONE or describe): Saw an earlier judge summary",
        ),
        "NONE for judge-output exposure",
    ),
    "boundary failed on an untriggered brief": (
        lambda t: t.replace("| professional_boundary=1 |", "| professional_boundary=0 |", 1),
        "automatic pass",
    ),
    "another packet": (lambda t: t.replace("Packet: packet-x", "Packet: packet-y"), "another"),
    **{
        f"U+{ord(separator):04X} in a comment": (
            in_section("R03", "Synthetic comment.", f"Pasted{separator}note."),
            f"Item R03: .*U\\+{ord(separator):04X}",
        )
        for separator in map(chr, (0x2028, 0x2029, 0x85))
    },
    "line separator in a declaration": (
        lambda t: t.replace(f"Reviewer: {REVIEWER}", f"Reviewer: Synthetic{chr(0x2028)}x"),
        "declarations: .*U\\+2028",
    ),
    "hidden comment opening": (
        in_section("R05", "Synthetic comment.", "Synthetic <!-- hidden"),
        "Item R05: .*<!--",
    ),
    "tag line inside a comment": (
        in_section("R06", "Second synthetic line.", "<details>Second synthetic line."),
        "Item R06: .*HTML tag",
    ),
    "tag hiding a declaration": (
        lambda t: t.replace(f"{ADOPTION}: Yes\n", f"<div hidden>\n\n{ADOPTION}: Yes\n\n</div>\n"),
        "declarations: .*HTML tag",
    ),
    "h-tag line is not an autolink": (
        in_section("R07", "Second synthetic line.", "<h1 hidden>Second synthetic line."),
        "Item R07: .*HTML tag",
    ),
    "hidden declarations": (
        lambda t: t.replace("NONE): NONE\n", "NONE): NONE\n<!--\n", 1).replace(
            "for these items: Yes\n", "for these items: Yes\n-->\n", 1
        ),
        "declarations: .*<!--",
    ),
}


def test_complete_sheet_parses_and_every_gap_is_refused(ready):
    root, _, tmp_path = ready
    packet = prepare(ready)
    template = (tmp_path / "reviewer/MY-ANSWERS.template.md").read_text()
    assert template.count("| professional_boundary=1 |") == 40
    with pytest.raises(ValueError, match="declaration"):
        parse_packet_answers(template, packet)
    sheet = completed(template)
    parsed = parse_packet_answers("\ufeff" + sheet.replace("\n", "\r\n"), packet)
    assert [row["review_id"] for row in parsed["labels"]] == [f"R{n:02d}" for n in range(1, 41)]
    assert all(row["decisions"] == decisions() for row in parsed["labels"])
    assert parsed["labels"][0]["notes"] == "Synthetic comment.\nSecond synthetic line."
    assert parsed["declarations_as_supplied"]["Reviewer"] == REVIEWER
    arrow = "ModelLine --> Curve conversion is wrong; a < b stays plain text."
    accepted = parse_packet_answers(sheet.replace("Synthetic comment.", arrow, 1), packet)
    assert accepted["labels"][0]["notes"].startswith(arrow)
    for link in ("<https://pro.arcgis.com/en/pro-app/3.6/>", "  <http://example.invalid/>"):
        linked = parse_packet_answers(sheet.replace("Second synthetic line.", link, 1), packet)
        assert linked["labels"][0]["notes"].endswith(link.strip())
    for name, (mutate, message) in INVALID.items():
        changed = mutate(sheet)
        assert changed != sheet, name
        try:
            parse_packet_answers(changed, packet)
        except ValueError as error:
            assert re.search(message, str(error)), (name, str(error))
        else:
            pytest.fail(f"accepted an invalid sheet: {name}")


def write_answers(tmp_path, text):
    path = tmp_path / "reviewer/MY-ANSWERS.md"
    path.write_text(text)
    return path


def test_import_writes_twenty_plus_twenty_blind_labels_once(ready):
    root, _, tmp_path = ready
    prepare(ready)
    template = (tmp_path / "reviewer/MY-ANSWERS.template.md").read_text()
    answers = write_answers(tmp_path, completed(template, {"R01": ["clarity"]}))
    result = import_packet_answers(root, "packet-x", answers, REVIEWER)
    directory = root / "packets/packet-x"
    assert (directory / "submitted-answers.md").read_bytes() == answers.read_bytes()
    assert read_json(directory / "import.json") == result
    assert result["answers_sha256"] == file_sha256(answers)
    labels = {
        aid: load_labels_v2(*load_assessment_v2(root, aid)[:3]) for aid in ("assess-a", "assess-b")
    }
    assert [len(group) for group in labels.values()] == [20, 20]
    for entry in mapping(root):
        label = labels[entry["assessment_id"]][entry["item_id"]]
        assert (label["review_stage"], label["packet_id"]) == ("blind", "packet-x")
        assert label["review_id"] == entry["review_id"]
        assert result["label_ids"][entry["review_id"]] == label["label_id"]
        assert label["notes"] == "Synthetic comment.\nSecond synthetic line."
        expected = decisions(clarity=0) if entry["review_id"] == "R01" else decisions()
        assert label["decisions"] == expected
    with pytest.raises(ValueError, match="already imported"):
        import_packet_answers(root, "packet-x", answers, REVIEWER)
    for assessment_id in ("assess-a", "assess-b"):
        reference = freeze_reference_v2(root, assessment_id, REVIEWER, declare_blind=True)
        assert reference["packet_ids"] == ["packet-x"]


def test_interrupted_import_blocks_later_imports(ready, monkeypatch):
    root, _, tmp_path = ready
    prepare(ready)
    answers = write_answers(
        tmp_path, completed((tmp_path / "reviewer/MY-ANSWERS.template.md").read_text())
    )
    real, calls = review_packet_v2.append_label_v2, []

    def interrupted(*args, **kwargs):
        calls.append(args)
        if len(calls) == 6:
            raise KeyboardInterrupt
        return real(*args, **kwargs)

    monkeypatch.setattr(review_packet_v2, "append_label_v2", interrupted)
    with pytest.raises(KeyboardInterrupt):
        import_packet_answers(root, "packet-x", answers, REVIEWER)
    monkeypatch.setattr(review_packet_v2, "append_label_v2", real)
    directory = root / "packets/packet-x"
    # The sheet and its declarations are preserved before the first label is appended.
    assert (directory / "submitted-answers.md").read_bytes() == answers.read_bytes()
    started = read_json(directory / "import-started.json")
    assert started["answers_sha256"] == file_sha256(answers)
    assert started["declarations_as_supplied"]["Reviewer"] == REVIEWER
    assert not (directory / "import.json").exists()
    assert not list(root.rglob(".writer.lock"))
    with pytest.raises(ValueError, match="interrupted"):
        import_packet_answers(root, "packet-x", answers, REVIEWER)
    counts = [
        len(load_labels_v2(*load_assessment_v2(root, a)[:3])) for a in ("assess-a", "assess-b")
    ]
    assert sum(counts) == 5


@pytest.mark.parametrize("target", ["mapping", "packet", "resigned-packet"])
def test_mapping_and_template_commitments_are_enforced(ready, target):
    root, _, tmp_path = ready
    prepare(ready)
    answers = write_answers(
        tmp_path, completed((tmp_path / "reviewer/MY-ANSWERS.template.md").read_text())
    )
    directory = root / "packets/packet-x"
    if target == "mapping":
        path = directory / "sealed-mapping.json"
        value = read_json(path)
        first, second = value["entries"][:2]
        first["item_id"], second["item_id"] = second["item_id"], first["item_id"]
        path.write_text(json.dumps(value, indent=2) + "\n")
        message = "mapping"
    else:
        path = directory / "packet.json"
        value = read_json(path)
        value["items"][0]["professional_boundary_triggered"] = True
        if target == "resigned-packet":
            value["sha256"] = digest({k: v for k, v in value.items() if k != "sha256"})
        path.write_text(json.dumps(value))
        message = "template" if target == "resigned-packet" else "packet record"
    with pytest.raises(ValueError, match=message):
        import_packet_answers(root, "packet-x", answers, REVIEWER)
    assert not (directory / "import-started.json").exists()
    assert all(
        not load_labels_v2(*load_assessment_v2(root, a)[:3]) for a in ("assess-a", "assess-b")
    )


def resign_packet(directory, mutate_mapping=None, mutate_packet=None):
    """Rewrite the sealed mapping and the packet record so both hash commitments still hold."""
    value = read_json(directory / "sealed-mapping.json")
    if mutate_mapping:
        mutate_mapping(value)
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    (directory / "sealed-mapping.json").write_text(text)
    packet = read_json(directory / "packet.json")
    packet["sealed_mapping_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    if mutate_packet:
        mutate_packet(packet)
    packet["sha256"] = digest({k: v for k, v in packet.items() if k != "sha256"})
    (directory / "packet.json").write_text(json.dumps(packet))
    for recorded in packet["assessments"]:  # Re-bind each assessment's packet marker too.
        marker = directory.parents[1] / "assessments" / recorded["assessment_id"] / MARKER
        marker.write_text(json.dumps(read_json(marker) | {"packet_sha256": packet["sha256"]}))


def swap_targets(value):
    first, second = value["entries"][:2]
    for key in ("assessment_id", "assessment_sha256", "item_id", "payload_sha256"):
        first[key], second[key] = second[key], first[key]


def flip_first_flag(packet):
    packet["items"][0]["professional_boundary_triggered"] = True
    template = render_answers(packet["packet_id"], packet["items"])
    packet["reviewer_files_sha256"][TEMPLATE] = hashlib.sha256(template.encode()).hexdigest()


def unselected_target(root):
    selected = set(read_json(root / "assessments/assess-a/manifest.json")["selected_ids"])
    _, _, records, _ = load_assessment_v2(root, "assess-a")
    record = next(r for r in records if r["item_id"] not in selected)

    def mutate(value):
        entry = next(e for e in value["entries"] if e["assessment_id"] == "assess-a")
        entry["item_id"], entry["payload_sha256"] = record["item_id"], digest(record["item"])

    return mutate


@pytest.mark.parametrize("change", ["swapped targets", "unselected item", "flipped boundary flag"])
def test_resigned_packet_records_must_rebuild_from_both_selections(ready, change):
    root, _, tmp_path = ready
    prepare(ready)
    answers = write_answers(
        tmp_path, completed((tmp_path / "reviewer/MY-ANSWERS.template.md").read_text())
    )
    directory = root / "packets/packet-x"
    if change == "swapped targets":
        resign_packet(directory, mutate_mapping=swap_targets)
    elif change == "unselected item":
        resign_packet(directory, mutate_mapping=unselected_target(root))
    else:
        resign_packet(directory, mutate_packet=flip_first_flag)
    load_packet(root, "packet-x")  # Every hash commitment still holds after the rewrite.
    message = "professional-boundary" if change == "flipped boundary flag" else "frozen selections"
    with pytest.raises(ValueError, match=message):
        import_packet_answers(root, "packet-x", answers, REVIEWER)
    assert not (directory / "import-started.json").exists()
    assert all(
        not load_labels_v2(*load_assessment_v2(root, a)[:3]) for a in ("assess-a", "assess-b")
    )


def test_a_sheet_already_in_the_packet_folder_stops_the_import_before_any_label(ready):
    root, _, tmp_path = ready
    prepare(ready)
    answers = write_answers(
        tmp_path, completed((tmp_path / "reviewer/MY-ANSWERS.template.md").read_text())
    )
    kept = root / "packets/packet-x/submitted-answers.md"
    kept.write_text("An operator's earlier copy")
    with pytest.raises(ValueError, match="inspect"):
        import_packet_answers(root, "packet-x", answers, REVIEWER)
    assert kept.read_text() == "An operator's earlier copy"
    assert not (root / "packets/packet-x/import-started.json").exists()
    assert all(
        not load_labels_v2(*load_assessment_v2(root, a)[:3]) for a in ("assess-a", "assess-b")
    )


def test_freeze_requires_the_packets_import_to_have_finished(ready, monkeypatch):
    root, _, tmp_path = ready
    prepare(ready)
    answers = write_answers(
        tmp_path, completed((tmp_path / "reviewer/MY-ANSWERS.template.md").read_text())
    )
    real = review_packet_v2.save_new

    def stop_before_the_record(path, value):
        if path.name == "import.json":
            raise KeyboardInterrupt
        return real(path, value)

    monkeypatch.setattr(review_packet_v2, "save_new", stop_before_the_record)
    with pytest.raises(KeyboardInterrupt):
        import_packet_answers(root, "packet-x", answers, REVIEWER)
    monkeypatch.setattr(review_packet_v2, "save_new", real)
    counts = [
        len(load_labels_v2(*load_assessment_v2(root, a)[:3])) for a in ("assess-a", "assess-b")
    ]
    assert counts == [20, 20]
    with pytest.raises(ValueError, match="unfinished"):
        freeze_reference_v2(root, "assess-a", REVIEWER, declare_blind=True)
    assert not (root / "assessments/assess-a/human-reference.json").exists()


@pytest.mark.parametrize("tamper", ["label ids", "sheet"])
def test_freeze_refuses_an_import_record_that_no_longer_matches(ready, tamper):
    root, _, tmp_path = ready
    prepare(ready)
    answers = write_answers(
        tmp_path, completed((tmp_path / "reviewer/MY-ANSWERS.template.md").read_text())
    )
    import_packet_answers(root, "packet-x", answers, REVIEWER)
    directory = root / "packets/packet-x"
    if tamper == "label ids":
        record = read_json(directory / "import.json")
        ids = record["label_ids"]
        ids["R01"], ids["R02"] = ids["R02"], ids["R01"]
        record["sha256"] = digest({k: v for k, v in record.items() if k != "sha256"})
        (directory / "import.json").write_text(json.dumps(record))
    else:
        (directory / "submitted-answers.md").write_bytes(answers.read_bytes() + b"Edited.\n")
    for assessment_id in ("assess-a", "assess-b"):
        with pytest.raises(ValueError, match="import"):
            freeze_reference_v2(root, assessment_id, REVIEWER, declare_blind=True)


@pytest.mark.parametrize("failure", ["output under a regular file", "staging"])
def test_a_failure_before_binding_leaves_both_assessments_free(ready, monkeypatch, failure):
    root, pack, tmp_path = ready
    output = tmp_path / "reviewer"
    if failure == "output under a regular file":
        blocker = tmp_path / "not-a-folder"
        blocker.write_text("A file where a folder was meant.")
        output = blocker / "reviewer"
    else:
        real_open, staged = Path.open, []

        def disk_full_on_the_third_staged_file(self, mode="r", *args, **kwargs):
            if ".partial-" in self.parent.name and "x" in mode:
                staged.append(self)
                if len(staged) == 3:
                    raise OSError(28, "No space left on device (simulated)")
            return real_open(self, mode, *args, **kwargs)

        monkeypatch.setattr(Path, "open", disk_full_on_the_third_staged_file)
    with pytest.raises(OSError):
        prepare_masked_packet(root, "packet-x", ["assess-a", "assess-b"], pack, output)
    if failure == "staging":
        monkeypatch.setattr(Path, "open", real_open)
    for assessment_id in ("assess-a", "assess-b"):
        assert not (root / "assessments" / assessment_id / MARKER).exists()
    assert not (root / "packets/packet-x").exists()
    assert not list(tmp_path.glob(".*.partial-*")) and not list(root.rglob(".writer.lock"))
    prepare_masked_packet(root, "packet-x", ["assess-a", "assess-b"], pack, tmp_path / "retry")


def test_a_mapping_resigned_after_the_import_cannot_change_a_payload_hash(ready):
    # Only the label's payload clause sees this: the item still routes, the hashes commit.
    root, directory = imported(ready)
    entry = mapping(root)[0]

    def other_payload(value):
        next(e for e in value["entries"] if e["review_id"] == "R01")["payload_sha256"] = "0" * 64

    resign_packet(directory, mutate_mapping=other_payload)
    load_packet(root, "packet-x")  # Every hash commitment still holds after the rewrite.
    with pytest.raises(ValueError, match="R01 of packet packet-x"):
        freeze_reference_v2(root, entry["assessment_id"], REVIEWER, declare_blind=True)


@pytest.mark.parametrize("change", ["flipped decision", "label moved to another item"])
def test_freeze_binds_packet_labels_to_the_preserved_sheet(ready, change):
    root, _, tmp_path = ready
    prepare(ready)
    template = (tmp_path / "reviewer/MY-ANSWERS.template.md").read_text()
    answers = write_answers(tmp_path, completed(template, {"R01": ["clarity"]}))
    import_packet_answers(root, "packet-x", answers, REVIEWER)
    assessment_id = mapping(root)[0]["assessment_id"]
    directory = root / "assessments" / assessment_id
    ledger = read_records(directory / "human-labels.jsonl")
    index = next(i for i, e in enumerate(ledger) if e["label"]["review_id"] == "R01")
    if change == "flipped decision":
        resign_ledger(directory, lambda label: label["decisions"].update(clarity=1), index)
    else:
        other = next(i for i in range(len(ledger)) if i != index)
        keys = ("item_id", "trace_id", "payload_sha256")
        first, second = ({k: ledger[i]["label"][k] for k in keys} for i in (index, other))
        resign_ledger(directory, lambda label: label.update(second), index)
        resign_ledger(directory, lambda label: label.update(first), other)
    load_labels_v2(*load_assessment_v2(root, assessment_id)[:3])  # Still self-consistent.
    with pytest.raises(ValueError, match="preserved sheet"):
        freeze_reference_v2(root, assessment_id, REVIEWER, declare_blind=True)
    assert not (directory / "human-reference.json").exists()


def imported(ready):
    """Prepare packet-x, answer it with R01 failed on clarity, and import the sheet."""
    root, _, tmp_path = ready
    prepare(ready)
    template = (tmp_path / "reviewer/MY-ANSWERS.template.md").read_text()
    answers = write_answers(tmp_path, completed(template, {"R01": ["clarity"]}))
    import_packet_answers(root, "packet-x", answers, REVIEWER)
    return root, root / "packets/packet-x"


def rewrite(path, change, *, resign):
    value = read_json(path)
    change(value)
    if resign:
        value["sha256"] = digest({k: v for k, v in value.items() if k != "sha256"})
    path.write_text(json.dumps(value))


def changed_declaration(value):
    value["declarations_as_supplied"]["Review date"] = "2026-11-22"


@pytest.mark.parametrize(
    "files, change, resign",
    [
        # V-N1: a field no other check covers, under the record's old self-hash.
        (("import.json",), lambda r: r.update(imported_at="2026-11-22T00:00:00+00:00"), False),
        # V-N19: the record no longer covers every review ID.
        (("import.json",), lambda r: r["label_ids"].pop("R01"), True),
        # V-N20: the record names another packet.
        (("import.json",), lambda r: r.update(packet_id="packet-y"), True),
        # V-N18: the started marker's declarations differ from the record's.
        (("import-started.json",), changed_declaration, False),
        # The record and its marker agree with each other, not with the preserved sheet.
        (("import.json", "import-started.json"), changed_declaration, True),
        (("import.json",), lambda r: r.update(reviewer="Another synthetic reviewer"), True),
    ],
)
def test_freeze_refuses_a_tampered_import_record(ready, files, change, resign):
    root, directory = imported(ready)
    for name in files:
        rewrite(directory / name, change, resign=resign and name == "import.json")
    for assessment_id in ("assess-a", "assess-b"):
        with pytest.raises(ValueError, match="import record differs"):
            freeze_reference_v2(root, assessment_id, REVIEWER, declare_blind=True)


def append_envelope(directory, label):
    """Append one correctly chained envelope and move the checkpoint with it."""
    path = directory / "human-labels.jsonl"
    previous = read_records(path)[-1]["sha256"]
    envelope = {"label": label, "previous_sha256": previous}
    envelope["sha256"] = digest(envelope)
    path.write_text(path.read_text() + json.dumps(envelope, ensure_ascii=False) + "\n")
    checkpoint = read_json(directory / "labels-checkpoint.json")
    checkpoint |= {"ledger_sha256": digest(path.read_text()), "count": checkpoint["count"] + 1}
    (directory / "labels-checkpoint.json").write_text(json.dumps(checkpoint))


@pytest.mark.parametrize("half", ["extra label ID", "missing label ID"])
def test_each_packet_label_is_bound_by_its_imported_label_id(ready, half):
    root, directory = imported(ready)
    assessment_id = mapping(root)[0]["assessment_id"]
    parent = root / "assessments" / assessment_id
    if half == "extra label ID":  # V-N3a: an identical label under an ID the import never wrote.
        original = next(
            e["label"]
            for e in read_records(parent / "human-labels.jsonl")
            if e["label"]["review_id"] == "R01"
        )
        forged = original | {
            "label_id": "forged-label",
            "supersedes_label_id": original["label_id"],
        }
        append_envelope(parent, forged)
    else:  # V-N3b: the import names a label ID that no label carries.
        rewrite(directory / "import.json", lambda r: r["label_ids"].update(R01="gone"), resign=True)
    load_labels_v2(*load_assessment_v2(root, assessment_id)[:3])  # Still self-consistent.
    with pytest.raises(ValueError, match="R01 of packet packet-x"):
        freeze_reference_v2(root, assessment_id, REVIEWER, declare_blind=True)


def stray(labels):
    """A further label claiming the packet, under an ID and item the import never wrote."""
    claimed = next(label for label in labels.values() if "packet_id" in label)
    return claimed | {"label_id": "stray", "item_id": "stray-item"}


@pytest.mark.parametrize(
    "change",
    [
        # Losing the packet would also shift its label count, so a stray label keeps the
        # count equal and leaves the per-label packet_id check alone to refuse it.
        lambda label, labels: (label.pop("packet_id"), labels.update({"stray": stray(labels)})),
        lambda label, labels: label.update(review_id="R02"),
        lambda label, labels: label.update(assessment_id="another-assessment"),
        lambda label, labels: label.update(item_id="another-item"),
        lambda label, labels: label.update(payload_sha256="0" * 64),
        lambda label, labels: label["decisions"].update(clarity=1),
        lambda label, labels: label.update(notes="Edited after the import."),
        lambda label, labels: label.update(reviewer="Another synthetic reviewer"),
        lambda label, labels: label.update(review_stage="post_review"),
    ],
)
def test_every_packet_label_field_is_bound_to_the_sheet_and_routing(ready, change):
    root, _ = imported(ready)
    assessment_id = mapping(root)[0]["assessment_id"]
    labels = load_labels_v2(*load_assessment_v2(root, assessment_id)[:3])
    packet_label_records(root, assessment_id, labels)  # The untouched labels are bound.
    item_id = mapping(root)[0]["item_id"]
    labels[item_id] = json.loads(json.dumps(labels[item_id]))
    change(labels[item_id], labels)
    with pytest.raises(ValueError, match="R01 of packet packet-x"):
        packet_label_records(root, assessment_id, labels)


def test_a_stray_label_claiming_the_packet_is_refused(ready):
    root, _ = imported(ready)
    assessment_id = mapping(root)[0]["assessment_id"]
    labels = load_labels_v2(*load_assessment_v2(root, assessment_id)[:3])
    with pytest.raises(ValueError, match="labels of packet packet-x differ"):
        packet_label_records(root, assessment_id, labels | {"stray-item": stray(labels)})


@pytest.mark.parametrize(
    "change",
    [
        lambda marker: marker.update(packet_id="packet-y"),
        lambda marker: marker.update(packet_sha256="0" * 64),
        None,  # The marker is missing.
    ],
)
def test_import_requires_each_assessment_bound_to_this_packet(ready, change):
    # V-N8b: each assessment's review-packet.json must name this packet and its sha256.
    root, _, tmp_path = ready
    prepare(ready)
    answers = write_answers(
        tmp_path, completed((tmp_path / "reviewer/MY-ANSWERS.template.md").read_text())
    )
    marker = root / "assessments/assess-b" / MARKER
    if change is None:
        marker.unlink()
    else:
        value = read_json(marker)
        change(value)
        marker.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="assess-b is not bound to packet-x"):
        import_packet_answers(root, "packet-x", answers, REVIEWER)
    assert not (root / "packets/packet-x/import-started.json").exists()
    assert not load_labels_v2(*load_assessment_v2(root, "assess-a")[:3])


def test_an_assessment_takes_part_in_one_packet_only(ready):
    root, _, tmp_path = ready
    prepare(ready)
    create_assessment_v2(root, "cohort-a", "assess-a2", declare_no_prior_reviews=True)
    create_assessment_v2(root, "cohort-b", "assess-b2", declare_no_prior_reviews=True)
    for ids in (("assess-a", "assess-b2"), ("assess-a2", "assess-b")):
        with pytest.raises(ValueError, match="already has review packet packet-x"):
            prepare(ready, packet_id="packet-y", output="second", ids=ids)
    assert not (root / "packets/packet-y").exists() and not (tmp_path / "second").exists()
    for assessment_id in ("assess-a", "assess-b"):
        marker = read_json(root / "assessments" / assessment_id / "review-packet.json")
        assert marker["packet_id"] == "packet-x"
    prepare(ready, packet_id="packet-y", output="second", ids=("assess-a2", "assess-b2"))


@pytest.mark.parametrize("crash", ["packet record", "publication"])
def test_a_crash_never_leaves_a_complete_looking_reviewer_folder(ready, monkeypatch, crash):
    root, _, tmp_path = ready
    if crash == "packet record":
        real = review_packet_v2.save_new

        def failing(path, value):
            if path.name == "packet.json":
                raise KeyboardInterrupt
            return real(path, value)

        monkeypatch.setattr(review_packet_v2, "save_new", failing)
    else:

        def failing(*args):
            raise KeyboardInterrupt

        monkeypatch.setattr(review_packet_v2.os, "rename", failing)
    with pytest.raises(KeyboardInterrupt):
        prepare(ready)
    assert not (tmp_path / "reviewer").exists()
    assert not list(root.rglob(".writer.lock"))


def test_fields_render_in_canonical_order_whatever_the_stored_order():
    item = valid_item(1).model_dump()
    reordered = dict(reversed(list(item.items())))
    rendered = render_item("R01", "Synthetic brief.", reordered)
    assert rendered == render_item("R01", "Synthetic brief.", item)
    body = rendered.split("```json\n", 1)[1].split("\n```", 1)[0]
    assert list(json.loads(body)) == list(QAItem.model_fields)


def test_the_real_pin_is_the_frozen_rubrics_task_pack_hash(tmp_path):
    rubric = load_rubric_v2()
    assert (
        pinned_task_pack_sha256(rubric)
        == rubric["target_version"]["source"]["sha256"]
        == "878854bc28a977256d203b16966ce5c1b334ba655622b0c7a5ddceb77be6e341"
    )
    with pytest.raises(ValueError, match="pins"):
        pinned_briefs(Path(v2_config(tmp_path).reference_pack_path), rubric)


def test_labels_are_refused_on_a_bound_arm_until_its_import_finishes(ready, capsys):
    root, _, tmp_path = ready
    prepare(ready)
    item = selected_records(root, "assess-a")[0]["item_id"]
    with pytest.raises(ValueError, match="assess-a belongs to review packet packet-x"):
        record_label_v2(root, "assess-a", item, decisions(), REVIEWER, review_stage="blind")
    prompts = []
    with pytest.raises(ValueError, match="belongs to review packet packet-x"):
        interactive_label_v2(
            root, "assess-a", REVIEWER, input_fn=prompts.append, output=lambda _: None
        )
    assert not prompts
    at = ("--artifact-root", str(root), "--assessment-id", "assess-a", "--reviewer", REVIEWER)
    assert evaluation_main(["label", *at, "--item-id", item, "--decisions", *"11111111"]) == 2
    assert "belongs to review packet packet-x" in capsys.readouterr().err
    assert not load_labels_v2(*load_assessment_v2(root, "assess-a")[:3])
    answers = write_answers(
        tmp_path, completed((tmp_path / "reviewer/MY-ANSWERS.template.md").read_text())
    )
    import_packet_answers(root, "packet-x", answers, REVIEWER)  # The import path is exempt.
    current = load_labels_v2(*load_assessment_v2(root, "assess-a")[:3])[item]
    amendment = record_label_v2(
        root, "assess-a", item, decisions(), REVIEWER, supersedes=current["label_id"]
    )
    assert amendment["supersedes_label_id"] == current["label_id"]


@pytest.mark.parametrize(
    "files", [("import.json", "import-started.json"), ("import-started.json",)]
)
def test_the_import_records_its_parser_version_and_unknown_versions_are_refused(ready, files):
    root, directory = imported(ready)
    for name in ("import-started.json", "import.json"):
        assert read_json(directory / name)["parser_version"] == PARSER_VERSION
    for name in files:  # Both records unknown, or only the marker disagreeing with the record.
        rewrite(
            directory / name,
            lambda r: r.update(parser_version="answers-v0"),
            resign=name == "import.json",
        )
    with pytest.raises(ValueError, match="parser version"):
        freeze_reference_v2(root, "assess-a", REVIEWER, declare_blind=True)


@pytest.mark.parametrize("missing", ["import-started.json", "submitted-answers.md"])
def test_a_finished_import_missing_its_marker_or_sheet_is_refused_clearly(ready, missing):
    root, directory = imported(ready)
    (directory / missing).unlink()
    with pytest.raises(ValueError, match=f"packet packet-x .*{missing}"):
        freeze_reference_v2(root, "assess-a", REVIEWER, declare_blind=True)


def test_import_refuses_another_reviewer_or_a_started_review(ready):
    root, _, tmp_path = ready
    prepare(ready)
    answers = write_answers(
        tmp_path, completed((tmp_path / "reviewer/MY-ANSWERS.template.md").read_text())
    )
    with pytest.raises(ValueError, match="reviewer"):
        import_packet_answers(root, "packet-x", answers, "Another synthetic reviewer")
    item = selected_records(root, "assess-b")[0]["item_id"]
    directory, manifest, records, _ = load_assessment_v2(root, "assess-b")
    with exclusive(directory):  # A label written past record_label_v2's refusal.
        append_label_v2(directory, manifest, records, item, decisions(), REVIEWER)
    with pytest.raises(ValueError, match="already has human labels"):
        import_packet_answers(root, "packet-x", answers, REVIEWER)
    assert not (root / "packets/packet-x/import-started.json").exists()
    assert len(load_labels_v2(*load_assessment_v2(root, "assess-a")[:3])) == 0


def test_preparation_refuses_wrong_arms_reviewed_items_and_changed_briefs(ready, monkeypatch):
    root, pack, tmp_path = ready
    create_assessment_v2(root, "cohort-a", "assess-a2", declare_no_prior_reviews=True)
    for ids, message in (
        (("assess-a", "assess-a2"), "one baseline and one corrected"),
        (("assess-a", "assess-a"), "two distinct"),
        (("assess-a", "assess-b", "assess-a2"), "two distinct"),
    ):
        with pytest.raises(ValueError, match=message):
            prepare(ready, ids=ids)
    task_id = selected_records(root, "assess-b")[0]["reference_context"]["task"]["id"]
    changed = tmp_path / "changed-pack.json"
    value = json.loads(pack.read_text())
    next(t for t in value["tasks"] if t["id"] == task_id)["brief"] = "A reworded synthetic brief."
    changed.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="pins"):
        prepare_masked_packet(root, "packet-x", ["assess-a", "assess-b"], changed, tmp_path / "x")
    monkeypatch.setattr(review_packet_v2, "pinned_task_pack_sha256", lambda r: file_sha256(changed))
    with pytest.raises(ValueError, match=f"brief for task {task_id}"):
        prepare_masked_packet(root, "packet-x", ["assess-a", "assess-b"], changed, tmp_path / "x")
    monkeypatch.setattr(review_packet_v2, "pinned_task_pack_sha256", lambda r: file_sha256(pack))
    (root / "assessments/assess-b/judges/synthetic").mkdir(parents=True)
    with pytest.raises(ValueError, match="judge"):
        prepare(ready)
    shutil.rmtree(root / "assessments/assess-b/judges")
    item = selected_records(root, "assess-a")[0]["item_id"]
    record_label_v2(root, "assess-a", item, decisions(), REVIEWER)
    with pytest.raises(ValueError, match="already has human labels"):
        prepare(ready)
    assert not (root / "packets").exists() and not (tmp_path / "reviewer").exists()


def test_existing_or_repository_destinations_are_refused(ready):
    root, pack, tmp_path = ready
    (tmp_path / "reviewer").mkdir()
    (tmp_path / "reviewer/MY-ANSWERS.md").write_text("Human work in progress")
    with pytest.raises(FileExistsError):
        prepare(ready)
    assert (tmp_path / "reviewer/MY-ANSWERS.md").read_text() == "Human work in progress"
    with pytest.raises(ValueError, match="outside the repository"):
        prepare_masked_packet(root, "packet-x", ["assess-a", "assess-b"], pack, REPO / "packet")
    prepare(ready, output="first")
    with pytest.raises(FileExistsError):
        prepare(ready, output="second")
    assert not (REPO / "packet").exists() and not (tmp_path / "second").exists()
