"""Synthetic case-specific response contract, native normalization and validation order."""

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import aec_conformance_docs as conformance
from aec_wire_docs import INSTRUCTOR_PREFIX, INSTRUCTOR_SUFFIX, expanded_schema

from aia_mp1.grounded_documentation import GroundedJudgment

CASE_ID = "SYNTHETIC-conformance-only"
TASK = "SYNTHETIC task: inspect a pretend record and describe the check."


def case():
    return {
        "untrusted_item": {
            "question": "SYNTHETIC: inspect a pretend record safely.",
            "answer": "SYNTHETIC answer, not an actual evaluation item.",
            "equipment_problem": "SYNTHETIC mock record problem.",
            "tools_required": ["SYNTHETIC-tool"],
            "steps": ["SYNTHETIC step one", "SYNTHETIC step two"],
            "safety_info": "SYNTHETIC hazard and precaution.",
            "tips": ["SYNTHETIC first tip", "SYNTHETIC second tip"],
        },
        "untrusted_reference_context": {"task": {"brief": TASK}},
    }


def pages():
    return [
        {"id": "P1", "excerpts": [{"id": "E1", "text": "SYNTHETIC documentation passage."}]},
        {"id": "P2", "excerpts": [{"id": "E1", "text": "SYNTHETIC second passage."}]},
    ]


def specimen():
    note = "SYNTHETIC only"
    return {
        "task_checks": [
            {"candidate_ids": ["answer"], "status": "uncertain", "note": note, "task_quote": TASK}
        ],
        "safety": {"candidate_ids": ["safety_info"], "status": "uncertain", "note": note},
        "bindings": [
            {"candidate_ids": ["question"], "status": "uncertain", "note": note, "task_quote": TASK}
        ],
        "tips": [
            {
                "candidate_ids": [f"tips[{i}]"],
                "status": "uncertain",
                "note": note,
                "tip_id": f"tips[{i}]",
            }
            for i in range(2)
        ],
        "documentation": [
            {
                "candidate_id": "answer",
                "passage_id": "P1.E1",
                "quote": None,
                "status": "uncertain",
                "note": note,
            }
        ],
        "ratings": {
            f"D{i}": {"decision": 0, "justification": "SYNTHETIC parser fixture, not a rating."}
            for i in range(1, 7)
        },
    }


def supplied():
    return conformance.contract(CASE_ID, case(), pages())


def text(value):
    return json.dumps(value, ensure_ascii=False)


def test_valid_specimen_passes_overlay_canonical_model_and_grounding_without_change():
    raw = text(specimen())
    parsed, ratings = conformance.validate_raw(raw, supplied(), CASE_ID, case(), pages())
    assert parsed.model_dump() == specimen()
    assert ratings.model_dump() == specimen()["ratings"]


FAULTS = {
    "extra_safety_field": lambda x: x["safety"].update(note_detail="SYNTHETIC extra"),
    "candidate_as_task_quote": lambda x: x["task_checks"][0].update(
        task_quote=case()["untrusted_item"]["answer"]
    ),
    "task_span_not_full_task": lambda x: x["bindings"][0].update(task_quote=TASK[:20]),
    "page_only_id": lambda x: x["documentation"][0].update(passage_id="P1"),
    "foreign_passage_id": lambda x: x["documentation"][0].update(passage_id="P99.E1"),
    "foreign_safety_id": lambda x: x["safety"].update(candidate_ids=["answer"]),
    "nonnull_exact_quote": lambda x: x["documentation"][0].update(
        quote="SYNTHETIC documentation passage."
    ),
    "foreign_candidate_id": lambda x: x["task_checks"][0].update(candidate_ids=["foreign"]),
    "foreign_document_candidate": lambda x: x["documentation"][0].update(candidate_id="foreign"),
    "foreign_tip_id": lambda x: x["tips"][0].update(tip_id="tips[99]"),
    "non_tip_as_tip_id": lambda x: x["tips"][0].update(tip_id="answer"),
    "missing_required_nullable_quote": lambda x: x["documentation"][0].pop("quote"),
    "note_length": lambda x: x["safety"].update(note="x" * 361),
    "array_limit": lambda x: x.update(task_checks=x["task_checks"] * 9),
    "status_enum": lambda x: x["safety"].update(status="invented"),
    "decision_bound": lambda x: x["ratings"]["D1"].update(decision=2),
    "boolean_decision": lambda x: x["ratings"]["D1"].update(decision=True),
    "string_decision": lambda x: x["ratings"]["D1"].update(decision="0"),
    "extra_root": lambda x: x.update(extra="SYNTHETIC"),
    "extra_rating": lambda x: x["ratings"].update(D7=x["ratings"]["D1"]),
}


@pytest.mark.parametrize("name", FAULTS)
def test_schema_faults_are_rejected_by_logical_overlay_before_canonical_parsing(name):
    value = specimen()
    FAULTS[name](value)
    with pytest.raises(ValueError):
        conformance.validate_instance(supplied()["logical"], supplied()["logical"], value)
    with pytest.raises(ValueError):
        conformance.validate_raw(text(value), supplied(), CASE_ID, case(), pages())


@pytest.mark.parametrize(
    "operation",
    [
        lambda x: x["task_checks"][0].update(candidate_ids=["answer", "answer"]),
        lambda x: x["task_checks"][0].update(candidate_ids=[], status="supported"),
        lambda x: x["tips"].reverse(),
        lambda x: x["documentation"][0].update(passage_id=None, status="supported"),
    ],
)
def test_cross_field_faults_pass_overlay_and_remain_rejected_by_unchanged_grounding(operation):
    value = specimen()
    operation(value)
    logical = supplied()["logical"]
    conformance.validate_instance(logical, logical, value)
    GroundedJudgment.model_validate(value)
    with pytest.raises(ValueError):
        conformance.validate_raw(text(value), supplied(), CASE_ID, case(), pages())


def test_safety_restriction_does_not_narrow_other_evidence_fields():
    logical = supplied()["logical"]
    value = specimen()
    value["task_checks"][0]["candidate_ids"] = ["safety_info", "steps[1]", "tools_required[0]"]
    value["bindings"][0]["candidate_ids"] = ["equipment_problem"]
    conformance.validate_instance(logical, logical, value)
    definitions = logical["$defs"]
    assert definitions["SafetyFieldEvidence"]["properties"]["candidate_ids"]["items"]["enum"] == [
        "safety_info"
    ]
    catalog = definitions["TaskEvidence"]["properties"]["candidate_ids"]["items"]["enum"]
    assert len(catalog) == 9 and "safety_info" in catalog
    assert logical["properties"]["safety"] == {"$ref": "#/$defs/SafetyFieldEvidence"}


def test_null_passage_and_every_shown_passage_are_allowed_but_canonical_schema_is_unchanged():
    canonical = GroundedJudgment.model_json_schema()
    contract = supplied()
    assert GroundedJudgment.model_json_schema() == canonical
    for passage in ("P1.E1", "P2.E1", None):
        value = specimen()
        value["documentation"][0]["passage_id"] = passage
        conformance.validate_raw(text(value), contract, CASE_ID, case(), pages())
    value = specimen()
    value["documentation"] = []
    conformance.validate_raw(text(value), contract, CASE_ID, case(), pages())


def test_native_view_replaces_only_union_literal_nodes_and_expands_from_factored_form():
    contract = supplied()
    native = contract["native"]["$defs"]["DocumentationEvidence"]["properties"]
    assert native["quote"] == {"type": "null", "const": None, "title": "Quote"}
    assert native["passage_id"] == {"enum": ["P1.E1", "P2.E1", None], "title": "Passage Id"}
    assert "anyOf" not in json.dumps(contract["native"])
    assert json.dumps(expanded_schema(contract["factored"]), sort_keys=True) == json.dumps(
        expanded_schema(contract["native"]), sort_keys=True
    )
    for value in (specimen(), *[FAULTS[name](v) or v for name in FAULTS for v in [specimen()]]):
        outcomes = []
        for schema in (contract["logical"], contract["native"]):
            try:
                conformance.validate_instance(schema, schema, value)
                outcomes.append(True)
            except ValueError:
                outcomes.append(False)
        assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize(
    "change",
    [
        lambda n: n["$defs"]["DocumentationEvidence"]["properties"].update(
            quote={"anyOf": [{"type": "string"}, {"type": "null"}], "const": None, "title": "Quote"}
        ),
        lambda n: n["$defs"]["DocumentationEvidence"]["properties"]["passage_id"].update(
            anyOf=[{"type": "string"}, {"type": "null"}]
        ),
        lambda n: n["$defs"]["DocumentationEvidence"]["properties"]["passage_id"]["enum"].pop(0),
        lambda n: n["$defs"]["DocumentationEvidence"]["properties"]["quote"].pop("title"),
        lambda n: n["$defs"]["TaskEvidence"]["properties"]["note"].update(maxLength=500),
        lambda n: n["$defs"]["TipEvidence"].update(additionalProperties=True),
        lambda n: n["$defs"]["TaskEvidence"]["properties"]["note"].update(pattern="^S"),
        lambda n: n["properties"].update(safety={"$ref": "#/$defs/FieldEvidence", "title": "X"}),
    ],
)
def test_native_proof_rejects_unnormalized_or_otherwise_changed_views(change):
    contract = supplied()
    native = deepcopy(contract["native"])
    change(native)
    with pytest.raises(ValueError):
        conformance.prove_native(contract["logical"], native)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c, p: c["untrusted_reference_context"]["task"].update(brief="x" * 361),
        lambda c, p: c["untrusted_reference_context"]["task"].update(brief="  "),
        lambda c, p: c["untrusted_item"].update(tips=[]),
        lambda c, p: p[1].update(id="P1"),
        lambda c, p: c["untrusted_item"].update(extra="SYNTHETIC"),
    ],
)
def test_contract_rejects_inputs_it_cannot_represent_without_truncation(mutation):
    value, shown = case(), pages()
    mutation(value, shown)
    with pytest.raises(ValueError):
        conformance.contract(CASE_ID, value, shown)


def test_task_at_the_unchanged_limit_is_the_complete_constant():
    value = case()
    value["untrusted_reference_context"]["task"]["brief"] = "y" * 360
    logical = conformance.contract(CASE_ID, value, pages())["logical"]
    assert logical["$defs"]["TaskEvidence"]["properties"]["task_quote"]["const"] == "y" * 360


@pytest.mark.parametrize(
    "stale",
    [
        lambda s, c, p: ("SYNTHETIC-other", c, p, s),
        lambda s, c, p: (
            CASE_ID,
            c | {"untrusted_item": c["untrusted_item"] | {"answer": "Changed"}},
            p,
            s,
        ),
        lambda s, c, p: (
            CASE_ID,
            c,
            [p[0] | {"excerpts": [{"id": "E1", "text": "Changed"}]}, p[1]],
            s,
        ),
        lambda s, c, p: (
            CASE_ID,
            c,
            p,
            s
            | {
                "logical": s["logical"]
                | {"properties": s["logical"]["properties"] | {"extra": {"type": "string"}}}
            },
        ),
    ],
)
def test_stale_case_page_or_schema_bindings_are_rejected_before_validation(stale):
    case_id, value, shown, contract = stale(supplied(), case(), pages())
    with pytest.raises(ValueError, match="binding differs"):
        conformance.validate_raw(text(specimen()), contract, case_id, value, shown)


@pytest.mark.parametrize(
    "raw",
    [
        '{"task_checks": [], "task_checks": []}',
        text(specimen()).replace('"decision": 0', '"decision": NaN', 1),
        text(specimen()) + " trailing",
        "null",
    ],
)
def test_duplicate_keys_nonstandard_constants_and_non_objects_are_rejected(raw):
    with pytest.raises(ValueError):
        conformance.validate_raw(raw, supplied(), CASE_ID, case(), pages())


def test_validator_rejects_unknown_keywords_instead_of_ignoring_them():
    with pytest.raises(ValueError, match="unsupported schema keyword"):
        conformance.validate_instance({}, {"type": "string", "pattern": "^x$"}, "y")
    with pytest.raises(ValueError, match="unsupported schema keyword"):
        conformance.validate_instance({}, {"uniqueItems": True}, [1, 1])


def instructor_wire(messages):
    schema = json.dumps(GroundedJudgment.model_json_schema(), indent=2, ensure_ascii=False)
    first = messages[0] | {
        "content": messages[0]["content"] + INSTRUCTOR_PREFIX + schema + INSTRUCTOR_SUFFIX
    }
    return {
        "model": "synthetic",
        "messages": [first, *deepcopy(messages[1:])],
        "response_format": {"type": "json_object"},
        "max_tokens": 8192,
        "temperature": 0,
    }


def test_wire_sends_nested_native_schema_and_displays_only_the_factored_case_schema():
    messages = [
        {"role": "system", "content": "SYNTHETIC instructions"},
        {"role": "user", "content": "SYNTHETIC data"},
    ]
    original = instructor_wire(messages)
    contract = supplied()
    actual = conformance.conformance_wire(original, messages, contract)
    assert actual["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "GroundedJudgment", "schema": contract["factored"]},
    }
    shown = json.dumps(contract["factored"], ensure_ascii=False, separators=(",", ":"))
    assert actual["messages"][0]["content"] == (
        "SYNTHETIC instructions" + INSTRUCTOR_PREFIX + shown + INSTRUCTOR_SUFFIX
    )
    assert actual["messages"][1:] == original["messages"][1:]
    assert {k: v for k, v in actual.items() if k not in {"messages", "response_format"}} == {
        k: v for k, v in original.items() if k not in {"messages", "response_format"}
    }
    assert original["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize(
    "mutation",
    [
        lambda w: w.update(response_format={"type": "json_schema"}),
        lambda w: w["messages"][0].update(content=w["messages"][0]["content"] + " drift"),
        lambda w: w["messages"][1].update(content="changed"),
        lambda w: w["messages"].append({"role": "user", "content": "extra"}),
    ],
)
def test_wire_rejects_unexpected_instructor_shapes(mutation):
    messages = [
        {"role": "system", "content": "SYNTHETIC instructions"},
        {"role": "user", "content": "SYNTHETIC data"},
    ]
    original = instructor_wire(messages)
    mutation(original)
    with pytest.raises(ValueError):
        conformance.conformance_wire(original, messages, supplied())


def test_canonical_whitespace_normalization_is_not_an_extra_rejection_gate():
    value = specimen()
    value["ratings"]["D1"]["justification"] = "  SYNTHETIC with surrounding whitespace.\n"
    parsed, ratings = conformance.validate_raw(text(value), supplied(), CASE_ID, case(), pages())
    assert ratings.D1.justification == "SYNTHETIC with surrounding whitespace."


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c, p: c["untrusted_item"].update(tips=[f"SYNTHETIC tip {i}" for i in range(9)]),
        lambda c, p: p[0].update(excerpts=None),
        lambda c, p: p[0].pop("excerpts"),
    ],
)
def test_unsatisfiable_tip_counts_and_malformed_pages_raise_value_errors(mutation):
    value, shown = case(), pages()
    mutation(value, shown)
    with pytest.raises(ValueError):
        conformance.contract(CASE_ID, value, shown)


def native_accepts(root, node, value):
    """Mirror of the pinned build_node_impl precedence: $ref, anyOf/oneOf, const, enum, type."""
    same = conformance._same_json
    if "$ref" in node:
        return native_accepts(root, root["$defs"][node["$ref"].removeprefix("#/$defs/")], value)
    if "oneOf" in node or "anyOf" in node:
        return any(native_accepts(root, b, value) for b in node.get("oneOf", node.get("anyOf")))
    if "const" in node:
        return same(value, node["const"])
    if "enum" in node:
        return any(same(value, item) for item in node["enum"])
    kind = node.get("type")
    if kind == "object" or (kind is None and "properties" in node):
        properties = node.get("properties", {})
        return (
            isinstance(value, dict)
            and all(key in value for key in node.get("required", []))
            and (node.get("additionalProperties") is not False or set(value) <= set(properties))
            and all(
                native_accepts(root, properties[k], v) for k, v in value.items() if k in properties
            )
        )
    if kind == "array":
        return (
            isinstance(value, list)
            and node.get("minItems", 0) <= len(value) <= node.get("maxItems", len(value))
            and all(native_accepts(root, node["items"], item) for item in value)
        )
    if kind == "string":
        return isinstance(value, str) and node.get("minLength", 0) <= len(value) <= node.get(
            "maxLength", len(value)
        )
    if kind == "integer":
        return type(value) is int and node.get("minimum", value) <= value <= node.get(
            "maximum", value
        )
    if kind == "null":
        return value is None
    raise AssertionError(f"Unmodelled native node {node}")


def test_transmitted_schema_under_native_precedence_matches_logical_overlay():
    contract = supplied()
    corpus = [specimen()]
    for name in FAULTS:
        value = specimen()
        FAULTS[name](value)
        corpus.append(value)
    for value in corpus:
        try:
            conformance.validate_instance(contract["logical"], contract["logical"], value)
            expected = True
        except ValueError:
            expected = False
        factored = contract["factored"]
        assert native_accepts(factored, factored, value) is expected
    # The unnormalized overlay would let the native builder accept a copied quote.
    quoted = specimen()
    quoted["documentation"][0]["quote"] = "SYNTHETIC documentation passage."
    assert native_accepts(contract["logical"], contract["logical"], quoted) is True
    assert native_accepts(contract["factored"], contract["factored"], quoted) is False
