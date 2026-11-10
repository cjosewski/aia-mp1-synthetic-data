"""Exercise the real SDK/Instructor boundary with synthetic HTTP responses."""

import json
import logging
from copy import deepcopy

import httpx
import pytest

from aia_mp1.model_client import InstructorClient

KEY = "synthetic-test-credential-do-not-log"
MESSAGES = [{"role": "user", "content": "Generate a synthetic test Q&A item."}]


def qa_payload():
    return {
        "question": "How do I validate the units in a standalone test grid?",
        "answer": "Inspect the units, validate a test distance, then save a new copy.",
        "equipment_problem": "A synthetic grid has an unknown distance unit.",
        "tools_required": ["Python standard library"],
        "steps": ["Read the unit metadata.", "Check a known test distance.", "Save a new copy."],
        "safety_info": "Mixed units corrupt distances; compare a known distance before saving.",
        "tips": ["Record the original metadata separately to make a conversion reversible."],
    }


def completion(content, *, tools=False):
    message = {"role": "assistant", "content": content}
    if tools:
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "test-call-1",
                    "type": "function",
                    "function": {"name": "QAItem", "arguments": content},
                }
            ],
        }
    return {
        "id": "test-completion-1",
        "object": "chat.completion",
        "created": 1,
        "model": "synthetic-model-revision",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


def make_client(handler, **kwargs):
    return InstructorClient(
        base_url="http://127.0.0.1:8080/v1",
        model="explicit-test-model",
        api_key=KEY,
        _transport=httpx.MockTransport(handler),
        **kwargs,
    )


@pytest.mark.parametrize("mode", ["json", "tools"])
def test_valid_response_uses_one_request_and_retains_completion(mode):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=completion(json.dumps(qa_payload()), tools=mode == "tools"))

    messages = deepcopy(MESSAGES)
    with make_client(handler, mode=mode, timeout_seconds=2.5) as client:
        result = client.generate(messages)

    assert len(calls) == 1
    assert str(calls[0].url) == "http://127.0.0.1:8080/v1/chat/completions"
    body = json.loads(calls[0].content)
    assert body["model"] == "explicit-test-model"
    assert body["temperature"] == 0.6
    assert body["max_tokens"] == 1200
    assert calls[0].extensions["timeout"]["read"] == 2.5
    assert result.item.model_dump() == qa_payload()
    assert result.raw_response["id"] == "test-completion-1"
    assert result.raw_response["usage"]["total_tokens"] == 30
    assert result.response_model == "synthetic-model-revision"
    assert result.error is None
    assert messages == MESSAGES  # Instructor's schema instructions do not mutate callers.


@pytest.mark.parametrize("content", ["not valid JSON", json.dumps({"question": "Missing fields"})])
def test_malformed_or_invalid_output_is_returned_without_hidden_retry(content):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=completion(content))

    with make_client(handler) as client:
        result = client.generate(MESSAGES)

    assert len(calls) == 1
    assert result.item is None
    assert result.error
    assert result.error_type
    assert result.raw_response["choices"][0]["message"]["content"] == content


@pytest.mark.parametrize("status", [401, 429, 500])
def test_http_failures_are_one_attempt_and_preserve_error_body(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "synthetic server error"}})

    with make_client(handler) as client:
        result = client.generate(MESSAGES)

    assert len(calls) == 1
    assert result.item is None
    assert result.error
    assert "synthetic server error" in json.dumps(result.raw_response)


def test_timeout_returns_failure_without_transport_retry():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("synthetic timeout", request=request)

    with make_client(handler) as client:
        result = client.generate(MESSAGES)

    assert len(calls) == 1
    assert result.item is None
    assert result.raw_response is None
    assert result.error_type == "APITimeoutError"


@pytest.mark.parametrize("kind", ["truncated", "broken_envelope", "not_json"])
def test_unparseable_or_truncated_completion_still_retains_response_body(kind):
    calls = []
    raw = completion('{"question":"truncated')
    raw["choices"][0]["finish_reason"] = "length"
    if kind == "broken_envelope":
        raw = {"unexpected": "not a chat completion"}

    def handler(request):
        calls.append(request)
        if kind == "not_json":
            return httpx.Response(200, text="synthetic invalid HTTP response")
        return httpx.Response(200, json=raw)

    with make_client(handler) as client:
        result = client.generate(MESSAGES)

    assert len(calls) == 1
    assert result.item is None
    assert result.error
    assert result.raw_response == ("synthetic invalid HTTP response" if kind == "not_json" else raw)


def test_successful_payload_and_raw_response_redact_echoed_credentials():
    payload = qa_payload()
    payload["answer"] += f" Echoed credential: {KEY}"
    raw = completion(json.dumps(payload))
    raw["extra_metadata"] = {"authorization": "Bearer unrelated-secret", "nested": [KEY]}
    with make_client(lambda request: httpx.Response(200, json=raw)) as client:
        result = client.generate(MESSAGES)

    assert result.item is not None
    serialized = json.dumps(result.raw_response) + result.item.model_dump_json()
    assert KEY not in serialized
    assert "unrelated-secret" not in serialized
    assert "[REDACTED]" in serialized


@pytest.mark.parametrize("prefix", ["", "malformed response containing "])
def test_failed_response_and_error_redact_echoed_credential(caplog, prefix):
    # The longer case makes Pydantic abbreviate the credential-containing input;
    # exact full-key replacement alone would leave a visible credential suffix.
    raw = completion(prefix + KEY)
    caplog.set_level(logging.ERROR, logger="instructor.v2.retry")
    with make_client(lambda request: httpx.Response(200, json=raw)) as client:
        result = client.generate(MESSAGES)

    assert result.item is None
    for fragment in (KEY, KEY[-16:]):
        assert fragment not in json.dumps(result.raw_response)
        assert fragment not in result.error
        assert fragment not in caplog.text
    assert "[REDACTED]" in json.dumps(result.raw_response)
    assert any(record.levelno == logging.ERROR for record in caplog.records)
    assert "[REDACTED]" in caplog.text
    assert "json_invalid" in caplog.text
    assert "json_invalid" in result.error


def test_schema_diagnostics_retain_field_details_without_echoed_input(caplog):
    payload = qa_payload()
    payload["steps"] = "long invalid list value containing " + KEY
    raw = completion(json.dumps(payload))
    with make_client(lambda request: httpx.Response(200, json=raw)) as client:
        result = client.generate(MESSAGES)

    assert result.item is None
    for fragment in (KEY, KEY[-16:]):
        assert fragment not in result.error
        assert fragment not in caplog.text
    assert "steps" in result.error
    assert "list_type" in result.error
    assert "list_type" in caplog.text
    assert "input_value=[REDACTED]" in result.error


def test_http_error_redacts_credential_from_body_and_message(caplog):
    def handler(request):
        return httpx.Response(401, json={"error": {"message": f"Invalid credential {KEY}"}})

    with make_client(handler) as client:
        result = client.generate(MESSAGES)

    assert KEY not in json.dumps(result.raw_response) + result.error
    assert "[REDACTED]" in result.error
    assert KEY not in caplog.text


def test_production_transport_ignores_environment_proxies(monkeypatch):
    # No injected transport: MockTransport would disable HTTPX proxy discovery
    # itself and conceal this regression. Inspect actual routing without I/O.
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(name, "http://127.0.0.1:9")
        monkeypatch.delenv(name.lower(), raising=False)
    for name in ("NO_PROXY", "no_proxy", "REQUEST_METHOD"):
        monkeypatch.delenv(name, raising=False)
    endpoint = httpx.URL("http://127.0.0.1:8080/v1/chat/completions")

    # Prove the synthetic environment would route this exact endpoint through
    # a proxy in an ordinary HTTPX client, rather than being a no-op fixture.
    with httpx.Client(trust_env=True) as control:
        assert control._transport_for_url(endpoint) is not control._transport

    with InstructorClient(
        base_url="http://127.0.0.1:8080/v1",
        model="explicit-test-model",
        api_key=KEY,
    ) as client:
        transport_client = client._sdk._client
        assert transport_client._transport_for_url(endpoint) is transport_client._transport
        assert not transport_client._mounts


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mode": "unsupported"},
        {"timeout_seconds": 0},
        {"timeout_seconds": float("inf")},
        {"max_tokens": 0},
        {"max_tokens": True},
        {"temperature": float("nan")},
    ],
)
def test_invalid_client_settings_fail_before_network(kwargs):
    def handler(request):
        raise AssertionError("No HTTP request should be made")

    with pytest.raises(ValueError):
        make_client(handler, **kwargs)
