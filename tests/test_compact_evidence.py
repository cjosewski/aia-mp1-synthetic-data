"""Synthetic protocol validation; no generated human labels or live services."""

import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from aia_mp1.compact_evidence import (
    CompactEvidenceClient,
    CompactJudgment,
    compact_catalog,
    parse_compact,
    validate_compact,
)
from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.model_client import InstructorClient


@pytest.fixture
def sample():
    content = {
        "untrusted_item": {
            "question": "Synthetic inspection question.",
            "answer": "Inspect a synthetic record.",
            "equipment_problem": "Read a synthetic record without changes.",
            "tools_required": ["Synthetic reader"],
            "steps": ["Open synthetic copy.", "Inspect its identifier.", "Report identifier."],
            "safety_info": "Use a copy to prevent changing the original record.",
            "tips": ["Record missing identifiers rather than guessing."],
        },
        "untrusted_reference_context": {
            "task": {"brief": "Inspect a synthetic record and report its identifier."},
            "sources": [{"text": "Synthetic reader can inspect a record."}],
        },
    }
    rubric = json.loads(Path("config/rubric.json").read_text())
    report = {
        "citations": [
            {"path": "task", "quote": "Inspect a synthetic record"},
            {"path": "answer", "quote": "Inspect a synthetic record."},
            {"path": "steps.1", "quote": "Inspect its identifier."},
        ]
    }
    report.update(
        {
            d: {
                "requirement": 0,
                "evidence": [1, 2],
                "counter": [],
                "decision": 1,
                "justification": "Synthetic assessment only.",
            }
            for d in DIMENSIONS
        }
    )
    return content, rubric, report


def envelope(report):
    return {
        "id": "synthetic",
        "object": "chat.completion",
        "created": 1,
        "model": "synthetic-model",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": json.dumps(report)},
            }
        ],
    }


def test_shared_quotes_project_without_mutation(sample):
    content, rubric, report = sample
    before = deepcopy(sample)
    projected = validate_compact(parse_compact(envelope(report)), content, rubric)
    assert projected.decisions() == dict.fromkeys(DIMENSIONS, 1)
    assert sample == before
    assert set(projected.D1.model_dump()) == {"decision", "justification"}


@pytest.mark.parametrize("index", [-1, 24, 5, True, "1"])
def test_invalid_and_dangling_indices_rejected(sample, index):
    content, rubric, report = sample
    report["D1"]["evidence"] = [index]
    with pytest.raises(ValueError):
        validate_compact(CompactJudgment.model_validate(report), content, rubric)


@pytest.mark.parametrize(
    "change",
    ["source_as_evidence", "candidate_requirement", "foreign_anchor", "conflict", "counter_source"],
)
def test_citation_roles_and_dimension_ownership(sample, change):
    content, rubric, report = sample
    if change == "source_as_evidence":
        report["D1"]["evidence"] = [0]
    elif change == "candidate_requirement":
        report["D1"]["requirement"] = 1
        report["D1"]["evidence"] = [2]
    elif change == "foreign_anchor":
        report["citations"][0] = {
            "path": "D2.pass",
            "quote": rubric["dimensions"][1]["pass_anchor"],
        }
    elif change == "conflict":
        report["D1"]["counter"] = [1]
    else:
        report["D1"]["counter"] = [0]
    with pytest.raises(ValueError):
        validate_compact(CompactJudgment.model_validate(report), content, rubric)


@pytest.mark.parametrize(
    "path,quote",
    [
        ("answer", "Invented quotation"),
        ("steps.-1", "Report identifier."),
        ("steps.01", "Inspect its identifier."),
        ("expected_labels", "Synthetic pass"),
        ("answer", "Inspect  a synthetic record."),
    ],
)
def test_quotes_are_verbatim_at_the_cited_allowed_location(sample, path, quote):
    content, rubric, report = sample
    report["citations"][1] = {"path": path, "quote": quote}
    with pytest.raises(ValueError):
        validate_compact(CompactJudgment.model_validate(report), content, rubric)


def test_four_candidate_citations_are_valid_in_new_contract(sample):
    content, rubric, report = sample
    report["citations"] += [
        {"path": "safety_info", "quote": "prevent changing the original record"},
        {"path": "tips.0", "quote": "rather than guessing"},
    ]
    report["D1"]["evidence"] = [1, 2, 3, 4]
    assert (
        validate_compact(CompactJudgment.model_validate(report), content, rubric).D1.decision == 1
    )


def test_injected_metadata_has_no_citable_alias(sample):
    content, rubric, _ = sample
    content["untrusted_reference_context"]["human_labels"] = {"D1": 1}
    candidates, references = compact_catalog(content, rubric)
    assert all("label" not in key for key in candidates | references)
    content["human_labels"] = {"D1": 1}
    with pytest.raises(ValueError):
        compact_catalog(content, rubric)


@pytest.mark.parametrize(
    "change", ["missing_dimension", "boolean", "extra", "empty", "duplicate_key", "truncated"]
)
def test_contract_rejects_invalid_responses(sample, change):
    report = sample[2]
    if change == "missing_dimension":
        del report["D6"]
    elif change == "boolean":
        report["D1"]["decision"] = True
    elif change == "extra":
        report["human_labels"] = {}
    elif change == "empty":
        report["D1"]["evidence"] = []
    raw = envelope(report)
    if change == "duplicate_key":
        raw["choices"][0]["message"]["content"] = '{"citations": [], "citations": []}'
    if change == "truncated":
        raw["choices"][0]["finish_reason"] = "length"
    with pytest.raises(ValueError):
        parse_compact(raw)


@pytest.mark.parametrize("bad_quote", [False, True])
def test_transport_has_one_attempt_retains_full_evidence_and_rejects_bad_quotes(sample, bad_quote):
    content, rubric, report = sample
    if bad_quote:
        report["citations"][1]["quote"] = "Fabricated quotation"
    raw = envelope(report)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=raw)

    messages = [
        {"role": "system", "content": "Synthetic test only."},
        {"role": "user", "content": json.dumps(content)},
    ]
    before = deepcopy(messages)
    with InstructorClient(
        base_url="http://127.0.0.1:8081/v1",
        model="synthetic-model",
        api_key="synthetic-key",
        response_model=CompactJudgment,
        _transport=httpx.MockTransport(handler),
    ) as client:
        result = CompactEvidenceClient(client, rubric).generate(messages)
    assert len(calls) == 1 and messages == before and result.raw_response == raw
    assert (result.item is None) == bad_quote
    assert result.error_type == ("EvidenceValidationError" if bad_quote else None)
