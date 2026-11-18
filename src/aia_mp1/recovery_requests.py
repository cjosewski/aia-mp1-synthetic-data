"""Build the next recovery request from frozen preparation and accepted facts."""

import json

from .factcheck import source_file
from .factcheck_stages import load_json
from .recovery_audit_bridge import accepted_fact_material, case_binding
from .recovery_evidence import evidence_request, parse_plan
from .recovery_packet import require_ready
from .recovery_scoring import scoring_request
from .recovery_wire import prepare_wire


def prepare_next(ledger, packet_root):
    """Read-only preparation; actual runtime/token preflight is still required."""
    manifest, _, state, _ = ledger.read()
    next_slot = state["next_request"]
    if next_slot is None:
        raise ValueError("no unused audit-released request is available")
    experiment = manifest["experiment"]
    expected = experiment.get("packet_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("frozen preparation identity is required")
    packet = require_ready(packet_root, expected)
    expected_policy = (
        "audited-materiality-v1" if packet["protocol"] == "recovery-preparation-v2" else None
    )
    if experiment.get("uncertainty_policy") != expected_policy:
        raise ValueError("frozen uncertainty policy differs from preparation version")
    if (
        packet["protocol"] == "recovery-preparation-v2"
        and experiment.get("prepared_insufficient") != packet["insufficient_claims"]
    ):
        raise ValueError("frozen insufficient claims differ from preparation")
    if experiment.get("case_bindings") != packet["case_bindings"]:
        raise ValueError("experiment case bindings differ from preparation")
    if manifest["case_ids"] != list(packet["case_bindings"]):
        raise ValueError("experiment case order differs from frozen selection")
    item, stage = next_slot["item_id"], next_slot["stage"]
    content = load_json(source_file(packet_root, f"{item}/input.json"))
    plan = parse_plan(load_json(source_file(packet_root, f"{item}/plan.json")))
    rubric = load_json(source_file(packet_root, "rubric.json"))
    if case_binding(plan, content, rubric) != packet["case_bindings"][item]:
        raise ValueError("case changed during preparation replay")
    if stage == "facts":
        body = evidence_request(plan, content, rubric, packet_root / "sources")
    else:
        accepted, _, _ = accepted_fact_material(
            ledger, item, plan, content, rubric, packet_root / "sources"
        )
        body = scoring_request(accepted)
    prompts = experiment.get("prompts", {})
    if set(prompts) != {"facts", "score"} or any(
        not isinstance(value, str) or not value.strip() for value in prompts.values()
    ):
        raise ValueError("both stage prompts must be frozen and nonblank")
    policy = experiment["transport_policy"]
    request = {
        key: policy[key] for key in ("model", "temperature", "max_tokens", "timeout_seconds")
    }
    request["messages"] = [
        {"role": "system", "content": prompts[stage]},
        {"role": "user", "content": json.dumps(body, ensure_ascii=False, separators=(",", ":"))},
    ]
    return {
        **next_slot,
        "request": request,
        "receipt": prepare_wire(request, stage),
        "binding": packet["case_bindings"][item],
        "endpoint": policy["endpoint"],
        "packet_sha256": expected,
        "execution_enabled": False,
    }
