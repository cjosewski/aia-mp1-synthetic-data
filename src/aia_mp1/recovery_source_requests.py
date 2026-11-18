"""Read-only next-request builder for the versioned source-ID recovery protocol."""

import json

from .factcheck import source_file
from .factcheck_stages import load_json
from .recovery_audit_bridge import case_binding
from .recovery_evidence import parse_plan
from .recovery_packet import require_ready
from .recovery_source_audit import accepted_source_fact_material
from .recovery_source_contract import require_source_contract
from .recovery_source_refs import source_request
from .recovery_source_scoring import source_scoring_request
from .recovery_source_wire import prepare_source_wire


def prepare_source_next(ledger, packet_root):
    """Bind one unused slot to frozen packet, prompts, policy and exact wire."""
    manifest, _, state, _ = ledger.read()
    next_slot = state["next_request"]
    if next_slot is None:
        raise ValueError("no unused audit-released source-ID request")
    experiment = manifest["experiment"]
    require_source_contract(experiment)
    expected = experiment.get("packet_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("frozen source preparation identity is required")
    packet = require_ready(packet_root, expected)
    if (
        packet["protocol"] != "recovery-preparation-v2"
        or experiment.get("source_protocol") != "recovery-source-refs-v1"
        or experiment.get("uncertainty_policy") != "audited-materiality-v1"
        or experiment.get("prepared_insufficient") != packet["insufficient_claims"]
        or experiment.get("case_bindings") != packet["case_bindings"]
        or manifest["case_ids"] != list(packet["case_bindings"])
    ):
        raise ValueError("source-ID experiment differs from frozen packet or policy")
    item, stage = next_slot["item_id"], next_slot["stage"]
    content = load_json(source_file(packet_root, f"{item}/input.json"))
    plan = parse_plan(load_json(source_file(packet_root, f"{item}/plan.json")))
    rubric = load_json(source_file(packet_root, "rubric.json"))
    binding = case_binding(plan, content, rubric)
    if binding != packet["case_bindings"][item]:
        raise ValueError("case changed during source-ID replay")
    if stage == "facts":
        body = source_request(plan, content, rubric, packet_root / "sources")
        body["prepared_insufficient"] = [
            row for row in packet["insufficient_claims"] if row["item_id"] == item
        ]
    else:
        accepted, _, _ = accepted_source_fact_material(
            ledger, item, plan, content, rubric, packet_root / "sources"
        )
        body = source_scoring_request(accepted)
    prompts = experiment.get("prompts")
    if (
        not isinstance(prompts, dict)
        or set(prompts) != {"facts", "score"}
        or any(not isinstance(value, str) or not value.strip() for value in prompts.values())
    ):
        raise ValueError("both source-ID prompts must be frozen")
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
        "receipt": prepare_source_wire(request, stage),
        "binding": binding,
        "endpoint": policy["endpoint"],
        "packet_sha256": expected,
        "execution_enabled": False,
    }
