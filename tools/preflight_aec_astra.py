"""Exercise the proposed AEC Astra request with the locked SDK and an offline transport."""

import json

import httpx
import instructor
from openai import OpenAI
from prepare_aec_api_evaluation import ROOT
from prepare_aec_source_free import build
from run_aec_development import pin

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, read_text
from aia_mp1.evaluation_schemas import DIMENSIONS, Judgment
from aia_mp1.frontier_dispatch import MODEL
from aia_mp1.tracing import digest

INPUT_LIMIT = 12_000
OUTPUT_LIMIT = 4_096
MAX_STARTS = 60
# Microdollars per token at Standard short-context rates on 2026-11-18.
# The input bound covers even the most expensive (12-hour) cache write.
INPUT_RATE = 20
OUTPUT_RATE = 40
CAP_MICRODOLLARS = 25_000_000
PER_START = INPUT_LIMIT * INPUT_RATE + OUTPUT_LIMIT * OUTPUT_RATE


def request_judgment(adapter, messages):
    return adapter.chat.completions.create_with_completion(
        model=MODEL,
        messages=messages,
        response_model=Judgment,
        service_tier="default",
        reasoning_effort="medium",
        max_completion_tokens=OUTPUT_LIMIT,
        max_retries=0,
    )


def offline(root):
    manifest = build(root)
    bundle = root / "api-source-free-preparation-001"
    output = root / "api-source-free-astra-preflight-001"
    output.mkdir(exist_ok=True)
    fixture = {
        key: {"decision": 0, "justification": "Offline transport fixture."} for key in DIMENSIONS
    }
    schema = Judgment.model_json_schema()
    captures = []

    def intercept(request):
        body = json.loads(request.content)
        if (
            str(request.url) != "https://api.openai.com/v1/chat/completions"
            or request.method != "POST"
            or body["model"] != MODEL
            or body["service_tier"] != "default"
            or body["max_completion_tokens"] != OUTPUT_LIMIT
            or set(body)
            != {
                "model",
                "messages",
                "max_completion_tokens",
                "service_tier",
                "reasoning_effort",
                "response_format",
            }
            or body["reasoning_effort"] != "medium"
            or body["response_format"]["type"] != "json_schema"
            or body["response_format"]["json_schema"]["schema"] != schema
        ):
            raise ValueError("Unexpected provider wire")
        # The complete UTF-8 body includes all rubric, schema and candidate text.
        # Allow another 1,024 tokens for server-side chat framing.
        bound = len(request.content) + 1024
        if bound > INPUT_LIMIT:
            raise ValueError("Wire exceeds the per-start input allocation")
        captures.append(
            (body["messages"], {"wire_sha256": digest(body), "input_token_bound": bound})
        )
        return httpx.Response(
            200,
            json={
                "id": "offline",
                "object": "chat.completion",
                "created": 0,
                "model": MODEL,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(fixture)},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    if MAX_STARTS * PER_START > CAP_MICRODOLLARS:
        raise ValueError("Combined reservation exceeds the proposed cap")
    checks = {}
    with (
        exclusive(output),
        OpenAI(
            api_key="offline-fixture",
            base_url="https://api.openai.com/v1",
            max_retries=0,
            http_client=httpx.Client(
                transport=httpx.MockTransport(intercept), trust_env=False, follow_redirects=False
            ),
        ) as client,
    ):
        adapter = instructor.from_openai(client, mode=instructor.Mode.JSON_SCHEMA)
        for group in ("development", "baseline"):
            path = bundle / f"{group}-requests.json"
            if file_hash(path) != manifest["inputs"][group]["file_sha256"]:
                raise ValueError("Comparison bundle changed")
            checks[group] = {}
            for row in json.loads(read_text(path)):
                size = len(captures)
                judgment, _ = request_judgment(adapter, row["messages"])
                if (
                    len(captures) != size + 1
                    or captures[-1][0] != row["messages"]
                    or judgment.model_dump() != fixture
                ):
                    raise ValueError(
                        "SDK changed the public input, request count or fixture decisions"
                    )
                checks[group][row["item_id"]] = captures[-1][1]
        if {group: len(rows) for group, rows in checks.items()} != {
            "development": 10,
            "baseline": 50,
        } or len(captures) != MAX_STARTS:
            raise ValueError("Expected 60 distinct starts across the two stages")
        receipt = {
            "protocol": "offline-aec-astra-v1",
            "model": MODEL,
            "uses_instructor": True,
            "external_requests": 0,
            "measured_judgments": 0,
            "input_limit": INPUT_LIMIT,
            "output_limit": OUTPUT_LIMIT,
            "price_check": "2026-11-18",
            "pricing_url": "https://developers.openai.com/api/docs/pricing",
            "microdollars_per_input_token": INPUT_RATE,
            "microdollars_per_output_token": OUTPUT_RATE,
            "development_max_usd": 10 * PER_START / 1_000_000,
            "combined_max_usd": MAX_STARTS * PER_START / 1_000_000,
            "largest_input_token_bound": max(c[1]["input_token_bound"] for c in captures),
            "input_manifest_sha256": file_hash(bundle / "manifest.json"),
            "wires": checks,
            "temperature": "Unsupported by Astra. This hosted comparison cannot verify the lower-temperature course requirement.",
        }
        return pin(output / "preflight.json", receipt)


if __name__ == "__main__":
    checked = offline(ROOT.resolve())
    print(json.dumps({k: v for k, v in checked.items() if k != "wires"}, indent=2))
