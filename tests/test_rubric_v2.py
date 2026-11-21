"""The frozen v2 rubric loads only byte-for-byte; its schemas take exactly eight binary labels."""

import json
import shutil

import pytest
from pydantic import ValidationError
from v2_fixtures import RUBRIC_V2, decisions

from aia_mp1 import rubric_v2
from aia_mp1.rubric_v2 import (
    DIMENSIONS_V2,
    RUBRIC_V2_SHA256,
    DecisionsV2,
    HumanLabelV2,
    boundary_triggered,
    load_rubric_v2,
)
from aia_mp1.schemas import CATEGORIES
from aia_mp1.tracing import digest


def test_frozen_file_loads_and_matches_its_recorded_hash():
    text = RUBRIC_V2.read_text(encoding="utf-8")
    assert digest(text) == RUBRIC_V2_SHA256
    rubric = load_rubric_v2()
    assert rubric == load_rubric_v2(text) == json.loads(text)
    assert [d["id"] for d in rubric["dimensions"]] == list(DIMENSIONS_V2)


def test_one_byte_change_is_refused_even_when_the_json_is_equivalent(tmp_path):
    copy = tmp_path / "rubric-v2.json"
    shutil.copyfile(RUBRIC_V2, copy)
    text = copy.read_text(encoding="utf-8")
    assert text.endswith("\n")
    copy.write_text(text[:-1] + " ", encoding="utf-8")
    changed = copy.read_text(encoding="utf-8")
    assert json.loads(changed) == json.loads(text)
    with pytest.raises(ValueError, match="sha256"):
        load_rubric_v2(changed)


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda r: r.update(status="draft"), "frozen"),
        (lambda r: r.update(version="aec-rubric-v3"), "version"),
        (lambda r: r["dimensions"].reverse(), "dimension"),
        (lambda r: r.update(label_values=[0, 1, 2]), "label_values"),
        (lambda r: r["per_dimension_pass_rate_minimum"].pop("tips"), "minimum"),
        (lambda r: r["overall_pass"].update(rule="any_dimension_passes"), "overall"),
        (lambda r: r["professional_boundary_triggers"].update(status="proposed"), "boundary"),
        (lambda r: r["professional_boundary_triggers"]["tasks"].pop(), "boundary"),
    ],
)
def test_rules_hold_even_for_a_rehashed_rubric(monkeypatch, mutate, message):
    rubric = json.loads(RUBRIC_V2.read_text(encoding="utf-8"))
    mutate(rubric)
    text = json.dumps(rubric)
    monkeypatch.setattr(rubric_v2, "RUBRIC_V2_SHA256", digest(text))
    with pytest.raises(ValueError, match=message):
        load_rubric_v2(text)


@pytest.mark.parametrize("value", [True, False, "1", 1.0, -1, 2, None])
def test_decisions_are_strictly_binary(value):
    with pytest.raises(ValidationError):
        DecisionsV2.model_validate(decisions(tips=value))


def test_decisions_require_exactly_the_eight_dimensions():
    missing = decisions()
    missing.pop("clarity")
    for invalid in (missing, decisions(D1=1)):
        with pytest.raises(ValidationError):
            DecisionsV2.model_validate(invalid)
    assert DecisionsV2.model_validate(decisions(safety=0)).model_dump() == decisions(safety=0)


def label(**changes) -> dict:
    return {
        "label_id": "synthetic-label",
        "assessment_id": "synthetic-assessment",
        "item_id": "synthetic-item",
        "trace_id": "synthetic-trace",
        "payload_sha256": "0" * 64,
        "rubric_version": "aec-rubric-v2",
        "rubric_sha256": RUBRIC_V2_SHA256,
        "reviewer": "Synthetic reviewer",
        "timestamp": "2026-11-20T00:00:00+00:00",
        "decisions": decisions(),
        "review_stage": "blind",
    } | changes


def test_label_requires_a_stage_and_keeps_multiline_notes():
    plain = HumanLabelV2.model_validate(label()).model_dump(mode="json")
    assert "packet_id" not in plain and "review_id" not in plain
    without_stage = label()
    without_stage.pop("review_stage")
    for invalid in (without_stage, label(review_stage="adjudicated"), label(packet_id="P")):
        with pytest.raises(ValidationError):
            HumanLabelV2.model_validate(invalid)
    notes = "First line.\n\n  Indented second line.\n"
    value = HumanLabelV2.model_validate(label(notes=notes, packet_id="P", review_id="R01"))
    assert value.model_dump(mode="json")["notes"] == notes
    assert value.review_id == "R01"


def test_boundary_classification_is_read_from_the_frozen_rubric():
    rubric = load_rubric_v2()
    task_ids = [f"{c}-{n:02d}" for c in CATEGORIES for n in range(1, 11)]
    assert not any(boundary_triggered(rubric, task_id) for task_id in task_ids)
    with pytest.raises(ValueError, match="classification"):
        boundary_triggered(rubric, "gis_scripting-11")
    rubric["professional_boundary_triggers"]["tasks"][0]["triggered"] = True
    assert boundary_triggered(
        rubric, rubric["professional_boundary_triggers"]["tasks"][0]["task_id"]
    )
