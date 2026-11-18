"""Bind accepting fact audits to frozen cases and retained raw completions."""

import json

from .evidence_judge import completion_json
from .recovery_checks import Observations
from .recovery_scoring import build_scoring_input, fingerprint
from .tracing import digest


def case_binding(plan, content, rubric):
    return {
        "plan_sha256": fingerprint(plan),
        "input_sha256": digest(content),
        "rubric_sha256": digest(rubric),
    }


def accept_fact_audit(ledger, plan, content, rubric, source_root, audit):
    """Accept only after revalidating the saved completion and every fact/audit gate.

    The experiment must freeze case_bindings. Start payloads must carry the same
    binding alongside their request; finish payloads are raw chat completions.
    This adapter never accepts a caller-supplied parsed observation or Boolean.
    It does not authenticate the auditor's expertise or permit model dispatch.
    """
    manifest, records, state, _ = ledger.read()
    waiting = state["awaiting_audit"]
    if waiting is None or waiting["stage"] != "facts":
        raise ValueError("no verifier completion awaits a fact audit")
    binding = case_binding(plan, content, rubric)
    if manifest["experiment"].get("case_bindings", {}).get(waiting["item_id"]) != binding:
        raise ValueError("case differs from frozen experiment")
    finish = next(r for r in records if digest(r) == waiting["finish_sha256"])
    start = next(r for r in records if digest(r) == finish["start_sha256"])
    envelopes = [
        json.loads(line)
        for line in (ledger.directory / "events.jsonl").read_text("utf-8").splitlines()
    ]
    payloads = {digest(row["record"]): row["payload"] for row in envelopes}
    start_payload = payloads[digest(start)]
    raw = payloads[digest(finish)]
    # Recheck the exact payloads used here, not just the earlier journal read.
    ledger.check_payload(start, start_payload)
    ledger.check_payload(finish, raw)
    if start_payload.get("case_binding") != binding:
        raise ValueError("verifier start belongs to different case inputs")
    observations = Observations.model_validate(completion_json(raw))
    scoring_input = build_scoring_input(plan, content, rubric, source_root, observations, audit)
    payload = {
        "audit": audit.model_dump(mode="json"),
        "case_binding": binding,
        "observations_sha256": fingerprint(observations),
        "scoring_input_sha256": digest(scoring_input),
    }
    event = {
        "kind": "audit",
        "finish_sha256": digest(finish),
        "audit_sha256": digest(payload),
        "accepted": True,
    }
    state = ledger.append(event, payload)
    return {"state": state, "scoring_input": scoring_input, "execution_enabled": False}
