"""Bind accepting fact audits to frozen cases and retained raw completions."""

import json

from .evidence_judge import completion_json
from .recovery_checks import Observations
from .recovery_evidence import EvidencePlan, RuntimeEvidencePlan
from .recovery_scoring import (
    EvidenceFactAudit,
    FactAudit,
    RuntimeFactAudit,
    Scores,
    build_scoring_input,
    fingerprint,
    inspect_scores,
)
from .tracing import digest


def case_binding(plan, content, rubric):
    return {
        "plan_sha256": fingerprint(plan),
        "input_sha256": digest(content),
        "rubric_sha256": digest(rubric),
    }


def _payloads(ledger):
    envelopes = [
        json.loads(line)
        for line in (ledger.directory / "events.jsonl").read_text("utf-8").splitlines()
    ]
    for row in envelopes:
        ledger.check_payload(row["record"], row["payload"])
    return {digest(row["record"]): row["payload"] for row in envelopes}


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
    payloads = _payloads(ledger)
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


def accept_score_audit(ledger, plan, content, rubric, source_root, audit):
    """Reconstruct facts and scores from the journal before accepting a score audit.

    The scorer start must bind the exact scoring input released by the accepted
    fact audit. Neither observations nor scores are supplied by the caller.
    """
    manifest, records, state, _ = ledger.read()
    waiting = state["awaiting_audit"]
    if waiting is None or waiting["stage"] != "score":
        raise ValueError("no scorer completion awaits a score audit")
    binding = case_binding(plan, content, rubric)
    if manifest["experiment"].get("case_bindings", {}).get(waiting["item_id"]) != binding:
        raise ValueError("case differs from frozen experiment")
    payloads = _payloads(ledger)
    finish = next(r for r in records if digest(r) == waiting["finish_sha256"])
    start = next(r for r in records if digest(r) == finish["start_sha256"])
    fact_start = next(
        r
        for r in records
        if r["kind"] == "start" and r["item_id"] == waiting["item_id"] and r["stage"] == "facts"
    )
    fact_finish = next(
        r for r in records if r["kind"] == "finish" and r["start_sha256"] == digest(fact_start)
    )
    accepted = next(
        r
        for r in records
        if r["kind"] == "audit" and r["finish_sha256"] == digest(fact_finish) and r["accepted"]
    )
    fact_payload = payloads[digest(accepted)]
    if payloads[digest(fact_start)].get("case_binding") != binding:
        raise ValueError("verifier start belongs to different case inputs")
    observations = Observations.model_validate(completion_json(payloads[digest(fact_finish)]))
    audit_class = (
        RuntimeFactAudit
        if isinstance(plan, RuntimeEvidencePlan)
        else EvidenceFactAudit
        if isinstance(plan, EvidencePlan)
        else FactAudit
    )
    fact_audit = audit_class.model_validate(fact_payload["audit"])
    scoring_input = build_scoring_input(
        plan, content, rubric, source_root, observations, fact_audit
    )
    if (
        fact_payload.get("case_binding") != binding
        or fact_payload.get("observations_sha256") != fingerprint(observations)
        or fact_payload.get("scoring_input_sha256") != digest(scoring_input)
        or payloads[digest(start)].get("case_binding") != binding
        or payloads[digest(start)].get("scoring_input_sha256") != digest(scoring_input)
    ):
        raise ValueError("scorer lineage differs from accepted facts")
    scores = Scores.model_validate(completion_json(payloads[digest(finish)]))
    report = inspect_scores(
        plan, content, rubric, source_root, observations, fact_audit, scores, audit
    )
    if report["status"] != "audited_development" or report["judgment"] is None:
        raise ValueError("score audit has unresolved objections")
    payload = {"audit": audit.model_dump(mode="json"), "report": report, "case_binding": binding}
    state = ledger.append(
        {
            "kind": "audit",
            "finish_sha256": digest(finish),
            "audit_sha256": digest(payload),
            "accepted": True,
        },
        payload,
    )
    return {"state": state, "report": report, "execution_enabled": False}
