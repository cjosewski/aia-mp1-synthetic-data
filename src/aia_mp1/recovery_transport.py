"""Single-request recovery transport; caller owns evidence/runtime preflight.

This is an internal adapter, not an operator command or experiment authorization.
The top-level runner must validate source readiness, frozen prompts, runtime and
token fit before calling it. Existing pending starts can never be redispatched.
"""

import json

import httpx

from .factcheck_transport import loopback_url
from .model_client import InstructorClient
from .recovery_audit_bridge import record_completion, record_transport_failure
from .recovery_wire import SCHEMAS, verify_wire
from .tracing import digest


class _StartedTransport(httpx.BaseTransport):
    def __init__(self, ledger, start, payload, wire, inner):
        self.ledger, self.start, self.payload = ledger, start, payload
        self.wire, self.inner = wire, inner
        self.calls = 0
        self.failure_recorded = False

    def handle_request(self, request):
        if self.calls or json.loads(request.content) != self.wire:
            raise ValueError("unexpected wire or hidden retry")
        # Append must complete, including its checkpoint, before any network I/O.
        # Concurrent callers can inspect the same ready state, but only one can
        # append its start successfully under the journal's single-writer lock.
        self.ledger.append(self.start, self.payload)
        self.calls += 1
        try:
            return self.inner.handle_request(request)
        except httpx.TransportError as exc:
            record_transport_failure(self.ledger, digest(self.start), exc)
            self.failure_recorded = True
            raise

    def close(self):
        self.inner.close()


def dispatch_next(
    ledger, item_id, stage, request, receipt, binding, endpoint, key, *, transport=None
):
    """Persist one new start, send once, and preserve its result for audit.

    Requires a frozen transport_policy and case binding in the journal manifest.
    A policy alone is not source/runtime approval; no CLI exposes this adapter.
    Call only after the top-level runner's evidence and fresh runtime preflight.
    The policy pins endpoint and all non-message request settings. Prompt/input
    construction and actual token-fit verification remain caller responsibilities.
    """
    loopback_url(endpoint)
    manifest, _, state, _ = ledger.read()
    if state["next_request"] != {"item_id": item_id, "stage": stage}:
        raise ValueError("request is not the next unused, audit-released slot")
    policy = {k: request[k] for k in ("model", "temperature", "max_tokens", "timeout_seconds")}
    policy["endpoint"] = endpoint
    if manifest["experiment"].get("transport_policy") != policy:
        raise ValueError("transport settings differ from frozen experiment")
    case_bindings = manifest["experiment"].get("case_bindings", {})
    if (
        item_id not in case_bindings
        or not isinstance(binding, dict)
        or case_bindings[item_id] != binding
    ):
        raise ValueError("case binding differs from frozen experiment")
    wire = verify_wire(request, stage, receipt)
    payload = {"request": request, "wire_receipt": receipt, "case_binding": binding}
    if stage == "score":
        # The score adapter later checks this value against the accepted facts.
        body = json.loads(request["messages"][1]["content"])
        payload["scoring_input_sha256"] = body["scoring_input_sha256"]
    start = {"kind": "start", "item_id": item_id, "stage": stage, "request_sha256": digest(payload)}
    guarded = _StartedTransport(
        ledger,
        start,
        payload,
        wire,
        transport if transport is not None else httpx.HTTPTransport(retries=0),
    )
    with InstructorClient(
        base_url=endpoint,
        api_key=key,
        model=request["model"],
        mode="json",
        temperature=request["temperature"],
        max_tokens=request["max_tokens"],
        timeout_seconds=request["timeout_seconds"],
        response_model=SCHEMAS[stage],
        _transport=guarded,
    ) as client:
        result = client.generate(request["messages"])
    if guarded.calls != 1:
        raise ValueError("dispatch did not reach the single recorded network boundary")
    if guarded.failure_recorded:
        return {
            "state": ledger.read()[2],
            "outcome": "transport_failure",
            "calibration_eligible": False,
        }
    if result.raw_response is None:
        # Client-boundary bugs and process interruptions do not release an attempt.
        raise ValueError("response missing after dispatch; pending outcome requires inspection")
    raw = result.raw_response
    if isinstance(raw, dict) and "choices" in raw and raw.get("model") != request["model"]:
        # A returned completion is known, but cannot belong to the frozen model.
        # Preserve it exactly, halt all later slots, and never offer it for audit.
        state = ledger.append(
            {
                "kind": "response_identity_failure",
                "start_sha256": digest(start),
                "completion_sha256": digest(raw),
            },
            raw,
        )
        return {
            "state": state,
            "outcome": "response_identity_failure",
            "calibration_eligible": False,
        }
    finished = record_completion(ledger, digest(start), result.raw_response)
    return {**finished, "outcome": "response_retained", "calibration_eligible": False}
