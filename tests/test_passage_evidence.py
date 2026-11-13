"""Synthetic passage integrity and transport tests; no human labels."""

import json
from copy import deepcopy

import httpx
import pytest
from test_compact_evidence import envelope
from test_compact_evidence import sample as sample

from aia_mp1.model_client import InstructorClient
from aia_mp1.passage_evidence import (
    PassageEvidenceClient,
    PassageJudgment,
    parse_passage,
    passage_catalog,
    passage_input,
    resolved_passages,
    validate_passage,
    validate_passage_input,
)


@pytest.fixture
def case(sample):
    content, rubric, _ = sample
    report = {
        f"D{i}": {
            "requirement": "R.task",
            "evidence": ["C.answer"],
            "counter": [],
            "decision": 1,
            "justification": "Synthetic assessment only.",
        }
        for i in range(1, 7)
    }
    return passage_input(content, rubric), rubric, report


def test_input_adds_only_deterministic_location_index(sample):
    content, rubric, _ = sample
    before = deepcopy(content)
    augmented = passage_input(content, rubric)
    assert content == before
    assert {k: v for k, v in augmented.items() if k != "passage_index"} == content
    assert augmented == passage_input(deepcopy(content), deepcopy(rubric))
    catalog = validate_passage_input(augmented, rubric)
    assert catalog["C.steps.1"] == {
        "path": "/untrusted_item/steps/1",
        "text": "Inspect its identifier.",
    }
    assert (
        catalog["R.source.0"]["text"]
        == content["untrusted_reference_context"]["sources"][0]["text"]
    )
    assert catalog["R.D6.fail"]["text"] == rubric["dimensions"][5]["fail_anchor"]


def test_long_passage_is_resolved_exactly_without_quote_generation(case):
    content, rubric, report = case
    text = "Synthetic complete passage with meaningful spacing.\n" * 12
    content["untrusted_item"]["answer"] = text
    parsed = parse_passage(envelope(report))
    assert validate_passage(parsed, content, rubric).D1.decision == 1
    resolved = resolved_passages(parsed, content, rubric)
    assert resolved["D1"]["evidence"][0]["text"] == text
    assert resolved["D1"]["requirement"]["id"] == "R.task"
    assert "text" not in report["D1"]


@pytest.mark.parametrize(
    "mutation",
    ["unknown", "wrong_role", "foreign_anchor", "conflict", "counter_role", "case", "negative"],
)
def test_invalid_citations_reject_without_score_projection(case, mutation):
    content, rubric, report = case
    if mutation == "unknown":
        report["D1"]["evidence"] = ["C.missing"]
    elif mutation == "wrong_role":
        report["D1"]["evidence"] = ["R.source.0"]
    elif mutation == "foreign_anchor":
        report["D1"]["requirement"] = "R.D2.pass"
    elif mutation == "conflict":
        report["D1"]["counter"] = ["C.answer"]
    elif mutation == "counter_role":
        report["D1"]["counter"] = ["R.source.0"]
    elif mutation == "case":
        report["D1"]["evidence"] = ["c.answer"]
    else:
        report["D1"]["evidence"] = ["C.steps.-1"]
    with pytest.raises(ValueError):
        validate_passage(PassageJudgment.model_validate(report), content, rubric)


@pytest.mark.parametrize("mutation", ["redirect", "missing", "extra", "labels"])
def test_input_index_is_rebuilt_and_verified(case, mutation):
    content, rubric, _ = case
    if mutation == "redirect":
        content["passage_index"]["C.answer"] = "/untrusted_item/safety_info"
    elif mutation == "missing":
        del content["passage_index"]["C.answer"]
    elif mutation == "extra":
        content["passage_index"]["R.human_label"] = "/human_labels/D1"
    else:
        content["human_labels"] = {"D1": 1}
    with pytest.raises(ValueError):
        validate_passage_input(content, rubric)


def test_metadata_never_becomes_a_citable_passage(sample):
    content, rubric, _ = sample
    content["untrusted_reference_context"]["human_labels"] = {"D1": 1}
    catalog = passage_catalog(content, rubric)
    assert all("label" not in p["path"] for p in catalog.values())


@pytest.mark.parametrize(
    "mutation", ["missing_dimension", "boolean", "extra", "empty_evidence", "blank_justification"]
)
def test_existing_strict_judgment_requirements_remain(case, mutation):
    report = case[2]
    if mutation == "missing_dimension":
        del report["D6"]
    elif mutation == "boolean":
        report["D1"]["decision"] = True
    elif mutation == "extra":
        report["citations"] = []
    elif mutation == "empty_evidence":
        report["D1"]["evidence"] = []
    else:
        report["D1"]["justification"] = "   "
    with pytest.raises(ValueError):
        parse_passage(envelope(report))


@pytest.mark.parametrize("bad", [False, True])
def test_single_call_retains_raw_and_validates_ids(case, bad):
    content, rubric, report = case
    if bad:
        report["D2"]["evidence"] = ["C.fabricated"]
    raw = envelope(report)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=raw)

    messages = [
        {"role": "system", "content": "Synthetic test only."},
        {"role": "user", "content": json.dumps(content)},
    ]
    original = deepcopy(messages)
    with InstructorClient(
        base_url="http://127.0.0.1:8081/v1",
        model="synthetic-model",
        api_key="synthetic-key",
        response_model=PassageJudgment,
        _transport=httpx.MockTransport(handler),
    ) as client:
        result = PassageEvidenceClient(client, rubric).generate(messages)
        content["passage_index"]["C.answer"] = "/wrong"
        with pytest.raises(ValueError):
            PassageEvidenceClient(client, rubric).generate(
                [messages[0], {"role": "user", "content": json.dumps(content)}]
            )
    assert len(calls) == 1 and messages == original
    assert result.raw_response == raw and (result.item is None) == bad
    assert result.error_type == ("EvidenceValidationError" if bad else None)
