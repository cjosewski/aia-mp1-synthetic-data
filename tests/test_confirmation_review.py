"""Synthetic reviews only: incomplete evidence cannot become a frozen reference."""

import json
from pathlib import Path

import pytest
from assessed_fixtures import REPO, fixture_config
from test_generation import valid_item

from aia_mp1.confirmation_review import (
    ADOPTION,
    ASSISTANCE,
    BLIND,
    byte_hash,
    freeze_review,
    load_review,
    main,
    parse_answers,
    verify_packet,
)
from aia_mp1.judge import messages_for
from aia_mp1.schemas import CATEGORIES
from aia_mp1.tracing import digest


@pytest.fixture
def packet(tmp_path):
    config = fixture_config(tmp_path)
    pack = json.loads(Path(config.reference_pack_path).read_text())
    rubric = json.loads((REPO / "config/rubric.json").read_text())
    directory = tmp_path / "packet"
    directory.mkdir()
    prompt = "Synthetic confirmation test only."
    records = []
    for i in range(10):
        item = valid_item(i).model_dump()
        category = CATEGORIES[i % 5]
        records.append(
            {
                "item_id": f"synthetic-{i:02d}",
                "item": item,
                "category": category,
                "assessment_eligible": False,
                "payload_sha256": digest(item),
                "reference_context": {
                    "source_pack_sha256": digest(pack),
                    "task": {"category": category, "source_refs": ["test-source"]},
                    "sources": pack["sources"],
                },
            }
        )
    inputs = [
        {"item_id": r["item_id"], "messages": messages_for(prompt, rubric, r)} for r in records
    ]
    for name, value in {"rubric.json": rubric, "source-pack.json": pack}.items():
        (directory / name).write_text(json.dumps(value))
    for name, values in {"data.jsonl": records, "model-inputs.jsonl": inputs}.items():
        (directory / name).write_text("".join(json.dumps(v) + "\n" for v in values))
    (directory / "judge-prompt.md").write_text(prompt)
    manifest = {
        "packet_id": "synthetic-packet",
        "source_pack_sha256": digest(pack),
        "rubric_sha256": digest(rubric),
        "prompt_sha256": digest(prompt),
        "category_counts": dict.fromkeys(CATEGORIES, 2),
        "human_label_count": 0,
        "model_requests": 0,
        "files_sha256": {p.name: byte_hash(p) for p in directory.iterdir()},
    }
    (directory / "manifest.json").write_text(json.dumps(manifest))
    text = (
        f"Packet: synthetic-packet\nReviewer: Synthetic test reviewer\nReview date: 2026-11-14\n"
        f"{ASSISTANCE}: synthetic fixture\n{ADOPTION}: Yes\n{BLIND}: Yes\n\n"
    )
    for i, record in enumerate(records, 1):
        text += (
            f"## C{i:02d} — {record['item_id']}\n\n"
            "D1=0 | D2=1 | D3=0 | D4=1 | D5=1 | D6=0\n\n"
            "Comment: Synthetic review for tests only.\nSecond comment line.\n\n"
        )
    answers = tmp_path / "answers.md"
    answers.write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode())
    return directory, byte_hash(directory / "manifest.json"), answers


def test_freeze_preserves_exact_submission_and_rejects_rewrite(packet, tmp_path):
    directory, sha, answers = packet
    out = tmp_path / "frozen"
    reference = freeze_review(directory, sha, answers, out)
    assert reference == load_review(directory, sha, out)
    assert reference["labels"][0]["decisions"]["D1"] == 0
    assert len(reference["labels"]) == 10
    assert (out / "submitted-answers.md").read_bytes() == answers.read_bytes()
    with pytest.raises(FileExistsError):
        freeze_review(directory, sha, answers, out)
    (out / "submitted-answers.md").write_text("changed")
    with pytest.raises(ValueError):
        load_review(directory, sha, out)


@pytest.mark.parametrize(
    "old,new",
    [
        ("D1=0", "D1=_"),
        ("D2=1", "D2=2"),
        ("D3=0", "D2=0"),
        ("Reviewer: Synthetic test reviewer", "Reviewer: "),
        ("synthetic-01", "synthetic-00"),
        (f"{BLIND}: Yes", f"{BLIND}: No"),
        (f"{ADOPTION}: Yes", f"{ADOPTION}: ____________________"),
        ("Comment: Synthetic review for tests only.", "Comment: ____________________"),
    ],
)
def test_incomplete_or_exposed_review_creates_nothing(packet, tmp_path, old, new):
    directory, sha, answers = packet
    text = answers.read_text(encoding="utf-8-sig").replace(old, new, 1)
    answers.write_text(text)
    out = tmp_path / "invalid-freeze"
    with pytest.raises(ValueError):
        freeze_review(directory, sha, answers, out)
    assert not out.exists()


def test_packet_tampering_and_unreviewed_message_are_rejected(packet):
    directory, sha, _ = packet
    inputs = directory / "model-inputs.jsonl"
    original = inputs.read_text()
    inputs.write_text(original.replace("Synthetic confirmation", "Changed confirmation"))
    with pytest.raises(ValueError, match="file changed"):
        verify_packet(directory, sha)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files_sha256"][inputs.name] = byte_hash(inputs)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest differs"):
        verify_packet(directory, sha)
    with pytest.raises(ValueError, match="messages differ"):
        verify_packet(directory, byte_hash(manifest_path))


def test_blank_cli_is_controlled_and_has_no_write(packet, capsys):
    directory, sha, answers = packet
    answers.write_text(answers.read_text(encoding="utf-8-sig").replace("D1=0", "D1=_"))
    assert (
        main(["--packet", str(directory), "--manifest-sha256", sha, "--answers", str(answers)]) == 1
    )
    assert "Review not ready" in capsys.readouterr().out


def test_reference_decision_cannot_be_rewritten_with_new_digest(packet, tmp_path):
    directory, sha, answers = packet
    out = tmp_path / "freeze"
    reference = freeze_review(directory, sha, answers, out)
    reference["labels"][0]["decisions"]["D1"] = 1
    reference["sha256"] = digest({k: v for k, v in reference.items() if k != "sha256"})
    (out / "human-reference.json").write_text(json.dumps(reference))
    with pytest.raises(ValueError, match="submitted record"):
        load_review(directory, sha, out)


def test_duplicate_declaration_is_not_silently_selected(packet):
    directory, sha, answers = packet
    manifest, ids = verify_packet(directory, sha)
    text = "Reviewer: Another synthetic reviewer\n" + answers.read_text(encoding="utf-8-sig")
    with pytest.raises(ValueError, match="declaration"):
        parse_answers(text, manifest["packet_id"], ids)


def test_pass_reasons_survive_freeze_and_cannot_be_removed(packet, tmp_path):
    directory, sha, answers = packet
    notes = "Pass reasons:\n\n- D2: Synthetic hazard and precaution.\n- D4: Synthetic scope."
    text = answers.read_text(encoding="utf-8-sig").replace("Comment:", notes + "\n\nComment:", 1)
    answers.write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode())
    out = tmp_path / "with-notes"
    reference = freeze_review(directory, sha, answers, out)
    assert load_review(directory, sha, out) == reference
    assert (out / "submitted-answers.md").read_bytes() == answers.read_bytes()
    assert reference["labels"][0]["comment"] == (
        notes + "\n\nComment: Synthetic review for tests only.\nSecond comment line."
    )
    assert reference["labels"][0]["decisions"] == dict(D1=0, D2=1, D3=0, D4=1, D5=1, D6=0)
    reference["labels"][0]["comment"] = "Synthetic review for tests only."
    reference["sha256"] = digest({k: v for k, v in reference.items() if k != "sha256"})
    (out / "human-reference.json").write_text(json.dumps(reference))
    with pytest.raises(ValueError, match="submitted record"):
        load_review(directory, sha, out)


@pytest.mark.parametrize("comment", ["", "   ", "___"])
def test_pass_reasons_do_not_replace_required_comment(packet, tmp_path, comment):
    directory, sha, answers = packet
    text = answers.read_text(encoding="utf-8-sig").replace(
        "Comment: Synthetic review for tests only.\nSecond comment line.",
        "Pass reasons:\n- D2: Synthetic precaution.\n\nComment: " + comment,
        1,
    )
    answers.write_text(text)
    out = tmp_path / "invalid-notes"
    with pytest.raises(ValueError):
        freeze_review(directory, sha, answers, out)
    assert not out.exists()
