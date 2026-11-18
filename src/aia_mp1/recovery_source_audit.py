"""Durable source-ID completion and audit adapters; no dispatch capability."""

from .evidence_judge import completion_json
from .recovery_audit_bridge import _payloads, _require_prepared_insufficient, case_binding
from .recovery_evidence import RuntimeEvidencePlan
from .recovery_scoring import (
    EvidenceFactAudit,
    RuntimeFactAudit,
    UncertaintyScoreAudit,
    fingerprint,
)
from .recovery_source_contract import require_source_contract
from .recovery_source_refs import SourceObservations
from .recovery_source_scoring import (
    SourceScores,
    build_source_scoring_input,
    inspect_source_scores,
)
from .tracing import digest


def _require_source_protocol(manifest):
    experiment = manifest["experiment"]
    require_source_contract(experiment)
    if (
        experiment.get("source_protocol") != "recovery-source-refs-v1"
        or experiment.get("uncertainty_policy") != "audited-materiality-v1"
    ):
        raise ValueError("frozen source-ID and uncertainty policy required")


def record_source_completion(ledger, start_sha256, raw):
    """Retain one raw response and derive schema validity, never semantic truth."""
    manifest, _, state, _ = ledger.read()
    _require_source_protocol(manifest)
    pending = state["pending"]
    if pending is None or digest(pending) != start_sha256:
        raise ValueError("source response does not match pending start")
    if not isinstance(raw, (dict, str)):
        raise ValueError("missing outcome stays pending for inspection")
    schema = SourceObservations if pending["stage"] == "facts" else SourceScores
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


def accept_source_fact_audit(ledger, plan, content, rubric, source_root, audit):
    """Bind an attributed technical audit to the exact retained source response."""
    manifest, records, state, _ = ledger.read()
    _require_source_protocol(manifest)
    waiting = state["awaiting_audit"]
    if waiting is None or waiting["stage"] != "facts":
        raise ValueError("no source verifier completion awaits audit")
    binding = case_binding(plan, content, rubric)
    if manifest["experiment"].get("case_bindings", {}).get(waiting["item_id"]) != binding:
        raise ValueError("case differs from frozen experiment")
    finish = next(row for row in records if digest(row) == waiting["finish_sha256"])
    start = next(row for row in records if digest(row) == finish["start_sha256"])
    payloads = _payloads(ledger)
    if payloads[digest(start)].get("case_binding") != binding:
        raise ValueError("source start belongs to another case")
    observations = SourceObservations.model_validate(completion_json(payloads[digest(finish)]))
    _require_prepared_insufficient(manifest, waiting["item_id"], observations)
    scoring_input = build_source_scoring_input(
        plan,
        content,
        rubric,
        source_root,
        observations,
        audit,
        allow_insufficient=True,
    )
    payload = {
        "audit": audit.model_dump(mode="json"),
        "case_binding": binding,
        "observations_sha256": fingerprint(observations),
        "scoring_input_sha256": digest(scoring_input),
    }
    state = ledger.append(
        {
            "kind": "audit",
            "finish_sha256": digest(finish),
            "audit_sha256": digest(payload),
            "accepted": True,
        },
        payload,
    )
    return {"state": state, "scoring_input": scoring_input, "execution_enabled": False}


def accepted_source_fact_material(ledger, item_id, plan, content, rubric, source_root):
    """Reconstruct and revalidate saved accepted facts before score preparation."""
    manifest, records, state, _ = ledger.read()
    _require_source_protocol(manifest)
    if state["cases"].get(item_id, {}).get("facts") != "accepted":
        raise ValueError("case has no accepted source fact audit")
    binding = case_binding(plan, content, rubric)
    if manifest["experiment"].get("case_bindings", {}).get(item_id) != binding:
        raise ValueError("case differs from frozen experiment")
    payloads = _payloads(ledger)
    start = next(
        row
        for row in records
        if row["kind"] == "start" and row["item_id"] == item_id and row["stage"] == "facts"
    )
    finish = next(
        row for row in records if row["kind"] == "finish" and row["start_sha256"] == digest(start)
    )
    accepted = next(
        row
        for row in records
        if row["kind"] == "audit" and row["finish_sha256"] == digest(finish) and row["accepted"]
    )
    audit_payload = payloads[digest(accepted)]
    if payloads[digest(start)].get("case_binding") != binding:
        raise ValueError("source start belongs to another case")
    observations = SourceObservations.model_validate(completion_json(payloads[digest(finish)]))
    _require_prepared_insufficient(manifest, item_id, observations)
    audit_class = RuntimeFactAudit if isinstance(plan, RuntimeEvidencePlan) else EvidenceFactAudit
    fact_audit = audit_class.model_validate(audit_payload["audit"])
    scoring_input = build_source_scoring_input(
        plan,
        content,
        rubric,
        source_root,
        observations,
        fact_audit,
        allow_insufficient=True,
    )
    if (
        audit_payload.get("case_binding") != binding
        or audit_payload.get("observations_sha256") != fingerprint(observations)
        or audit_payload.get("scoring_input_sha256") != digest(scoring_input)
    ):
        raise ValueError("source fact audit lineage changed")
    return scoring_input, observations, fact_audit


def accept_source_score_audit(ledger, plan, content, rubric, source_root, audit):
    """Require an accepted fact lineage and complete six-dimension score audit."""
    manifest, records, state, _ = ledger.read()
    _require_source_protocol(manifest)
    waiting = state["awaiting_audit"]
    if waiting is None or waiting["stage"] != "score":
        raise ValueError("no source scorer completion awaits audit")
    scoring_input, observations, fact_audit = accepted_source_fact_material(
        ledger, waiting["item_id"], plan, content, rubric, source_root
    )
    binding = case_binding(plan, content, rubric)
    payloads = _payloads(ledger)
    finish = next(row for row in records if digest(row) == waiting["finish_sha256"])
    start = next(row for row in records if digest(row) == finish["start_sha256"])
    if payloads[digest(start)].get("case_binding") != binding or payloads[digest(start)].get(
        "scoring_input_sha256"
    ) != digest(scoring_input):
        raise ValueError("source scorer lineage differs from accepted facts")
    scores = SourceScores.model_validate(completion_json(payloads[digest(finish)]))
    score_audit = UncertaintyScoreAudit.model_validate(audit.model_dump(mode="json"))
    report = inspect_source_scores(
        plan,
        content,
        rubric,
        source_root,
        observations,
        fact_audit,
        scores,
        score_audit,
        allow_insufficient=True,
    )
    if report["status"] != "audited_development" or report["judgment"] is None:
        raise ValueError("source score audit has unresolved objections")
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
