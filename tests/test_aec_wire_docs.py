"""Synthetic reversible tables and one-shot transport checks; no live requests."""

import json
import sys
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from aec_wire_docs import (
    LEGEND,
    OneShotWireTransport,
    compact_schema_wire,
    decode_pages,
    encode_pages,
)
from screen_aec_grounded_docs import schema_wire
from test_aec_grounded_judgment import response

from aia_mp1.canonical_development import QWEN_MODEL_SHA, QWEN_SETTINGS
from aia_mp1.grounded_documentation import GroundedJudgment
from aia_mp1.judge import JudgeConfig
from aia_mp1.model_client import InstructorClient


def pages():
    return [
        {
            "id": f"P{i + 1}",
            "url": f"https://example.invalid/page{i}",
            "request": {
                "page": f"https://example.invalid/page{i}" if i == 0 else "literal-alias",
                "anchors": ['α "quote"\n', "$missing"],
                "claim": "Preserve  two spaces.",
            },
            "search_results": [
                {"anchor": "$missing", "matched": False, "occurrence_count": 0, "excerpt_ids": []},
                {
                    "anchor": 'α "quote"\n',
                    "matched": True,
                    "occurrence_count": 2,
                    "excerpt_ids": ["E2", "E1"],
                },
            ],
            "excerpts": [
                {"id": "E2", "text": "  Unicode α\n"},
                {"id": "E1", "text": ' "$page_url" '},
            ],
            "search_strategy": "Same literal strategy",
            "edition": "Synthetic edition",
            "evidence_status": "partial",
            "http_status": 200,
        }
        for i in range(2)
    ]


def typed_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def test_roundtrip_preserves_typed_values_order_unicode_markers_and_aliases():
    original = pages()
    original[1]["marker_like_data"] = {"columns": ["$missing"], "url_refs": [True, None, 1]}
    before = deepcopy(original)
    encoded = encode_pages(original)
    assert typed_json(decode_pages(encoded)) == typed_json(original)
    assert original == before
    assert encoded["url_refs"] == [0]
    assert encoded["shared"]["search_strategy"] == "Same literal strategy"
    assert "anchor_index" in encoded["search_columns"]
    assert decode_pages(encoded)[0]["search_results"][0]["anchor"] == "$missing"
    assert decode_pages(encoded)[1]["request"]["page"] == "literal-alias"
    assert "zero-based" in LEGEND and "absent, not null" in LEGEND


def test_missing_null_empty_error_and_different_strategies_remain_distinct():
    original = pages()
    original[0]["http_status"] = True
    original[1]["http_status"] = 1
    original[1]["search_strategy"] = "Different strategy"
    original[1]["search_results"][0]["occurrence_count"] = None
    del original[0]["search_results"][0]["occurrence_count"]
    original += [
        {
            "id": "P3",
            "request": {"page": "error", "anchors": ["a"], "claim": "Synthetic"},
            "error": "timeout",
            "search_results": [],
            "excerpts": [],
        },
        {"id": "P4", "search_results": None, "excerpts": None, "edition": None},
        {"id": "P5", "error": None},
    ]
    encoded = encode_pages(original)
    decoded = decode_pages(encoded)
    assert typed_json(decoded) == typed_json(original)
    assert "search_strategy" not in encoded["shared"]
    assert "http_status" not in encoded["shared"]
    assert type(decoded[0]["http_status"]) is bool and type(decoded[1]["http_status"]) is int
    assert "occurrence_count" not in decoded[0]["search_results"][0]
    assert decoded[1]["search_results"][0]["occurrence_count"] is None
    assert decoded[2]["excerpts"] == [] and decoded[3]["excerpts"] is None
    assert "excerpts" not in decoded[4]


def test_unresolvable_anchor_cannot_silently_change_search_meaning():
    original = pages()
    original[0]["search_results"][0]["anchor"] = "not in this request"
    with pytest.raises(ValueError, match="does not resolve"):
        encode_pages(original)


@pytest.mark.parametrize("index", [True, -1, 2, 0.0, "0"])
def test_invalid_anchor_indices_are_rejected(index):
    encoded = encode_pages(pages())
    row = encoded["rows"][0][encoded["columns"].index("search_results")][0]
    row[encoded["search_columns"].index("anchor_index")] = index
    with pytest.raises(ValueError, match="Invalid anchor index"):
        decode_pages(encoded)


@pytest.mark.parametrize("index", [True, -1, 2, 0.0, "0"])
def test_invalid_url_reference_indices_are_rejected(index):
    encoded = encode_pages(pages())
    encoded["url_refs"] = [index]
    with pytest.raises(ValueError, match="Invalid URL reference"):
        decode_pages(encoded)


def test_empty_pages_and_literal_null_anchor_remain_lossless():
    assert decode_pages(encode_pages([])) == []
    original = pages()
    original[0]["search_results"][0]["anchor"] = None
    assert typed_json(decode_pages(encode_pages(original))) == typed_json(original)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x["rows"][0].pop(),
        lambda x: x.update(missing=[[False, 0]]),
        lambda x: x.update(missing=[[0, 0]]),
        lambda x: x.update(search_missing=[[9, 0, 0]]),
    ],
)
def test_malformed_tables_are_rejected_instead_of_dropping_values(mutation):
    encoded = encode_pages(pages())
    mutation(encoded)
    with pytest.raises(ValueError):
        decode_pages(encoded)


def wire_inputs():
    cfg = JudgeConfig(
        base_url="http://127.0.0.1:18082/v1",
        model="/synthetic/qwen.gguf",
        model_sha256=QWEN_MODEL_SHA,
        **QWEN_SETTINGS,
    )
    messages = [
        {"role": "system", "content": "Original rubric and all instructions.\n" + LEGEND},
        {
            "role": "user",
            "content": json.dumps(
                {"online_documentation": encode_pages(pages())}, ensure_ascii=False
            ),
        },
    ]
    original = schema_wire(messages, cfg, GroundedJudgment)
    transformed = compact_schema_wire(original, messages, GroundedJudgment.model_json_schema())
    return cfg, messages, original, transformed


def test_exact_schema_compaction_preserves_all_annotations_messages_and_parameters():
    _, messages, original, transformed = wire_inputs()
    schema = GroundedJudgment.model_json_schema()
    pretty = json.dumps(schema, indent=2)
    compact = json.dumps(schema, separators=(",", ":"))
    assert json.loads(compact) == schema
    assert transformed["messages"][0]["content"] == original["messages"][0]["content"].replace(
        pretty, compact, 1
    )
    assert transformed["messages"][0]["content"].startswith(messages[0]["content"])
    assert transformed["messages"][1:] == original["messages"][1:]
    assert {k: v for k, v in transformed.items() if k != "messages"} == {
        k: v for k, v in original.items() if k != "messages"
    }
    assert original["messages"][0]["content"].count(pretty) == 1
    assert '"title":"GroundedJudgment"' in transformed["messages"][0]["content"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda w: w.update(response_format={"type": "json_schema"}),
        lambda w: w["messages"][0].update(content="Different original system"),
        lambda w: w["messages"][1].update(content="Different evidence"),
        lambda w: w["messages"][0].update(
            content=w["messages"][0]["content"]
            + json.dumps(GroundedJudgment.model_json_schema(), indent=2)
        ),
    ],
)
def test_schema_compactor_rejects_unexpected_wire_shapes(mutation):
    _, messages, original, _ = wire_inputs()
    mutation(original)
    with pytest.raises(ValueError):
        compact_schema_wire(original, messages, GroundedJudgment.model_json_schema())


def test_transport_forwards_exact_measured_body_once_preserving_headers_and_timeouts():
    _, _, original, transformed = wire_inputs()
    seen = []

    def handler(request):
        seen.append(request)
        assert json.loads(request.content) == transformed
        assert request.headers["content-length"] == str(len(request.content))
        assert request.headers["authorization"] == "Bearer synthetic-private-placeholder"
        assert request.extensions["timeout"] == {"read": 300}
        return httpx.Response(200, json={"synthetic": True})

    transport = OneShotWireTransport(original, transformed, inner=httpx.MockTransport(handler))
    request = httpx.Request(
        "POST",
        "http://127.0.0.1:18082/v1/chat/completions",
        json=original,
        headers={"authorization": "Bearer synthetic-private-placeholder"},
        extensions={"timeout": {"read": 300}},
    )
    assert transport.handle_request(request).status_code == 200
    assert request.content != seen[0].content
    assert seen[0].method == request.method and seen[0].url == request.url
    with pytest.raises(ValueError, match="cannot dispatch twice"):
        transport.handle_request(request)
    assert len(seen) == 1
    transport.close()


def test_transport_rejects_wire_drift_before_network_and_does_not_retry():
    _, _, original, transformed = wire_inputs()
    calls = []
    transport = OneShotWireTransport(
        original, transformed, inner=httpx.MockTransport(lambda r: calls.append(r))
    )
    request = httpx.Request(
        "POST", "http://127.0.0.1:18082/v1/chat/completions", json=original | {"max_tokens": 1}
    )
    with pytest.raises(ValueError, match="differs from measured"):
        transport.handle_request(request)
    with pytest.raises(ValueError, match="cannot dispatch twice"):
        transport.handle_request(request)
    assert calls == []
    transport.close()


@pytest.mark.parametrize("valid", [True, False])
def test_instructor_keeps_original_response_validation_and_raw_return(valid):
    cfg, messages, original, transformed = wire_inputs()
    value = response() if valid else {"malformed": "Synthetic invalid return"}
    raw = {
        "id": "synthetic",
        "object": "chat.completion",
        "created": 1,
        "model": cfg.model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": json.dumps(value)},
            }
        ],
    }
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=raw)

    transport = OneShotWireTransport(original, transformed, inner=httpx.MockTransport(handler))
    with InstructorClient(
        base_url=cfg.base_url,
        model=cfg.model,
        api_key="synthetic-placeholder",
        mode=cfg.mode,
        temperature=cfg.temperature,
        timeout_seconds=cfg.timeout_seconds,
        max_tokens=cfg.max_tokens,
        reasoning_effort=cfg.reasoning_effort,
        response_model=GroundedJudgment,
        _transport=transport,
    ) as client:
        result = client.generate(messages)
    assert seen == [transformed] and transport.calls == 1
    assert result.raw_response == raw
    if valid:
        assert result.item.model_dump() == value and result.error_type is None
    else:
        assert result.item is None and result.error_type is not None


def test_factoring_preserves_expanded_constraints_annotations_and_literal_reference_data():
    from aec_wire_docs import expanded_schema, factor_schema

    schema = GroundedJudgment.model_json_schema()
    schema["properties"]["title"] = {
        "type": "object",
        "default": {"$ref": "literal-not-a-schema-ref"},
        "enum": [{"$ref": "#/$defs/TaskEvidence", "title": "Literal title"}],
        "examples": [{"$dynamicRef": "literal-value", "$id": "literal-id"}],
    }
    schema["properties"]["$ref"] = {"type": "string", "const": "#/$defs/TaskEvidence"}
    before = deepcopy(schema)
    factored = factor_schema(schema)
    assert typed_json(expanded_schema(factored)) == typed_json(expanded_schema(schema))
    assert schema == before
    assert factored["properties"]["title"] == schema["properties"]["title"]
    assert factored["properties"]["$ref"] == schema["properties"]["$ref"]
    assert len(json.dumps(factored)) < len(json.dumps(schema))
    assert factored["title"] == schema["title"] == "GroundedJudgment"


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s.update({"$id": "https://example.invalid/schema"}),
        lambda s: s.update({"$anchor": "root"}),
        lambda s: s["properties"]["ratings"].update({"$dynamicRef": "#anchor"}),
        lambda s: s["properties"]["ratings"].update(
            {"title": "Reference sibling cannot disappear"}
        ),
        lambda s: s["properties"]["ratings"].update({"$ref": "#/$defs/Absent"}),
        lambda s: s["$defs"]["Judgment"].update({"$ref": "#/$defs/Judgment"}),
        lambda s: s["$defs"].update({"Unused": {"$ref": "#/$defs/Unused"}}),
        lambda s: s["$defs"]["Judgment"].update({"$defs": {"Nested": {"type": "string"}}}),
    ],
)
def test_factoring_rejects_schema_shapes_outside_the_equivalence_proof(change):
    from aec_wire_docs import factor_schema

    schema = GroundedJudgment.model_json_schema()
    change(schema)
    with pytest.raises(ValueError):
        factor_schema(schema)


def test_compactor_rejects_changed_instructor_wrapper_even_with_identical_schema():
    _, messages, original, _ = wire_inputs()
    original["messages"][0]["content"] += "Additional unpinned wrapper instruction"
    with pytest.raises(ValueError, match="exact pinned Instructor"):
        compact_schema_wire(original, messages, GroundedJudgment.model_json_schema())


def test_factored_wire_keeps_original_schema_validation_and_non_schema_text():
    from aec_wire_docs import INSTRUCTOR_PREFIX, INSTRUCTOR_SUFFIX, expanded_schema

    _, messages, original, _ = wire_inputs()
    factored_wire = compact_schema_wire(
        original, messages, GroundedJudgment.model_json_schema(), factor=True
    )
    tail = factored_wire["messages"][0]["content"].removeprefix(
        messages[0]["content"] + INSTRUCTOR_PREFIX
    )
    displayed = json.loads(tail.removesuffix(INSTRUCTOR_SUFFIX))
    assert typed_json(expanded_schema(displayed)) == typed_json(
        expanded_schema(GroundedJudgment.model_json_schema())
    )
    assert factored_wire["messages"][1:] == original["messages"][1:]


def test_rubric_minification_preserves_every_value_and_surrounding_instructions():
    from aec_wire_docs import compact_rubric_messages

    rubric = {
        "dimensions": [{"id": "D1", "title": 'α "literal"', "anchor": "  exact\ntext "}],
        "strict": True,
        "threshold": 0.8,
        "missing": None,
    }
    prefix = "Original unchanged instructions.\n\nRubric:\n"
    suffix = "\n\nOriginal FINAL instructions.\n\n" + LEGEND
    messages = [
        {"role": "system", "content": prefix + json.dumps(rubric, ensure_ascii=False) + suffix},
        {"role": "user", "content": "Unchanged evidence"},
    ]
    before = deepcopy(messages)
    compact = compact_rubric_messages(messages, rubric)
    assert messages == before and compact[1:] == messages[1:]
    assert compact[0]["content"].startswith(prefix) and compact[0]["content"].endswith(suffix)
    decoded = json.loads(compact[0]["content"][len(prefix) : -len(suffix)])
    assert typed_json(decoded) == typed_json(rubric)
    assert len(compact[0]["content"]) < len(messages[0]["content"])
    with pytest.raises(ValueError, match="differs from frozen"):
        compact_rubric_messages(messages, rubric | {"strict": 1})
    with pytest.raises(ValueError, match="rubric boundary"):
        compact_rubric_messages([{"role": "system", "content": "No original marker"}], rubric)


def test_transport_does_not_retry_after_unknown_transport_failure():
    _, _, original, transformed = wire_inputs()
    calls = []

    def fail(request):
        calls.append(request)
        raise httpx.ReadTimeout("Synthetic unknown outcome", request=request)

    transport = OneShotWireTransport(original, transformed, inner=httpx.MockTransport(fail))
    request = httpx.Request("POST", "http://127.0.0.1:18082/v1/chat/completions", json=original)
    with pytest.raises(httpx.ReadTimeout):
        transport.handle_request(request)
    with pytest.raises(ValueError, match="cannot dispatch twice"):
        transport.handle_request(request)
    assert len(calls) == 1
    transport.close()
