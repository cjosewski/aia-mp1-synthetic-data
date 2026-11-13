"""Synthetic citation and transport cases, never human/reference labels."""

import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.evidence_judge import (
    CANDIDATE_FIELDS,
    EvidenceClient,
    EvidenceJudgment,
    citation_catalog,
    parse_evidence,
    validate_evidence,
)
from aia_mp1.model_client import InstructorClient


@pytest.fixture
def case():
    content = {
        "untrusted_item": {
            "question": "How do I inspect a synthetic record?",
            "answer": "Inspect the synthetic record and report its identifier.",
            "equipment_problem": "Report a synthetic identifier without changes.",
            "tools_required": ["Synthetic reader"],
            "steps": ["Open a synthetic copy.", "Read its identifier.", "Report that identifier."],
            "safety_info": "Avoid accidental modification by opening a disposable copy.",
            "tips": ["Report missing identifiers explicitly instead of guessing a value."],
        },
        "untrusted_reference_context": {
            "task": {"brief": "Inspect and report a synthetic identifier without changes."},
            "sources": [{"text": "Synthetic reader supports inspecting an identifier."}],
        },
    }
    rubric = json.loads(Path("config/rubric.json").read_text())
    report = {
        d: {
            "requirement": {
                "path": "/untrusted_reference_context/task/brief",
                "quote": "report a synthetic identifier",
            },
            "candidate_evidence": [
                {"path": "/untrusted_item/answer", "quote": "report its identifier"}
            ],
            "counterevidence": [],
            "missing_information": "",
            "searched_fields": [],
            "decision": 1,
            "justification": "Synthetic fixture judgment; not a human label.",
        }
        for d in DIMENSIONS
    }
    return content, rubric, report


def completion(report, finish="stop"):
    return {
        "id": "synthetic-evidence",
        "object": "chat.completion",
        "created": 1,
        "model": "synthetic-model",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish,
                "message": {"role": "assistant", "content": json.dumps(report)},
            }
        ],
    }


def test_projection_preserves_decisions_without_claiming_semantic_validation(case):
    content, rubric, report = case
    report["D2"]["decision"] = 0
    frozen = deepcopy((content, rubric, report))
    judgment = validate_evidence(EvidenceJudgment.model_validate(report), content, rubric)
    assert judgment.decisions() == {d: int(d != "D2") for d in DIMENSIONS}
    assert set(judgment.D2.model_dump()) == {"decision", "justification"}
    assert (content, rubric, report) == frozen
    # Mere quote validity accepts even an irrelevant synthetic assessment.
    # No test pretends that structural validation establishes technical truth.


@pytest.mark.parametrize(
    "path,quote",
    [
        ("/untrusted_item/answer", "fabricated quotation"),
        ("/untrusted_item/steps/-1", "Report that identifier."),
        ("/untrusted_item/steps/99", "Report that identifier."),
        ("/untrusted_item/steps/00", "Open a synthetic copy."),
        ("/untrusted_item/steps", "Open a synthetic copy."),
        ("/untrusted_item/answer", "report  its identifier"),
        ("/untrusted_reference_context/task/brief", "report a synthetic identifier"),
    ],
)
def test_candidate_quote_must_match_its_exact_allowed_leaf(case, path, quote):
    content, rubric, report = case
    report["D1"]["candidate_evidence"] = [{"path": path, "quote": quote}]
    with pytest.raises(ValueError, match="citation"):
        validate_evidence(EvidenceJudgment.model_validate(report), content, rubric)


def test_requirement_cannot_cite_candidate_or_another_dimension(case):
    content, rubric, report = case
    for citation in [
        {"path": "/untrusted_item/answer", "quote": "report its identifier"},
        {
            "path": "/rubric/dimensions/1/pass_anchor",
            "quote": rubric["dimensions"][1]["pass_anchor"],
        },
    ]:
        report["D1"]["requirement"] = citation
        with pytest.raises(ValueError, match="citation"):
            validate_evidence(EvidenceJudgment.model_validate(report), content, rubric)


def test_own_anchor_sources_and_list_quotes_are_supported(case):
    content, rubric, report = case
    report["D1"]["requirement"] = {
        "path": "/rubric/dimensions/0/pass_anchor",
        "quote": rubric["dimensions"][0]["pass_anchor"],
    }
    report["D3"]["requirement"] = {
        "path": "/untrusted_reference_context/sources/0/text",
        "quote": "supports inspecting an identifier",
    }
    report["D6"]["candidate_evidence"] = [
        {"path": "/untrusted_item/tips/0", "quote": "instead of guessing a value"}
    ]
    assert (
        validate_evidence(EvidenceJudgment.model_validate(report), content, rubric).D6.decision == 1
    )


@pytest.mark.parametrize("duplicate", [False, True])
def test_counterevidence_is_verified_and_not_duplicated(case, duplicate):
    content, rubric, report = case
    report["D1"]["counterevidence"] = [deepcopy(report["D1"]["candidate_evidence"][0])]
    if not duplicate:
        report["D1"]["counterevidence"][0]["quote"] = "fabricated counterevidence"
    with pytest.raises(ValueError):
        validate_evidence(EvidenceJudgment.model_validate(report), content, rubric)


@pytest.mark.parametrize(
    "decision,fields",
    [
        (1, list(CANDIDATE_FIELDS)),
        (0, ["answer"]),
        (0, [*CANDIDATE_FIELDS, "answer"]),
    ],
)
def test_absence_claim_cannot_skip_fields_or_support_a_pass(case, decision, fields):
    report = case[2]
    report["D1"].update(
        missing_information="Synthetic missing requirement",
        searched_fields=fields,
        decision=decision,
    )
    with pytest.raises(ValueError):
        EvidenceJudgment.model_validate(report)


def test_complete_search_declaration_is_not_a_semantic_proof(case):
    content, rubric, report = case
    report["D1"].update(
        missing_information="Synthetic missing requirement",
        searched_fields=list(CANDIDATE_FIELDS),
        decision=0,
    )
    assert (
        validate_evidence(EvidenceJudgment.model_validate(report), content, rubric).D1.decision == 0
    )


@pytest.mark.parametrize("mutation", ["boolean", "string", "missing", "extra", "no_evidence"])
def test_strict_output_contract(case, mutation):
    report = case[2]
    if mutation == "boolean":
        report["D1"]["decision"] = True
    elif mutation == "string":
        report["D1"]["decision"] = "1"
    elif mutation == "missing":
        del report["D6"]
    elif mutation == "extra":
        report["expected_labels"] = "not permitted"
    else:
        report["D1"]["candidate_evidence"] = []
    with pytest.raises(ValueError):
        EvidenceJudgment.model_validate(report)


@pytest.mark.parametrize("kind", ["truncated", "duplicates", "fenced", "multiple"])
def test_raw_contract_rejects_ambiguous_or_incomplete_output(case, kind):
    raw = completion(case[2])
    if kind == "truncated":
        raw["choices"][0]["finish_reason"] = "length"
    elif kind == "duplicates":
        raw["choices"][0]["message"]["content"] = '{"D1": {}, "D1": {}}'
    elif kind == "fenced":
        raw["choices"][0]["message"]["content"] = "```json\n" + json.dumps(case[2]) + "\n```"
    else:
        raw["choices"].append(deepcopy(raw["choices"][0]))
    with pytest.raises(ValueError):
        parse_evidence(raw)


def test_input_rejects_labels_and_noncanonical_fields(case):
    content, rubric, _ = case
    content["human_labels"] = {"D1": 1}
    with pytest.raises(ValueError, match="only candidate"):
        citation_catalog(content, rubric)


@pytest.mark.parametrize(
    "raw",
    [
        {"choices": [None]},
        {"choices": ["invalid"]},
        {"choices": [{"finish_reason": "stop", "message": None}]},
        {"choices": [{"finish_reason": "stop", "message": []}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": None}}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": {}}}]},
    ],
)
def test_malformed_provider_shapes_fail_as_validation_errors(raw):
    # Callers can record a failed completion instead of an unexpected crash
    # leaving a request with an unknown outcome.
    with pytest.raises(ValueError):
        parse_evidence(raw)


@pytest.mark.parametrize("invalid_quote", [False, True])
def test_real_transport_makes_one_call_preserves_raw_and_never_repairs(case, invalid_quote):
    content, rubric, report = case
    if invalid_quote:
        report["D2"]["candidate_evidence"][0]["quote"] = "fabricated citation"
    raw = completion(report)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=raw)

    messages = [
        {"role": "system", "content": "Synthetic test only."},
        {"role": "user", "content": json.dumps(content)},
    ]
    frozen = deepcopy(messages)
    with InstructorClient(
        base_url="http://127.0.0.1:8081/v1",
        model="synthetic-model",
        api_key="synthetic-test-key",
        response_model=EvidenceJudgment,
        _transport=httpx.MockTransport(handler),
    ) as client:
        result = EvidenceClient(client, rubric).generate(messages)
    assert len(calls) == 1
    assert messages == frozen
    assert result.raw_response == raw
    assert (result.item is None) == invalid_quote
    assert result.error_type == ("EvidenceValidationError" if invalid_quote else None)
    if not invalid_quote:
        assert result.item.decisions() == dict.fromkeys(DIMENSIONS, 1)
