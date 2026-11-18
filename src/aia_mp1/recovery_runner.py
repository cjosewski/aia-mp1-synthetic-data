"""Bounded recovery request orchestration; source and audit gates stay mandatory."""

from pathlib import Path

from .factcheck_stages import new_json
from .recovery_transport import dispatch_next
from .recovery_tunnel import preflight_with_tunnel
from .tracing import digest


def run_next(ledger, packet_root, key, read_remote, read_windows, *, execute=False, transport=None):
    """Preflight one unused slot, then optionally dispatch one audited attempt.

    No retries, automatic audit, loop over cases, or assessed calibration are
    hidden here. A failed/unknown started request is never automatically reused.
    """
    manifest, _, state, head = ledger.read()
    allocation = manifest["experiment"].get("development_allocation")
    if (
        not isinstance(allocation, dict)
        or set(allocation) != {"protocol", "max_starts", "decision_ref"}
        or allocation["protocol"] != "m4-recovery-development-v1"
        or type(allocation["max_starts"]) is not int
        or allocation["max_starts"] != 20
        or not isinstance(allocation["decision_ref"], str)
        or not allocation["decision_ref"].strip()
    ):
        raise ValueError("frozen bounded development allocation is required")
    if state["next_request"] is None or state["starts"] >= allocation["max_starts"]:
        raise ValueError("no unused, audit-released development slot")
    preflight = preflight_with_tunnel(
        ledger, Path(packet_root), key, read_remote, read_windows, transport=transport
    )
    prepared = preflight["prepared"]
    if ledger.read()[3] != head or prepared["item_id"] != state["next_request"]["item_id"]:
        raise ValueError("journal changed during request preparation")
    receipt = (
        ledger.directory
        / f"preflight-{state['starts']:02d}-{digest(prepared['receipt'])[:12]}.json"
    )
    # Never overwrite a prior receipt, including one left by an interrupted run.
    new_json(receipt, preflight)
    if not preflight["token_fit"]["fits"]:
        return {
            "outcome": "token_fit_failed",
            "receipt": str(receipt),
            "starts": state["starts"],
            "calibration_eligible": False,
        }
    if not execute:
        return {
            "outcome": "preflight_only",
            "receipt": str(receipt),
            "starts": state["starts"],
            "calibration_eligible": False,
        }
    # A second owner/health check is needed if operators leave time between
    # this function's preflight and dispatch; this function has no such handoff.
    outcome = dispatch_next(
        ledger,
        prepared["item_id"],
        prepared["stage"],
        prepared["request"],
        prepared["receipt"],
        prepared["binding"],
        prepared["endpoint"],
        key,
        transport=transport,
    )
    return {**outcome, "preflight_receipt": str(receipt)}
