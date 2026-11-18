"""Synthetic transport and spend controls for the approved frontier arm."""

import json
from types import SimpleNamespace

from aia_mp1.frontier_dispatch import CAP_USD, request_once, upper_bound_usd


class FakeResponse:
    model = "gpt-6.2-astra"

    def __init__(self, content, finish_reason="stop", prompt_tokens=300, completion_tokens=500):
        self.choices = [
            SimpleNamespace(finish_reason=finish_reason, message=SimpleNamespace(content=content))
        ]
        self.usage = SimpleNamespace(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )

    def model_dump(self, **_):
        return {
            "model": self.model,
            "choices": [{"message": {"content": self.choices[0].message.content}}],
        }


class FakeClient:
    def __init__(self, response):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.response = response

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


MESSAGES = [
    {"role": "system", "content": "Return JSON."},
    {"role": "user", "content": "Synthetic candidate."},
]
VALID = json.dumps(
    {
        dimension: {"decision": 1, "justification": "Synthetic justification."}
        for dimension in ("D1", "D2", "D3", "D4", "D5", "D6")
    }
)


def test_approved_request_shape_and_worst_case_cap():
    assert upper_bound_usd(50) <= CAP_USD
    client = FakeClient(FakeResponse(VALID))
    result = request_once(client, MESSAGES)
    assert result.judgment is not None
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["model"] == "gpt-6.2-astra"
    assert call["reasoning_effort"] == "medium"
    assert call["max_completion_tokens"] == 8192
    assert call["response_format"]["type"] == "json_schema"
    assert "temperature" not in call
    assert "tools" not in call


def test_invalid_completion_is_preserved_and_not_retried():
    client = FakeClient(FakeResponse("{}"))
    result = request_once(client, MESSAGES)
    assert result.judgment is None
    assert result.raw is not None
    assert result.error_type == "ValidationError"
    assert len(client.calls) == 1


def test_truncated_completion_is_not_a_valid_judgment():
    result = request_once(FakeClient(FakeResponse(VALID, finish_reason="length")), MESSAGES)
    assert result.judgment is None
    assert result.error_type == "ValueError"
