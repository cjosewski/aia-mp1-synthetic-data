"""Case-specific constrained response contract for native schema decoding.

The canonical ``GroundedJudgment`` model and ``validate_grounding`` remain unchanged and
authoritative. This module narrows only the allowed response values for one case and
its shown passages, derives a native-normalized view for the pinned llama.cpp schema
builder, proves the two accept the same values, and validates untouched raw text
against the logical overlay before canonical parsing. It never repairs a response,
selects a span or derives a rating.
"""

import json
from copy import deepcopy

from aec_wire_docs import INSTRUCTOR_PREFIX, INSTRUCTOR_SUFFIX, expanded_schema, factor_schema

from aia_mp1.grounded_documentation import GroundedJudgment, candidate_catalog, validate_grounding
from aia_mp1.tracing import digest

CONTRACT_VERSION = "aec-conformance-contract-v1"
SCHEMA_NAME = "GroundedJudgment"
TASK_LIMIT = 360
ANNOTATIONS = {"title", "description"}
# Every keyword the overlay may contain. Anything else stops validation instead of
# being silently ignored by either the Python check or the native converter.
ASSERTIONS = {
    "type",
    "const",
    "enum",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "anyOf",
    "$ref",
}
NATIVE_PATHS = {
    ("$defs", "DocumentationEvidence", "properties", "quote"),
    ("$defs", "DocumentationEvidence", "properties", "passage_id"),
}


def canonical_schema():
    return GroundedJudgment.model_json_schema()


def passage_ids(pages):
    if not isinstance(pages, list) or any(
        not isinstance(page, dict) or not isinstance(page.get("excerpts"), list) for page in pages
    ):
        raise ValueError("Shown pages must each carry an excerpt list")
    ids = [f"{page['id']}.{excerpt['id']}" for page in pages for excerpt in page["excerpts"]]
    if len(ids) != len(set(ids)) or any(not isinstance(value, str) for value in ids):
        raise ValueError("Shown passage identities must be unique strings")
    return ids


def logical_schema(case, pages):
    """Restrict the canonical schema to this case's original IDs and full task text."""
    schema = canonical_schema()
    catalog = list(candidate_catalog(case))
    tips = [key for key in catalog if key.startswith("tips[")]
    task = case["untrusted_reference_context"]["task"]["brief"]
    if not isinstance(task, str) or not task.strip():
        raise ValueError("Task brief must be nonempty original text")
    if len(task) > TASK_LIMIT:
        raise ValueError("Task brief exceeds the unchanged 360-character field limit")
    if not 1 <= len(tips) <= 8:
        raise ValueError("Constrained tip IDs need one to eight original tips")
    definitions = schema["$defs"]
    for name in ("FieldEvidence", "TaskEvidence", "TipEvidence"):
        definitions[name]["properties"]["candidate_ids"]["items"]["enum"] = catalog[:]
    definitions["TaskEvidence"]["properties"]["task_quote"]["const"] = task
    definitions["TipEvidence"]["properties"]["tip_id"]["enum"] = tips
    documentation = definitions["DocumentationEvidence"]["properties"]
    documentation["candidate_id"]["enum"] = catalog[:]
    documentation["passage_id"]["enum"] = [*passage_ids(pages), None]
    documentation["quote"]["const"] = None
    # A separate definition keeps the D2 restriction from narrowing other fields.
    safety = deepcopy(definitions["FieldEvidence"])
    safety["properties"]["candidate_ids"]["items"]["enum"] = ["safety_info"]
    safety["title"] = "SafetyFieldEvidence"
    definitions["SafetyFieldEvidence"] = safety
    schema["properties"]["safety"] = {"$ref": "#/$defs/SafetyFieldEvidence"}
    prove_logical(schema)
    return schema


def prove_logical(schema):
    """Removing exactly the enumerated restrictions must recover the canonical schema."""
    recovered = deepcopy(schema)
    definitions = recovered["$defs"]
    safety = definitions.pop("SafetyFieldEvidence")
    if safety["properties"]["candidate_ids"]["items"].pop("enum") != ["safety_info"]:
        raise ValueError("Safety overlay differs from the D2 field restriction")
    safety["title"] = "FieldEvidence"
    canonical = canonical_schema()
    if safety != canonical["$defs"]["FieldEvidence"]:
        raise ValueError("Safety overlay changes canonical field evidence")
    recovered["properties"]["safety"] = deepcopy(canonical["properties"]["safety"])
    for name in ("FieldEvidence", "TaskEvidence", "TipEvidence"):
        definitions[name]["properties"]["candidate_ids"]["items"].pop("enum")
    definitions["TaskEvidence"]["properties"]["task_quote"].pop("const")
    definitions["TipEvidence"]["properties"]["tip_id"].pop("enum")
    documentation = definitions["DocumentationEvidence"]["properties"]
    documentation["candidate_id"].pop("enum")
    documentation["passage_id"].pop("enum")
    if documentation["quote"].pop("const", "absent") is not None:
        raise ValueError("Documentation quote overlay must be null")
    if recovered != canonical:
        raise ValueError("Logical overlay changes canonical schema beyond its restrictions")


def native_schema(logical):
    """Replace union-plus-literal nodes the pinned builder would read as bare unions."""
    result = deepcopy(logical)
    documentation = result["$defs"]["DocumentationEvidence"]["properties"]
    documentation["quote"] = {"type": "null", "const": None, "title": "Quote"}
    documentation["passage_id"] = {
        "enum": deepcopy(documentation["passage_id"]["enum"]),
        "title": "Passage Id",
    }
    prove_native(logical, result)
    return result


def _walk(value, path=()):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, (*path, index))


def _at(value, path):
    for key in path:
        value = value[key]
    return value


def literal_domain(schema, node):
    """Finite accepted values of a const/enum node under standard semantics."""
    if "const" in node:
        values = [node["const"]]
    elif "enum" in node:
        values = node["enum"]
    else:
        raise ValueError("Expected a literal schema node")
    result = []
    for value in values:
        try:
            validate_instance(schema, node, value)
        except ValueError:
            continue
        result.append(value)
    return result


def prove_native(logical, native):
    """Prove the native view accepts exactly the logical overlay's values."""
    _lint_native(native)
    replaced = deepcopy(native)
    for path in NATIVE_PATHS:
        target = _at(replaced, path[:-1])
        target[path[-1]] = deepcopy(_at(logical, path))
    if replaced != logical:
        raise ValueError("Native view changes nodes outside the documented normalizations")
    for path in NATIVE_PATHS:
        old, new = (
            literal_domain(logical, _at(logical, path)),
            literal_domain(native, _at(native, path)),
        )
        if _canonical(old) != _canonical(new) or _canonical(new) != _canonical(
            _at(native, path).get("enum", [_at(native, path).get("const")])
        ):
            raise ValueError("Native normalization changes accepted values")
        if _at(native, path).get("title") != _at(logical, path).get("title"):
            raise ValueError("Native normalization drops annotations")
    for owner in ("DocumentationEvidence",):
        if native["$defs"][owner]["required"] != logical["$defs"][owner]["required"] or list(
            native["$defs"][owner]["properties"]
        ) != list(logical["$defs"][owner]["properties"]):
            raise ValueError("Native normalization changes requiredness or property order")


def _lint_native(schema):
    """Reject shapes where pinned native precedence differs from standard semantics."""
    for path, node in _walk(schema):
        if not isinstance(node, dict) or not _is_schema_path(path):
            continue
        unknown = set(node) - ASSERTIONS - ANNOTATIONS - ({"$defs"} if path == () else set())
        if unknown:
            raise ValueError(f"Unsupported schema keyword at {path}: {sorted(unknown)}")
        assertions = set(node) & ASSERTIONS
        if "$ref" in node and assertions != {"$ref"}:
            raise ValueError("Native builder ignores assertions beside $ref")
        if "anyOf" in node and assertions != {"anyOf"}:
            raise ValueError("Native builder ignores assertions beside anyOf")
        if "const" in node and "enum" in node:
            raise ValueError("Native builder ignores enum beside const")
        if {"const", "enum"} & assertions:
            literal = [node["const"]] if "const" in node else node["enum"]
            if not literal or _canonical(literal_domain(schema, node)) != _canonical(literal):
                raise ValueError("Native literal node has values its siblings reject")
        if node.get("type") == "object" and node.get("additionalProperties") is not False:
            raise ValueError("Every object must be explicitly closed")


def _is_schema_path(path):
    """True for paths naming a schema, not literal const/enum/required data."""
    index = 0
    while index < len(path):
        key = path[index]
        if key == "$defs" and index == 0:
            index += 2
        elif key == "properties":
            index += 2
        elif key in {"items", "additionalProperties"}:
            index += 1
        elif key == "anyOf":
            index += 2
        else:
            return False
    return index == len(path)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _json_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise ValueError("Value is not JSON data")


def _same_json(left, right):
    return _json_type(left) == _json_type(right) and _canonical(left) == _canonical(right)


def validate_instance(root, node, value, path="$"):
    """Strict validator for the overlay subset; unknown keywords are errors."""
    if not isinstance(node, dict):
        raise ValueError(f"{path}: schema must be an object")
    unknown = set(node) - ASSERTIONS - ANNOTATIONS - {"$defs"}
    if unknown:
        raise ValueError(f"{path}: unsupported schema keyword {sorted(unknown)}")
    if "$ref" in node:
        ref = node["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
            raise ValueError(f"{path}: unsupported reference")
        target = root.get("$defs", {}).get(ref.removeprefix("#/$defs/"))
        if target is None:
            raise ValueError(f"{path}: unresolved reference")
        validate_instance(root, target, value, path)
    if "anyOf" in node:
        errors = []
        for branch in node["anyOf"]:
            try:
                validate_instance(root, branch, value, path)
            except ValueError as error:
                errors.append(str(error))
            else:
                break
        else:
            raise ValueError(f"{path}: no alternative matched ({'; '.join(errors)})")
    kind = _json_type(value)
    if "type" in node:
        expected = node["type"]
        if not isinstance(expected, str) or kind != expected:
            raise ValueError(f"{path}: expected {expected}, found {kind}")
    if "const" in node and not _same_json(value, node["const"]):
        raise ValueError(f"{path}: value differs from the required constant")
    if "enum" in node and not any(_same_json(value, item) for item in node["enum"]):
        raise ValueError(f"{path}: value is not an allowed identifier")
    if kind == "string":
        if len(value) < node.get("minLength", 0):
            raise ValueError(f"{path}: string is too short")
        if "maxLength" in node and len(value) > node["maxLength"]:
            raise ValueError(f"{path}: string is too long")
    if kind == "integer":
        if "minimum" in node and value < node["minimum"]:
            raise ValueError(f"{path}: integer is below minimum")
        if "maximum" in node and value > node["maximum"]:
            raise ValueError(f"{path}: integer is above maximum")
    if kind == "array":
        if len(value) < node.get("minItems", 0):
            raise ValueError(f"{path}: too few items")
        if "maxItems" in node and len(value) > node["maxItems"]:
            raise ValueError(f"{path}: too many items")
        if "items" in node:
            for index, item in enumerate(value):
                validate_instance(root, node["items"], item, f"{path}[{index}]")
    if kind == "object":
        properties = node.get("properties", {})
        missing = [key for key in node.get("required", []) if key not in value]
        if missing:
            raise ValueError(f"{path}: missing required {missing}")
        extra = [key for key in value if key not in properties]
        if extra and node.get("additionalProperties", True) is False:
            raise ValueError(f"{path}: unexpected keys {extra}")
        if extra and isinstance(node.get("additionalProperties"), dict):
            raise ValueError(f"{path}: schema-valued additionalProperties is unsupported")
        for key, item in value.items():
            if key in properties:
                validate_instance(root, properties[key], item, f"{path}.{key}")


def _unique_object(pairs):
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("Raw JSON contains duplicate keys")
    return dict(pairs)


def _reject_constant(name):
    raise ValueError(f"Raw JSON contains non-standard constant {name}")


def contract(case_id, case, pages):
    """Bound logical/native/factored identities for one case and its shown passages."""
    logical = logical_schema(case, pages)
    native = native_schema(logical)
    factored = factor_schema(native)
    _lint_native(factored)
    if _canonical(expanded_schema(factored)) != _canonical(expanded_schema(native)):
        raise ValueError("Factored native schema does not expand to the normalized schema")
    binding = {
        "contract_version": CONTRACT_VERSION,
        "case_id": case_id,
        "case_sha256": digest(case),
        "shown_pages_sha256": digest(pages),
        "canonical_schema_sha256": digest(canonical_schema()),
        "logical_schema_sha256": digest(logical),
        "native_schema_sha256": digest(native),
        "factored_native_schema_sha256": digest(factored),
    }
    return {"binding": binding, "logical": logical, "native": native, "factored": factored}


def check_contract(supplied, case_id, case, pages):
    if supplied != contract(case_id, case, pages):
        raise ValueError("Case, shown pages or schema binding differs")


def validate_raw(text, supplied, case_id, case, pages):
    """Logical overlay, then canonical Pydantic, then unchanged grounding; no repair."""
    check_contract(supplied, case_id, case, pages)
    if not isinstance(text, str):
        raise ValueError("Raw response content must be text")
    value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    validate_instance(supplied["logical"], supplied["logical"], value)
    # Canonical normalization (e.g. stripped justifications) is the unchanged model's
    # own behavior, not an additional gate.
    parsed = GroundedJudgment.model_validate_json(text)
    ratings = validate_grounding(parsed, case, pages)
    return parsed, ratings


def conformance_wire(wire, original_messages, supplied):
    """Display and natively require the factored case schema in place of the canonical one."""
    if wire.get("response_format") != {"type": "json_object"}:
        raise ValueError("Expected Instructor JSON-object mode")
    if not wire.get("messages") or len(wire["messages"]) != len(original_messages):
        raise ValueError("Instructor message count differs")
    first, original = wire["messages"][0], original_messages[0]
    if first.get("role") != "system" or original.get("role") != "system":
        raise ValueError("Expected original system message")
    if not first["content"].startswith(original["content"]):
        raise ValueError("Original system instructions differ")
    if any(
        left != right
        for left, right in zip(wire["messages"][1:], original_messages[1:], strict=True)
    ):
        raise ValueError("Original non-system messages differ")
    suffix = first["content"][len(original["content"]) :]
    pretty = json.dumps(canonical_schema(), indent=2, ensure_ascii=False)
    if suffix != INSTRUCTOR_PREFIX + pretty + INSTRUCTOR_SUFFIX:
        raise ValueError("Expected exact pinned Instructor schema wrapper")
    factored = supplied["factored"]
    shown = json.dumps(factored, ensure_ascii=False, separators=(",", ":"))
    if json.loads(shown) != factored:
        raise ValueError("Schema serialization differs")
    result = deepcopy(wire)
    result["messages"][0]["content"] = original["content"] + suffix.replace(pretty, shown, 1)
    result["response_format"] = {
        "type": "json_schema",
        "json_schema": {"name": SCHEMA_NAME, "schema": deepcopy(factored)},
    }
    return result
