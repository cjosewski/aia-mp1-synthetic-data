"""Single-start source-ID transport; caller must complete live preflight."""

import json

import httpx

from .factcheck_transport import loopback_url
from .model_client import InstructorClient
from .recovery_source_audit import record_source_completion
from .recovery_source_contract import require_source_contract
from .recovery_source_wire import SCHEMAS, verify_source_wire
from .recovery_transport import _StartedTransport
from .tracing import digest


def dispatch_source_next(
    ledger, item_id, stage, request, receipt, binding, endpoint, key, *, transport=None
):
    """Record one start before network I/O, then retain the sole known outcome."""
    loopback_url(endpoint)
    manifest, _, state, _ = ledger.read()
    if state["next_request"] != {"item_id": item_id, "stage": stage}:
        raise ValueError("source request is not an unused audit-released slot")
    experiment = manifest["experiment"]
    require_source_contract(experiment)
    if (
        experiment.get("source_protocol") != "recovery-source-refs-v1"
        or experiment.get("uncertainty_policy") != "audited-materiality-v1"
    ):
        raise ValueError("frozen source-ID protocol required")
    policy = {k: request[k] for k in ("model", "temperature", "max_tokens", "timeout_seconds")}
    policy["endpoint"] = endpoint
    if experiment.get("transport_policy") != policy:
        raise ValueError("source transport settings differ from frozen policy")
    if experiment.get("case_bindings", {}).get(item_id) != binding:
        raise ValueError("source case binding differs from frozen experiment")
    wire = verify_source_wire(request, stage, receipt)
    payload = {"request": request, "wire_receipt": receipt, "case_binding": binding}
    if stage == "score":
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
        raise ValueError("source dispatch did not reach the single recorded boundary")
    if guarded.failure_recorded:
        return {
            "state": ledger.read()[2],
            "outcome": "transport_failure",
            "calibration_eligible": False,
        }
    if result.raw_response is None:
        raise ValueError("source response missing; pending outcome requires inspection")
    raw = result.raw_response
    if isinstance(raw, dict) and "choices" in raw and raw.get("model") != request["model"]:
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
    finished = record_source_completion(ledger, digest(start), raw)
    return {**finished, "outcome": "response_retained", "calibration_eligible": False}
