"""Native Mac V8 transport, exact Instructor wire inspection and token preflight."""

import hashlib
import json
import platform
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .factcheck_stages import (
    SCHEMAS,
    Completion,
    Experiment,
    Ledger,
    Runtime,
    new_json,
    request_for,
)
from .model_client import InstructorClient
from .tracing import digest

PROPERTIES = ("build_info", "total_slots", "default_generation_settings", "chat_template")


def loopback_url(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.path != "/v1"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("V8 requires a local HTTP loopback endpoint ending /v1")
    return url.removesuffix("/v1")


def client_for(request: dict, stage: str, endpoint: str, key: str, transport=None):
    return InstructorClient(
        base_url=endpoint,
        api_key=key,
        model=request["model"],
        mode="json",
        temperature=request["temperature"],
        max_tokens=request["max_tokens"],
        timeout_seconds=request["timeout_seconds"],
        response_model=SCHEMAS[stage],
        _transport=transport,
    )


def wire_request(request: dict, stage: str) -> dict:
    """Capture the actual locked Instructor serialization using a local mock only."""
    captured = []

    def capture(wire):
        captured.append(json.loads(wire.content))
        return httpx.Response(400, json={"error": {"message": "Offline wire inspection"}})

    with client_for(
        request, stage, "http://127.0.0.1:1/v1", "offline-placeholder", httpx.MockTransport(capture)
    ) as client:
        client.generate(request["messages"])
    if len(captured) != 1:
        raise ValueError("Instructor serialization must make exactly one intercepted request")
    return captured[0]


class VerifiedTransport(httpx.BaseTransport):
    def __init__(self, wire: dict, inner=None):
        self.expected = wire
        self.inner = inner if inner is not None else httpx.HTTPTransport(retries=0)
        self.calls = 0

    def handle_request(self, request):
        if self.calls or json.loads(request.content) != self.expected:
            raise ValueError("wire request differs from preflight or attempts a hidden retry")
        self.calls += 1
        return self.inner.handle_request(request)

    def close(self):
        self.inner.close()


def dispatch(
    request: dict, stage: str, wire: dict, endpoint: str, key: str, transport=None
) -> Completion:
    loopback_url(endpoint)
    started = time.monotonic()
    verified = VerifiedTransport(wire, transport)
    with client_for(request, stage, endpoint, key, verified) as client:
        result = client.generate(request["messages"])
    if verified.calls != 1:
        # The recorded start remains unknown; never turn a client-boundary bug into a retry.
        raise ValueError("no verified dispatch occurred; preserve pending start for inspection")
    return Completion(
        raw_response=result.raw_response,
        transport_failure=result.raw_response is None,
        elapsed_seconds=time.monotonic() - started,
    )


class LocalServer:
    def __init__(self, endpoint: str, key: str, transport=None):
        self.base = loopback_url(endpoint)
        self.client = httpx.Client(
            base_url=self.base,
            timeout=15,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            headers={"Authorization": "Bearer " + key},
        )

    def close(self):
        self.client.close()

    def json(self, path: str, body=None):
        response = self.client.get(path) if body is None else self.client.post(path, json=body)
        response.raise_for_status()
        return response.json()

    def observe(self, experiment: Experiment, properties: dict) -> dict:
        props = self.json("/props")
        models = self.json("/v1/models")["data"]
        if self.json("/health").get("status") != "ok" or len(models) != 1:
            raise ValueError("expected one healthy local model")
        if any(props.get(key) != properties.get(key) for key in PROPERTIES):
            raise ValueError("native runtime differs from archived fixed V7 settings")
        observed = Runtime(
            model=models[0]["id"],
            model_sha256=experiment.runtime.model_sha256,
            build=props["build_info"],
            template_sha256=digest(props["chat_template"]),
            context_size=props["default_generation_settings"]["n_ctx"],
            slots=props["total_slots"],
            temperature=0.1,
            max_tokens=4096,
            timeout_seconds=300,
        ).model_dump()
        if observed != experiment.runtime.model_dump() or props["model_path"] != observed["model"]:
            raise ValueError("observed model/runtime does not match the frozen experiment")
        return props

    def token_fit(self, wire: dict, context: int, reserve: int = 0) -> dict:
        prompt = self.json("/apply-template", wire)["prompt"]
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("server did not return a rendered chat prompt")
        tokens = self.json(
            "/tokenize",
            {
                "content": prompt,
                "add_special": True,
                "parse_special": True,
            },
        )["tokens"]
        if not isinstance(tokens, list) or any(type(token) is not int for token in tokens):
            raise ValueError("server tokenization result is malformed")
        required = len(tokens) + wire["max_tokens"] + reserve
        return {
            "wire_sha256": digest(wire),
            "rendered_prompt_sha256": digest(prompt),
            "prompt_tokens": len(tokens),
            "output_tokens": wire["max_tokens"],
            "reserve_tokens": reserve,
            "context_size": context,
            "required_tokens": required,
            "fits": required <= context,
        }


def verify_weight(experiment: Experiment, props: dict) -> dict:
    path = Path(props["model_path"])
    sha = hashlib.sha256()
    before = path.stat()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            sha.update(block)
    after = path.stat()
    if sha.hexdigest() != experiment.runtime.model_sha256 or (
        before.st_size,
        before.st_mtime_ns,
    ) != (after.st_size, after.st_mtime_ns):
        raise ValueError("served weight hash or file identity differs")
    return {"size": after.st_size, "mtime_ns": after.st_mtime_ns, "sha256": sha.hexdigest()}


def run_prepared(
    ledger: Ledger,
    source_root: Path,
    properties: dict,
    endpoint: str,
    key: str,
    *,
    execute: bool = False,
) -> dict:
    """Run only the frozen schedule; actual B token fit is checked after accepting A."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("live V8 execution requires native Apple Silicon macOS")
    experiment, state = ledger.read()
    server = LocalServer(endpoint, key)
    try:
        props = server.observe(experiment, properties)
        weight = verify_weight(experiment, props)
        receipt = ledger.directory / f"preflight-{state['count']:04d}.json"
        preflight = {
            "runtime": experiment.runtime.model_dump(),
            "weight": weight,
            "properties_sha256": digest({k: props[k] for k in PROPERTIES}),
            "requests": [],
            "inference": False,
        }
        # Known control/A messages must fit before any inference. Stage B adds the
        # actual memo later; reserve one verifier completion plus metadata headroom.
        for case in experiment.cases:
            for stage in ("control", "facts"):
                request = request_for(experiment, case, stage, None)
                fit = server.token_fit(wire_request(request, stage), 16384)
                preflight["requests"].append({"item_id": case.item_id, "stage": stage, **fit})
            request = request_for(experiment, case, "control", None)
            request["messages"][0]["content"] = (
                experiment.prompts.score
                + "\n\nFrozen rubric:\n"
                + json.dumps(experiment.rubric, ensure_ascii=False)
            )
            request["response_schema"] = SCHEMAS["score"].model_json_schema()
            fit = server.token_fit(wire_request(request, "score"), 16384, reserve=5120)
            preflight["requests"].append(
                {
                    "item_id": case.item_id,
                    "stage": "score_reserve",
                    "basis": "4096 verifier tokens + 1024 memo/serialization allowance; actual memo rechecked",
                    **fit,
                }
            )
        if receipt.exists():
            if json.loads(receipt.read_text("utf-8")) != preflight:
                raise ValueError("existing preflight differs; retain and inspect")
        else:
            new_json(receipt, preflight)
        if not all(row["fits"] for row in preflight["requests"]):
            ledger.halt("token_fit")
            return {"stopped": "token_fit", "starts": len(state["starts"])}
        if not execute:
            return {"stopped": "preflight_only", "starts": len(state["starts"])}
        while True:
            experiment, state = ledger.read()
            selected = ledger.next_stage(experiment, state)
            if selected is None:
                reason = state["halt"] or (
                    "unknown_outcome"
                    if state["pending"]
                    else "consecutive_failures"
                    if state["failures"] >= 2
                    else "complete"
                )
                return {"stopped": reason, "starts": len(state["starts"])}
            case, stage, predecessor = selected
            props = server.observe(experiment, properties)
            actual = Path(props["model_path"]).stat()
            if (actual.st_size, actual.st_mtime_ns) != (weight["size"], weight["mtime_ns"]):
                ledger.halt("preflight_mismatch")
                raise ValueError("weights changed after initial full hash verification")
            request = request_for(experiment, case, stage, predecessor)
            wire = wire_request(request, stage)
            fit = server.token_fit(wire, 16384)
            new_json(
                ledger.directory / f"wire-{len(state['starts']) + 1:04d}.json",
                {"request_sha256": digest(request), "wire": wire, "token_fit": fit},
            )
            if not fit["fits"]:
                ledger.halt("token_fit")
                return {"stopped": "token_fit", "starts": len(state["starts"])}
            started = ledger.begin(experiment.runtime.model_dump(), source_root)
            if started["request"] != request:
                raise ValueError(
                    "schedule changed during dispatch preparation; pending start retained"
                )
            completion = dispatch(request, stage, wire, endpoint, key)
            result = ledger.finish(started["attempt_id"], completion)
            print(
                json.dumps(
                    {
                        "item_id": case.item_id,
                        "stage": stage,
                        "attempt_id": started["attempt_id"],
                        "status": result["result"]["status"],
                    }
                ),
                flush=True,
            )
    finally:
        server.close()
