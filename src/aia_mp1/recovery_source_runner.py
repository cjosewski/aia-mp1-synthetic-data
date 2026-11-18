"""One bounded source-ID development preflight or attempt at a time."""

from pathlib import Path

from .factcheck_stages import new_json
from .recovery_source_contract import require_source_contract
from .recovery_source_preflight import preflight_source_owned
from .recovery_source_transport import dispatch_source_next
from .tracing import digest


def run_source_next(
    ledger, packet_root, key, read_remote, read_windows, *, execute=False, transport=None
):
    """Always recheck ownership and exact-wire fit before an optional single call."""
    manifest, _, state, head = ledger.read()
    require_source_contract(manifest["experiment"])
    allocation = manifest["experiment"].get("development_allocation")
    if (
        not isinstance(allocation, dict)
        or set(allocation) != {"protocol", "max_starts", "decision_ref"}
        or allocation["protocol"] != "m4-source-development-v1"
        or type(allocation["max_starts"]) is not int
        or allocation["max_starts"] != 20
        or not isinstance(allocation["decision_ref"], str)
        or not allocation["decision_ref"].strip()
    ):
        raise ValueError("frozen bounded source-ID development allocation required")
    if state["next_request"] is None or state["starts"] >= allocation["max_starts"]:
        raise ValueError("no unused audit-released source-ID slot")
    preflight = preflight_source_owned(
        ledger, Path(packet_root), key, read_remote, read_windows, transport=transport
    )
    prepared = preflight["prepared"]
    if ledger.read()[3] != head or prepared["item_id"] != state["next_request"]["item_id"]:
        raise ValueError("source journal changed during request preparation")
    receipt = (
        ledger.directory / f"source-preflight-{state['starts']:02d}-{digest(preflight)[:12]}.json"
    )
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
    outcome = dispatch_source_next(
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
