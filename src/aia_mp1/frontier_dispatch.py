"""Single-start hosted judge transport with a conservative per-run token budget."""

import json
from dataclasses import dataclass

from openai import OpenAI

from .evaluation_schemas import Judgment

MODEL = "gpt-6.2-astra"
MAX_STARTS = 50
MAX_INPUT_TOKENS = 12_000
MAX_COMPLETION_TOKENS = 8_192
INPUT_RATE_PER_MILLION = 10.0  # Higher of listed input and cache-write rates.
OUTPUT_RATE_PER_MILLION = 40.0
CAP_USD = 25.0
RATING_SCHEMA = {
    "type": "object",
    "properties": {
        dimension: {
            "type": "object",
            "properties": {"decision": {"type": "integer"}, "justification": {"type": "string"}},
            "required": ["decision", "justification"],
            "additionalProperties": False,
        }
        for dimension in ("D1", "D2", "D3", "D4", "D5", "D6")
    },
    "required": ["D1", "D2", "D3", "D4", "D5", "D6"],
    "additionalProperties": False,
}


def upper_bound_usd(starts: int) -> float:
    if type(starts) is not int or not 0 <= starts <= MAX_STARTS:
        raise ValueError("start count outside the frozen allocation")
    return (
        starts
        * (
            MAX_INPUT_TOKENS * INPUT_RATE_PER_MILLION
            + MAX_COMPLETION_TOKENS * OUTPUT_RATE_PER_MILLION
        )
        / 1_000_000
    )


@dataclass(frozen=True)
class FrontierResult:
    judgment: Judgment | None
    raw: dict | None
    error_type: str | None
    error: str | None
    input_tokens: int | None
    output_tokens: int | None


def request_once(client: OpenAI, messages: list[dict[str, str]]) -> FrontierResult:
    """Call once; the caller must journal the start before invoking this function."""
    if len(messages) != 2 or any(set(m) != {"role", "content"} for m in messages):
        raise ValueError("expected a frozen two-message paired input")
    # UTF-8 bytes conservatively bound input tokens for this text-only bundle.
    # Reserve 2,000 more tokens for chat/JSON framing and abort if measured
    # usage exceeds the budgeted maximum.
    wire_bytes = len(json.dumps(messages, ensure_ascii=False).encode("utf-8"))
    if wire_bytes > MAX_INPUT_TOKENS - 2_000:
        raise ValueError("paired input exceeds the budgeted input envelope")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "judge_ratings",
                    "strict": True,
                    "schema": RATING_SCHEMA,
                },
            },
            reasoning_effort="medium",
            max_completion_tokens=MAX_COMPLETION_TOKENS,
            service_tier="default",
        )
        raw = response.model_dump(mode="json")
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None
        if response.model != MODEL:
            raise ValueError("response model differs from the approved model")
        if not usage or input_tokens > MAX_INPUT_TOKENS or output_tokens > MAX_COMPLETION_TOKENS:
            raise ValueError("missing or over-budget provider token usage")
        if len(response.choices) != 1 or response.choices[0].finish_reason != "stop":
            raise ValueError("completion did not finish normally")
        judgment = Judgment.model_validate_json(response.choices[0].message.content)
        return FrontierResult(judgment, raw, None, None, input_tokens, output_tokens)
    except Exception as exc:
        # The OpenAI exception may contain request details; only retain its type.
        # A caller can inspect raw only when the SDK returned successfully.
        return FrontierResult(
            None,
            locals().get("raw"),
            type(exc).__name__,
            "provider request or judgment validation failed",
            locals().get("input_tokens"),
            locals().get("output_tokens"),
        )
