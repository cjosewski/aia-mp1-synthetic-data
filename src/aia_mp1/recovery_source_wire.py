"""Offline exact-wire serialization for source-ID recovery responses."""

import json
from copy import deepcopy

import httpx

from .model_client import InstructorClient
from .recovery_source_refs import SourceObservations
from .recovery_source_scoring import SourceScores
from .tracing import digest

SCHEMAS = {"facts": SourceObservations, "score": SourceScores}
FIELDS = {"model", "temperature", "max_tokens", "timeout_seconds", "messages"}


def prepare_source_wire(request: dict, stage: str) -> dict:
    """Capture Instructor serialization with exactly one intercepted local call."""
    if stage not in SCHEMAS or set(request) != FIELDS:
        raise ValueError("unexpected source-ID stage or request fields")
    messages = request["messages"]
    if (
        not isinstance(messages, list)
        or len(messages) != 2
        or [m.get("role") for m in messages if isinstance(m, dict)] != ["system", "user"]
        or any(set(m) != {"role", "content"} for m in messages)
        or any(not isinstance(m["content"], str) or not m["content"].strip() for m in messages)
    ):
        raise ValueError("source-ID requests require explicit system and user text")
    captured = []

    def capture(incoming):
        captured.append(json.loads(incoming.content))
        return httpx.Response(400, json={"error": {"message": "Offline source-ID inspection"}})

    original = deepcopy(request)
    with InstructorClient(
        base_url="http://127.0.0.1:1/v1",
        api_key="offline-placeholder",
        model=request["model"],
        mode="json",
        temperature=request["temperature"],
        max_tokens=request["max_tokens"],
        timeout_seconds=request["timeout_seconds"],
        response_model=SCHEMAS[stage],
        _transport=httpx.MockTransport(capture),
    ) as client:
        client.generate(deepcopy(messages))
    if len(captured) != 1 or request != original:
        raise ValueError("serialization must preserve input and intercept one request")
    wire = captured[0]
    return {
        "protocol": "recovery-source-wire-v1",
        "stage": stage,
        "request_sha256": digest(original),
        "schema_sha256": digest(SCHEMAS[stage].model_json_schema()),
        "wire": wire,
        "wire_sha256": digest(wire),
        "timeout_seconds": request["timeout_seconds"],
        "token_preflight": "not_measured",
        "execution_enabled": False,
        "calibration_eligible": False,
    }


def verify_source_wire(request: dict, stage: str, receipt: dict) -> dict:
    current = prepare_source_wire(request, stage)
    if current != receipt:
        raise ValueError("source-ID request or serialized wire changed")
    return deepcopy(current["wire"])
