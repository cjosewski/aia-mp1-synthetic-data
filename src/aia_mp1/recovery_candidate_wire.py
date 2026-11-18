"""Capture the exact local Instructor wire for a candidate challenge."""

import json
from copy import deepcopy

import httpx

from .model_client import InstructorClient
from .recovery_candidate_challenge import CandidateApplicabilityChallenge
from .tracing import digest


def prepare_challenge_wire(request: dict) -> dict:
    if set(request) != {"model", "temperature", "max_tokens", "timeout_seconds", "messages"}:
        raise ValueError("unexpected challenge request fields")
    messages = request["messages"]
    if (
        not isinstance(messages, list)
        or len(messages) != 2
        or [row.get("role") for row in messages if isinstance(row, dict)] != ["system", "user"]
        or any(
            not isinstance(row.get("content"), str) or not row["content"].strip()
            for row in messages
        )
    ):
        raise ValueError("challenge needs a system and user message")
    captured = []

    def intercept(incoming):
        captured.append(json.loads(incoming.content))
        return httpx.Response(400, json={"error": {"message": "Offline challenge wire"}})

    original = deepcopy(request)
    with InstructorClient(
        base_url="http://127.0.0.1:1/v1",
        api_key="offline-placeholder",
        model=request["model"],
        mode="json",
        temperature=request["temperature"],
        max_tokens=request["max_tokens"],
        timeout_seconds=request["timeout_seconds"],
        response_model=CandidateApplicabilityChallenge,
        _transport=httpx.MockTransport(intercept),
    ) as client:
        client.generate(deepcopy(messages))
    if len(captured) != 1 or request != original:
        raise ValueError("challenge wire capture changed request or made multiple calls")
    wire = captured[0]
    return {
        "protocol": "candidate-challenge-wire-v1",
        "request_sha256": digest(request),
        "schema_sha256": digest(CandidateApplicabilityChallenge.model_json_schema()),
        "wire": wire,
        "wire_sha256": digest(wire),
        "timeout_seconds": request["timeout_seconds"],
        "model_starts": 0,
        "calibration_eligible": False,
    }
