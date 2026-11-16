"""Synthetic-only review exports preserve selection, payloads and blind boundaries."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from assessed_fixtures import GoodClient, fixture_config

from aia_mp1.assessed_review import fenced, parse_answers, prepare_review
from aia_mp1.assessment import create_cohort_assessment
from aia_mp1.cohort import freeze_cohort
from aia_mp1.collection import collect
from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.labels import record_label


@pytest.fixture
def corrected(tmp_path):
    config = fixture_config(tmp_path).model_copy(update={"purpose": "corrected"})
    root = Path(config.artifact_root)
    collect(config, "corrected", GoodClient())
    freeze_cohort(root, "corrected", "frozen")
    manifest = create_cohort_assessment(
        root, "frozen", "review", Path(__file__).resolve().parents[1] / "config/rubric.json"
    )
    return root, manifest


def test_export_has_exact_frozen_selection_and_blank_answers(corrected, tmp_path):
    root, assessment = corrected
    output = tmp_path / "review-packet"
    manifest = prepare_review(root, "review", output)
    records = [
        json.loads(line) for line in (output / "selected-items.jsonl").read_text().splitlines()
    ]
    assert [r["item_id"] for r in records] == assessment["selected_ids"]
    assert set(manifest["category_counts"].values()) == {4}
    packet = (output / "REVIEW-PACKET.md").read_text()
    assert packet.count("### Complete generated answer") == 20
    assert all(json.dumps(r["item"], ensure_ascii=False, indent=2) in packet for r in records)
    answers = (output / "MY-ANSWERS.md").read_text()
    assert answers.count("D1=_ | D2=_ | D3=_ | D4=_ | D5=_ | D6=_") == 20
    assert "MY-ANSWERS.md" not in manifest["files_sha256"]
    for name, expected in manifest["files_sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
    assert (root / "assessments/review/human-labels.jsonl").read_text() == ""
    (output / "MY-ANSWERS.md").write_text("Human work in progress")
    with pytest.raises(FileExistsError):
        prepare_review(root, "review", output)
    assert (output / "MY-ANSWERS.md").read_text() == "Human work in progress"


@pytest.mark.parametrize("started", ["human", "judge", "tampered"])
def test_rejects_prior_review_or_changed_evidence(corrected, tmp_path, started):
    root, assessment = corrected
    parent = root / "assessments/review"
    if started == "human":
        record_label(
            root,
            "review",
            assessment["selected_ids"][0],
            dict.fromkeys(DIMENSIONS, 1),
            "Synthetic reviewer",
            review_stage="blind",
        )
    elif started == "judge":
        (parent / "judges/existing").mkdir(parents=True)
    else:
        with (parent / "data.jsonl").open("a") as stream:
            stream.write("{}\n")
    with pytest.raises(ValueError):
        prepare_review(root, "review", tmp_path / "packet")
    assert not (tmp_path / "packet").exists()


def test_markdown_payload_cannot_close_its_own_fence():
    assert fenced("```\nInjected heading") == "````\n```\nInjected heading\n````\n"


def test_intake_requires_complete_authentic_declarations_and_preserves_comments(
    corrected, tmp_path
):
    root, assessment = corrected
    output = tmp_path / "answers"
    prepare_review(root, "review", output)
    blank = (output / "MY-ANSWERS.md").read_text()
    with pytest.raises(ValueError):
        parse_answers(blank, "review", assessment["selected_ids"])
    filled = blank.replace("Reviewer: \n", "Reviewer: Synthetic reviewer\n")
    filled = filled.replace("Review date: \n", "Review date: 2026-11-16\n")
    filled = filled.replace("or NONE): \n", "or NONE): NONE\n")
    filled = filled.replace("ratings/comments: \n", "ratings/comments: Yes\n")
    filled = filled.replace("for these items: \n", "for these items: Yes\n")
    filled = filled.replace("=_", "=1").replace(
        "Comments: \n", "Comments: Synthetic evidence.\nSecond line.\n"
    )
    result = parse_answers(filled, "review", assessment["selected_ids"])
    assert len(result["labels"]) == 20
    assert result["labels"][0]["notes"] == "Synthetic evidence.\nSecond line."
    assert all(row["decisions"] == dict.fromkeys(DIMENSIONS, 1) for row in result["labels"])
    for invalid in (
        filled.replace("D6=1", "D6=_", 1),
        filled.replace("for these items: Yes", "for these items: No"),
        filled.replace(assessment["selected_ids"][0], "foreign", 1),
        filled.replace("Assessment: review", "Assessment: wrong"),
    ):
        with pytest.raises(ValueError):
            parse_answers(invalid, "review", assessment["selected_ids"])
    assert (root / "assessments/review/human-labels.jsonl").read_text() == ""


def test_pdf_companion_preserves_selected_content(corrected, tmp_path):
    pytest.importorskip("reportlab")
    from pypdf import PdfReader

    path = Path(__file__).resolve().parents[1] / "tools/render_assessed_review.py"
    spec = importlib.util.spec_from_file_location("review_pdf", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root, _ = corrected
    output = tmp_path / "pdf-packet"
    prepare_review(root, "review", output)
    receipt = module.render(output)
    pages = PdfReader(output / "REVIEW-PACKET.pdf").pages
    assert receipt["pages"] == len(pages) and len(pages) >= 21
    extracted = "".join("".join(page.extract_text().split()) for page in pages)
    records = [
        json.loads(line) for line in (output / "selected-items.jsonl").read_text().splitlines()
    ]
    for record in records:
        assert record["item_id"] in extracted
        for value in record["item"].values():
            for part in value if isinstance(value, list) else [value]:
                assert "".join(part.split()) in extracted
    with pytest.raises(FileExistsError):
        module.render(output)
