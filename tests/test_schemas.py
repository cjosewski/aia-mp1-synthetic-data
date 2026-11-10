"""Synthetic contract fixtures, not generated or human-labeled assessment data."""

import json

import pytest
from pydantic import ValidationError

from aia_mp1.schemas import GeneratedItem, QAItem


def payload():
    return {
        "question": "How can I validate the units in a standalone test calculation?",
        "answer": "Inspect the input units, convert a test value, and compare with a known result.",
        "equipment_problem": "Unit mismatch in a synthetic calculation",
        "tools_required": ["Python standard library"],
        "steps": [
            "Read the input unit label.",
            "Convert one known input.",
            "Compare the expected and actual result.",
        ],
        "safety_info": "Incorrect units can change the result by orders of magnitude; verify a known value before using any output.",
        "tips": [
            "A dimensionless ratio can expose a scale factor that a rounded absolute difference hides."
        ],
    }


def envelope():
    return {
        "run_id": "test-run",
        "trace_id": "trace-1",
        "item_id": "item-1",
        "attempt_id": "attempt-1",
        "category": "gis_scripting",
        "prompt_variant": "baseline",
        "prompt_hash": "a" * 64,
        "model": "synthetic-test-fixture",
        "source_refs": [],
        "item": payload(),
    }


def test_payload_has_exact_canonical_schema_and_strips_text():
    data = payload()
    data["question"] = "  " + data["question"] + "\n"
    data["tools_required"] = [" Python standard library "]
    item = QAItem.model_validate(data)
    assert item.question == payload()["question"]
    assert item.tools_required == ["Python standard library"]
    assert set(item.model_dump()) == set(payload())
    assert set(QAItem.model_json_schema()["properties"]) == set(payload())
    assert QAItem.model_json_schema()["additionalProperties"] is False


def test_legacy_key_is_normalized_without_mutating_raw_evidence():
    data = payload()
    data["problem"] = data.pop("equipment_problem")
    before = json.dumps(data)
    item = QAItem.model_validate(data)
    assert item.equipment_problem == payload()["equipment_problem"]
    assert "problem" not in item.model_dump()
    assert json.dumps(data) == before


def test_conflicting_legacy_and_canonical_values_are_rejected():
    data = {**payload(), "problem": "A different problem"}
    with pytest.raises(ValidationError, match="conflicting problem"):
        QAItem.model_validate(data)


def test_equal_legacy_and_canonical_values_have_one_canonical_output():
    item = QAItem.model_validate({**payload(), "problem": payload()["equipment_problem"]})
    assert set(item.model_dump()) == set(payload())


@pytest.mark.parametrize("field", list(payload()))
def test_every_payload_field_is_required(field):
    data = payload()
    del data[field]
    with pytest.raises(ValidationError):
        QAItem.model_validate(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("question", " \n"),
        ("answer", ""),
        ("equipment_problem", "\t"),
        ("safety_info", " "),
        ("question", 5),
        ("answer", True),
        ("tools_required", "Python"),
        ("tools_required", ("Python",)),
        ("tools_required", []),
        ("tips", []),
        ("steps", ["One", "Two"]),
        ("steps", ["One", " ", "Three"]),
        ("tips", [" "]),
        ("tools_required", [1]),
    ],
)
def test_invalid_types_blank_values_and_list_minima_fail(field, value):
    with pytest.raises(ValidationError):
        QAItem.model_validate({**payload(), field: value})


def test_payload_metadata_is_forbidden():
    with pytest.raises(ValidationError):
        QAItem.model_validate({**payload(), "trace_id": "wrong-layer"})


def test_envelope_json_round_trip_keeps_identity_and_retry_lineage():
    data = {**envelope(), "parent_attempt_id": "attempt-0"}
    original = GeneratedItem.model_validate(data)
    restored = GeneratedItem.model_validate_json(original.model_dump_json())
    assert restored == original
    assert restored.schema_version == "1"
    assert restored.parent_attempt_id == "attempt-0"
    assert "trace_id" not in restored.item.model_dump()


@pytest.mark.parametrize(
    "field,value",
    [
        ("category", "unknown"),
        ("trace_id", " "),
        ("source_refs", [""]),
        ("schema_version", "2"),
        ("parent_attempt_id", ""),
    ],
)
def test_envelope_rejects_invalid_metadata(field, value):
    with pytest.raises(ValidationError):
        GeneratedItem.model_validate({**envelope(), field: value})


def test_envelope_requires_source_refs_and_forbids_unknown_fields():
    data = envelope()
    del data["source_refs"]
    with pytest.raises(ValidationError):
        GeneratedItem.model_validate(data)
    with pytest.raises(ValidationError):
        GeneratedItem.model_validate({**envelope(), "secret": "must-not-be-here"})
