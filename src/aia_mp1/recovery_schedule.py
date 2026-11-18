"""Pure recovery schedule replay; persistence and semantic audit validation are separate.

No result of this module authorizes dispatch. Audit events must be constructed by
the recovery audit validator, never from an unauthenticated model assertion.
"""

from .tracing import digest


def replay(case_ids: list[str], events: list[dict]) -> dict:
    if (
        len(case_ids) != 10
        or len(set(case_ids)) != 10
        or any(not isinstance(x, str) or not x.strip() for x in case_ids)
    ):
        raise ValueError("recovery requires ten distinct frozen cases")
    states = {item: {"facts": "ready", "score": "waiting"} for item in case_ids}
    starts = []
    pending = None
    auditing = None
    failures = 0
    halt = None
    transport_failure = None

    def next_request():
        if pending or auditing or halt or failures >= 2 or len(starts) >= 20:
            return None
        for item, stages in states.items():
            for stage in ("facts", "score"):
                if stages[stage] == "ready":
                    return {"item_id": item, "stage": stage}
        return None

    for event in events:
        kind = event.get("kind")
        if kind == "start":
            expected = next_request()
            if (
                expected is None
                or set(event) != {"kind", "item_id", "stage", "request_sha256"}
                or any(event[k] != v for k, v in expected.items())
                or not _sha(event["request_sha256"])
            ):
                raise ValueError("start violates order, audit gate or attempt allocation")
            pending = dict(event)
            starts.append(pending)
            states[event["item_id"]][event["stage"]] = "started"
        elif kind == "finish":
            if (
                pending is None
                or transport_failure is not None
                or set(event) != {"kind", "start_sha256", "completion_sha256", "structurally_valid"}
                or event["start_sha256"] != digest(pending)
                or not _sha(event["completion_sha256"])
                or type(event["structurally_valid"]) is not bool
            ):
                raise ValueError("finish must match the sole pending start")
            item, stage = pending["item_id"], pending["stage"]
            if event["structurally_valid"]:
                states[item][stage] = "awaiting_audit"
                auditing = {"item_id": item, "stage": stage, "finish_sha256": digest(event)}
                failures = 0
            else:
                states[item][stage] = "failed"
                if stage == "facts":
                    states[item]["score"] = "skipped"
                failures += 1
            pending = None
        elif kind == "response_identity_failure":
            if (
                pending is None
                or halt is not None
                or set(event) != {"kind", "start_sha256", "completion_sha256"}
                or event["start_sha256"] != digest(pending)
                or not _sha(event["completion_sha256"])
            ):
                raise ValueError("identity failure must match the sole pending start")
            item, stage = pending["item_id"], pending["stage"]
            states[item][stage] = "failed"
            if stage == "facts":
                states[item]["score"] = "skipped"
            pending = None
            halt = "response_model_identity_failed"
        elif kind == "transport_failure":
            if (
                pending is None
                or transport_failure is not None
                or set(event) != {"kind", "start_sha256", "failure_sha256"}
                or event["start_sha256"] != digest(pending)
                or not _sha(event["failure_sha256"])
            ):
                raise ValueError("transport failure must match the sole pending start")
            transport_failure = dict(event)
            halt = "transport_outcome_unknown"
        elif kind == "audit":
            if (
                auditing is None
                or set(event) != {"kind", "finish_sha256", "audit_sha256", "accepted"}
                or event["finish_sha256"] != auditing["finish_sha256"]
                or not _sha(event["audit_sha256"])
                or type(event["accepted"]) is not bool
            ):
                raise ValueError("audit must bind the waiting completion")
            item, stage = auditing["item_id"], auditing["stage"]
            states[item][stage] = "accepted" if event["accepted"] else "rejected"
            if not event["accepted"]:
                halt = "semantic_audit_rejected"
            elif stage == "facts":
                states[item]["score"] = "ready"
            auditing = None
        else:
            raise ValueError("unknown recovery schedule event")
    return {
        "cases": states,
        "starts": len(starts),
        "pending": pending,
        "awaiting_audit": auditing,
        "halt": halt or ("two_structural_failures" if failures >= 2 else None),
        "next_request": next_request(),
        "unknown_outcome": pending is not None,
        "transport_failure": transport_failure,
        "coverage_denominator": len(case_ids),
        "execution_enabled": False,
        "calibration_eligible": False,
    }


def _sha(value):
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )
