"""Reversible page tables and exact one-shot JSON-schema whitespace compaction."""

import json
from collections import Counter
from copy import deepcopy

import httpx

LEGEND = (
    "online_documentation is reversible page tables: rows use columns; search_results "
    "and excerpts use search_columns and excerpt_columns. anchor_index resolves into "
    "that page's unchanged request.anchors. shared fields apply to every page. "
    "url_refs lists zero-based page rows whose omitted request.page is restored from url. "
    "missing lists [page,column]; search_missing/excerpt_missing list [page,row,column]; "
    "these cells are absent, not null. All other cells are literal."
)
SHARED_FIELDS = ("search_strategy", "edition", "http_status", "evidence_status")


def _same(left, right):
    return json.dumps(left, ensure_ascii=False) == json.dumps(right, ensure_ascii=False)


def _columns(rows):
    return list(dict.fromkeys(key for row in rows for key in row))


def _pack(rows, columns):
    missing = [
        [r, c] for r, row in enumerate(rows) for c, key in enumerate(columns) if key not in row
    ]
    return [[deepcopy(row.get(key)) for key in columns] for row in rows], missing


def _unpack(rows, columns, missing):
    if len(columns) != len(set(columns)) or any(not isinstance(key, str) for key in columns):
        raise ValueError("Table columns must be unique strings")
    absent = set()
    for pair in missing:
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or any(type(v) is not int for v in pair)
            or not 0 <= pair[0] < len(rows)
            or not 0 <= pair[1] < len(columns)
        ):
            raise ValueError("Invalid absent-cell coordinates")
        absent.add(tuple(pair))
    if len(absent) != len(missing):
        raise ValueError("Duplicate absent-cell coordinates")
    result = []
    for r, values in enumerate(rows):
        if len(values) != len(columns):
            raise ValueError("Table row width differs")
        if any(values[c] is not None for rr, c in absent if rr == r):
            raise ValueError("Absent table cell must use a null placeholder")
        result.append(
            {key: deepcopy(values[c]) for c, key in enumerate(columns) if (r, c) not in absent}
        )
    return result


def encode_pages(pages):
    """Encode compact project_pages output; values and ordered arrays are lossless."""
    working = deepcopy(pages)
    shared = {
        key: deepcopy(pages[0][key])
        for key in SHARED_FIELDS
        if pages
        and key in pages[0]
        and all(key in page and _same(page[key], pages[0][key]) for page in pages)
    }
    url_refs = []
    for index, page in enumerate(working):
        for key in shared:
            del page[key]
        request = page.get("request")
        if isinstance(request, dict):
            value = request.get("page")
            if isinstance(value, str) and value == page.get("url"):
                url_refs.append(index)
                del request["page"]
        for row in page.get("search_results", []) or []:
            if "anchor_index" in row:
                raise ValueError("Reserved anchor_index key in source search row")
            if "anchor" in row:
                anchor = row.pop("anchor")
                anchors = page["request"]["anchors"]
                if anchor is not None and (not isinstance(anchor, str) or anchor not in anchors):
                    raise ValueError("Search anchor does not resolve to original request")
                row["anchor_index"] = anchors.index(anchor) if anchor is not None else None
    searches = [row for page in working for row in (page.get("search_results", []) or [])]
    excerpts = [row for page in working for row in (page.get("excerpts", []) or [])]
    search_columns, excerpt_columns = _columns(searches), _columns(excerpts)
    search_missing, excerpt_missing = [], []
    for index, page in enumerate(working):
        for field, columns, missing in (
            ("search_results", search_columns, search_missing),
            ("excerpts", excerpt_columns, excerpt_missing),
        ):
            if field in page:
                if page[field] is None:
                    continue
                page[field], absent = _pack(page[field], columns)
                missing.extend([[index, *pair] for pair in absent])
    columns = _columns(working)
    rows, missing = _pack(working, columns)
    encoded = {
        "columns": columns,
        "search_columns": search_columns,
        "excerpt_columns": excerpt_columns,
        "shared": shared,
        "url_refs": url_refs,
        "rows": rows,
    }
    for key, value in (
        ("missing", missing),
        ("search_missing", search_missing),
        ("excerpt_missing", excerpt_missing),
    ):
        if value:
            encoded[key] = value
    if json.dumps(decode_pages(encoded), sort_keys=True) != json.dumps(pages, sort_keys=True):
        raise ValueError("Page encoding is not reversible")
    return encoded


def decode_pages(encoded):
    pages = _unpack(encoded["rows"], encoded["columns"], encoded.get("missing", []))
    url_refs = encoded["url_refs"]
    if any(type(v) is not int or not 0 <= v < len(pages) for v in url_refs) or len(url_refs) != len(
        set(url_refs)
    ):
        raise ValueError("Invalid URL reference indices")
    for index, page in enumerate(pages):
        for key, value in encoded["shared"].items():
            if key in page:
                raise ValueError("Shared page field collides with literal field")
            page[key] = deepcopy(value)
        if index in url_refs:
            if "page" in page["request"]:
                raise ValueError("URL reference collides with request.page")
            page["request"]["page"] = page["url"]
        for field, columns_key, missing_key in (
            ("search_results", "search_columns", "search_missing"),
            ("excerpts", "excerpt_columns", "excerpt_missing"),
        ):
            missing = encoded.get(missing_key, [])
            if any(
                not isinstance(row, list)
                or len(row) != 3
                or type(row[0]) is not int
                or not 0 <= row[0] < len(pages)
                for row in missing
            ):
                raise ValueError("Invalid nested absent-cell coordinates")
            absent = [row[1:] for row in missing if row[0] == index]
            if field in page and page[field] is not None:
                page[field] = _unpack(page[field], encoded[columns_key], absent)
            elif absent:
                raise ValueError("Absent-cell coordinates reference a missing table")
        for row in page.get("search_results", []) or []:
            if "anchor_index" in row:
                value = row.pop("anchor_index")
                anchors = page["request"]["anchors"]
                if value is not None and (type(value) is not int or not 0 <= value < len(anchors)):
                    raise ValueError("Invalid anchor index")
                row["anchor"] = anchors[value] if value is not None else None
    return pages


SCHEMA_MAPS = {"properties", "patternProperties", "dependentSchemas"}
SCHEMA_SINGLE = {
    "items",
    "additionalProperties",
    "unevaluatedProperties",
    "unevaluatedItems",
    "contains",
    "propertyNames",
    "not",
    "if",
    "then",
    "else",
}
SCHEMA_LISTS = {"anyOf", "allOf", "oneOf", "prefixItems"}
UNSUPPORTED_SCHEMA = {
    "$id",
    "$anchor",
    "$dynamicAnchor",
    "$dynamicRef",
    "$recursiveRef",
    "$recursiveAnchor",
}


def _schema_children(value, visit, *, root=False):
    if not isinstance(value, (dict, bool)):
        raise ValueError("Expected a schema object or boolean")
    if isinstance(value, bool):
        return value
    if UNSUPPORTED_SCHEMA & value.keys() or ("$defs" in value and not root):
        raise ValueError("Unsupported schema identity or nested definition semantics")
    result = {}
    for key, item in value.items():
        if key == "$defs":
            continue
        if key in SCHEMA_MAPS:
            result[key] = {name: visit(child) for name, child in item.items()}
        elif key in SCHEMA_SINGLE:
            result[key] = visit(item)
        elif key in SCHEMA_LISTS:
            result[key] = [visit(child) for child in item]
        else:
            # Annotation/default/enum/const/example values are data, not schemas.
            result[key] = deepcopy(item)
    return result


def expanded_schema(schema):
    """Expand local references without treating literal annotation values as schemas."""
    definitions = schema.get("$defs", {})

    def expand(value, visited=(), root=False):
        if isinstance(value, dict) and "$ref" in value:
            ref = value["$ref"]
            if set(value) != {"$ref"} or not isinstance(ref, str) or not ref.startswith("#/$defs/"):
                raise ValueError("Unsupported schema reference structure")
            name = ref.removeprefix("#/$defs/")
            if name not in definitions or name in visited:
                raise ValueError("Unresolved or cyclic schema reference")
            return expand(definitions[name], (*visited, name))
        return _schema_children(value, lambda child: expand(child, visited), root=root)

    # Check unused definitions too; changing their interpretation is not permitted.
    for name, definition in definitions.items():
        expand(definition, (name,))
    return expand(schema, root=True)


def factor_schema(schema):
    """Share identical property schemas and shorten local definition names, retaining titles."""
    result = deepcopy(schema)
    definitions = result.get("$defs", {})
    properties = [
        (obj, key, value)
        for definition in definitions.values()
        if isinstance(definition, dict)
        for obj in [definition.get("properties", {})]
        for key, value in obj.items()
    ]

    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    counts = Counter(canonical(value) for _, _, value in properties)
    shared = {}
    for obj, key, value in properties:
        identity = canonical(value)
        if (
            isinstance(value, dict)
            and counts[identity] > 1
            and len(identity) > 40
            and "$ref" not in value
        ):
            if identity not in shared:
                name = "_shared" + str(len(shared))
                while name in definitions:
                    name += "_"
                shared[identity] = name
                definitions[name] = deepcopy(value)
            obj[key] = {"$ref": "#/$defs/" + shared[identity]}
    names = {name: f"S{index}" for index, name in enumerate(definitions)}

    def rename(value):
        if isinstance(value, dict) and "$ref" in value:
            ref = value["$ref"]
            name = ref.removeprefix("#/$defs/")
            if not ref.startswith("#/$defs/") or name not in names:
                raise ValueError("Only resolved local schema references can be renamed")
            return {"$ref": "#/$defs/" + names[name]}
        return _schema_children(value, rename)

    # Validate before rewriting so a reference with siblings cannot lose assertions.
    original_expanded = expanded_schema(schema)
    result = _schema_children(result, rename, root=True) | {
        "$defs": {names[name]: rename(value) for name, value in definitions.items()}
    }
    if json.dumps(expanded_schema(result), sort_keys=True) != json.dumps(
        original_expanded, sort_keys=True
    ):
        raise ValueError("Factored schema changes expanded constraints or annotations")
    return result


def compact_rubric_messages(messages, expected_rubric):
    """Minify only the original rubric JSON, preserving surrounding instructions and data."""
    result = deepcopy(messages)
    first = result[0]
    marker = "\n\nRubric:\n"
    if first.get("role") != "system" or first["content"].count(marker) != 1:
        raise ValueError("Expected one original rubric boundary")
    before, tail = first["content"].split(marker, 1)
    rubric, end = json.JSONDecoder().raw_decode(tail)
    if not isinstance(rubric, dict) or json.dumps(
        rubric, sort_keys=True, allow_nan=False
    ) != json.dumps(expected_rubric, sort_keys=True, allow_nan=False):
        raise ValueError("Original rubric differs from frozen expectation")
    compact = json.dumps(rubric, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    first["content"] = before + marker + compact + tail[end:]
    return result


INSTRUCTOR_PREFIX = (
    "\n\n\n            As a genius expert, your task is to understand the content and provide\n"
    "            the parsed objects in json that match the following json_schema:\n\n\n            "
)
INSTRUCTOR_SUFFIX = (
    "\n\n            Make sure to return an instance of the JSON, not the schema itself\n"
)


def compact_schema_wire(wire, original_messages, schema, *, factor=False):
    """Minify exactly the schema appended by the pinned Instructor JSON handler."""
    if wire.get("response_format") != {"type": "json_object"}:
        raise ValueError("Expected Instructor JSON-object mode")
    if not wire.get("messages") or len(wire["messages"]) != len(original_messages):
        raise ValueError("Instructor message count differs")
    result = deepcopy(wire)
    first = wire["messages"][0]
    original = original_messages[0]
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
    pretty = json.dumps(schema, indent=2, ensure_ascii=False)
    if suffix != INSTRUCTOR_PREFIX + pretty + INSTRUCTOR_SUFFIX:
        raise ValueError("Expected exact pinned Instructor schema wrapper")
    displayed = factor_schema(schema) if factor else schema
    compact = json.dumps(displayed, ensure_ascii=False, separators=(",", ":"))
    if json.loads(compact) != displayed:
        raise ValueError("Schema serialization differs")
    result["messages"][0]["content"] = original["content"] + suffix.replace(pretty, compact, 1)
    return result


class OneShotWireTransport(httpx.BaseTransport):
    """Forward only the measured transformed body, with no retries or global hooks."""

    def __init__(self, expected, transformed, *, inner=None):
        self.expected = deepcopy(expected)
        self.transformed = deepcopy(transformed)
        self.inner = inner if inner is not None else httpx.HTTPTransport(retries=0)
        self.calls = 0

    def handle_request(self, request):
        if self.calls:
            raise ValueError("Model attempt cannot dispatch twice")
        self.calls += 1
        if json.dumps(json.loads(request.content), sort_keys=True, allow_nan=False) != json.dumps(
            self.expected, sort_keys=True, allow_nan=False
        ):
            raise ValueError("Instructor wire differs from measured pre-transformation body")
        content = json.dumps(self.transformed, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        headers = [
            (key, value) for key, value in request.headers.raw if key.lower() != b"content-length"
        ]
        forwarded = httpx.Request(
            request.method,
            request.url,
            headers=headers,
            content=content,
            extensions=dict(request.extensions),
        )
        return self.inner.handle_request(forwarded)

    def close(self):
        self.inner.close()
