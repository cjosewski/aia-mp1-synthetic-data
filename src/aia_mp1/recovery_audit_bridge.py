"""Bind technical audits and completion records to retained model responses."""

import json
from typing import Literal

from .evidence_judge import StrictModel, completion_json
from .factcheck import SHA
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
from .schemas import NonBlank
from .tracing import digest


class AuditRejection(StrictModel):
    """Attributed technical stop, never a human rating or accepting audit."""

    finish_sha256: SHA
    auditor: NonBlank
    origin: Literal["assistant_review", "human_review"]
    reviewed_at: NonBlank
    reason: NonBlank


def reject_audit(ledger, rejection: AuditRejection):
    """Retain an objection and halt without rewriting any prior response or audit.

    An auditor may stop at the first decisive problem; a full accepting review
    is therefore not required. Attribution is a record, not authentication.
    """
    rejection = AuditRejection.model_validate(rejection.model_dump(mode="json"))
    _, _, state, _ = ledger.read()
    waiting = state["awaiting_audit"]
    if waiting is None or waiting["finish_sha256"] != rejection.finish_sha256:
        raise ValueError("rejection must identify the completion awaiting review")
    payload = {
        "rejection": rejection.model_dump(mode="json"),
        "item_id": waiting["item_id"],
        "stage": waiting["stage"],
        "calibration_eligible": False,
    }
    state = ledger.append(
        {
            "kind": "audit",
            "finish_sha256": rejection.finish_sha256,
            "audit_sha256": digest(payload),
            "accepted": False,
        },
        payload,
    )
    return {"state": state, "execution_enabled": False}


def record_completion(ledger, start_sha256, raw):
    """Retain a returned response and derive schema validity, never semantic truth.

    Call only for an actual response, not a missing/unknown transport outcome.
    The caller supplies the durable start identity to prevent a late response
    from being attributed to a subsequent request. Invalid returns consume their
    allocated slot; valid returns still require the separate semantic audit.
    """
    _, _, state, _ = ledger.read()
    pending = state["pending"]
    if pending is None or digest(pending) != start_sha256:
        raise ValueError("completion does not match the pending request")
    if not isinstance(raw, (dict, str)):
        raise ValueError(
            "retain a response object or original response text; missing outcome stays pending"
        )
    schema = Observations if pending["stage"] == "facts" else Scores
    error_type = None
    try:
        schema.model_validate(completion_json(raw))
    except (ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        error_type = type(exc).__name__
    state = ledger.append(
        {
            "kind": "finish",
            "start_sha256": start_sha256,
            "completion_sha256": digest(raw),
            "structurally_valid": error_type is None,
        },
        raw,
    )
    return {"state": state, "schema_error_type": error_type, "execution_enabled": False}


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
