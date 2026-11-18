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


def record_transport_failure(ledger, start_sha256, error: Exception):
    """Persist an explicit transport exception without assuming the server stopped.

    Exception messages, request objects and headers can contain credentials;
    retain only the exception class and the unresolved-outcome classification.
    The pending start remains consumed and cannot be finished or retried by this
    runner. Any later-discovered response requires separate evidence inspection.
    """
    if not isinstance(error, Exception):
        raise ValueError("an actual transport exception is required")
    _, _, state, _ = ledger.read()
    pending = state["pending"]
    if pending is None or digest(pending) != start_sha256:
        raise ValueError("transport failure does not match the pending request")
    payload = {
        "error_type": type(error).__name__,
        "classification": "transport_exception_server_outcome_unknown",
        "retry_permitted": False,
    }
    state = ledger.append(
        {
            "kind": "transport_failure",
            "start_sha256": start_sha256,
            "failure_sha256": digest(payload),
        },
        payload,
    )
    return {"state": state, "execution_enabled": False}


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


def _require_prepared_insufficient(manifest, item_id, observations):
    experiment = manifest["experiment"]
    if experiment.get("uncertainty_policy") != "audited-materiality-v1":
        return
    frozen = experiment.get("prepared_insufficient")
    if not isinstance(frozen, list):
        raise ValueError("uncertain claims are not frozen")
    required = {row["check_id"] for row in frozen if row["item_id"] == item_id}
    found = {row.check_id for row in observations.observations if row.status == "insufficient"}
    if not required <= found:
        raise ValueError("verifier promoted an explicitly insufficient claim")


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
    _require_prepared_insufficient(manifest, waiting["item_id"], observations)
    scoring_input = build_scoring_input(
        plan,
        content,
        rubric,
        source_root,
        observations,
        audit,
        allow_insufficient=manifest["experiment"].get("uncertainty_policy")
        == "audited-materiality-v1",
    )
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


def accepted_fact_material(ledger, item_id, plan, content, rubric, source_root):
    """Revalidate the saved accepted facts for request construction or score audit."""
    manifest, records, state, _ = ledger.read()
    if state["cases"].get(item_id, {}).get("facts") != "accepted":
        raise ValueError("case has no accepted fact audit")
    binding = case_binding(plan, content, rubric)
    if manifest["experiment"].get("case_bindings", {}).get(item_id) != binding:
        raise ValueError("case differs from frozen experiment")
    payloads = _payloads(ledger)
    fact_start = next(
        r
        for r in records
        if r["kind"] == "start" and r["item_id"] == item_id and r["stage"] == "facts"
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
    _require_prepared_insufficient(manifest, item_id, observations)
    audit_class = (
        RuntimeFactAudit
        if isinstance(plan, RuntimeEvidencePlan)
        else EvidenceFactAudit
        if isinstance(plan, EvidencePlan)
        else FactAudit
    )
    fact_audit = audit_class.model_validate(fact_payload["audit"])
    scoring_input = build_scoring_input(
        plan,
        content,
        rubric,
        source_root,
        observations,
        fact_audit,
        allow_insufficient=manifest["experiment"].get("uncertainty_policy")
        == "audited-materiality-v1",
    )
    if (
        fact_payload.get("case_binding") != binding
        or fact_payload.get("observations_sha256") != fingerprint(observations)
        or fact_payload.get("scoring_input_sha256") != digest(scoring_input)
    ):
        raise ValueError("accepted fact audit lineage changed")
    return scoring_input, observations, fact_audit


def accept_score_audit(ledger, plan, content, rubric, source_root, audit):
    """Reconstruct facts and scores from the journal before accepting a score audit."""
    manifest, records, state, _ = ledger.read()
    waiting = state["awaiting_audit"]
    if waiting is None or waiting["stage"] != "score":
        raise ValueError("no scorer completion awaits a score audit")
    scoring_input, observations, fact_audit = accepted_fact_material(
        ledger, waiting["item_id"], plan, content, rubric, source_root
    )
    binding = case_binding(plan, content, rubric)
    payloads = _payloads(ledger)
    finish = next(r for r in records if digest(r) == waiting["finish_sha256"])
    start = next(r for r in records if digest(r) == finish["start_sha256"])
    if payloads[digest(start)].get("case_binding") != binding or payloads[digest(start)].get(
        "scoring_input_sha256"
    ) != digest(scoring_input):
        raise ValueError("scorer lineage differs from accepted facts")
    scores = Scores.model_validate(completion_json(payloads[digest(finish)]))
    report = inspect_scores(
        plan,
        content,
        rubric,
        source_root,
        observations,
        fact_audit,
        scores,
        audit,
        allow_insufficient=manifest["experiment"].get("uncertainty_policy")
        == "audited-materiality-v1",
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
