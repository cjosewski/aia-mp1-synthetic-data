"""Read-only source-ID token, owner and immutable-file preflight."""

from pathlib import Path

from .factcheck_transport import PROPERTIES, LocalServer
from .recovery_preflight import _observe
from .recovery_process import observe_files, observe_process
from .recovery_source_contract import require_source_contract
from .recovery_source_requests import prepare_source_next
from .recovery_tunnel import observe_tunnel
from .tracing import digest, now


def preflight_source_next(ledger, packet_root, key, *, transport=None):
    """Regenerate exact wire and check the fixed server before any start event."""
    manifest, _, _, head = ledger.read()
    expected = manifest["experiment"].get("server_properties")
    if not isinstance(expected, dict) or set(expected) != {*PROPERTIES, "model_path"}:
        raise ValueError("frozen server build, template, settings, slots and model required")
    settings = expected["default_generation_settings"]
    context = settings.get("n_ctx") if isinstance(settings, dict) else None
    if (
        type(context) is not int
        or context <= 0
        or type(expected["total_slots"]) is not int
        or expected["total_slots"] != 1
        or not isinstance(expected["chat_template"], str)
        or not expected["chat_template"].strip()
        or not expected["build_info"]
    ):
        raise ValueError("frozen runtime needs context, one slot, template and build")
    prepared = prepare_source_next(ledger, Path(packet_root))
    model = prepared["request"]["model"]
    if expected["model_path"] != model:
        raise ValueError("frozen runtime model differs from request")
    server = LocalServer(prepared["endpoint"], key, transport)
    try:
        before = _observe(server, expected, model)
        fit = server.token_fit(prepared["receipt"]["wire"], context)
        after = _observe(server, expected, model)
        if before != after or ledger.read()[3] != head:
            raise ValueError("server or journal changed during token preflight")
    finally:
        server.close()
    return {
        "prepared": prepared,
        "observed_at": now(),
        "journal_head_sha256": head,
        "server_properties": before,
        "server_properties_sha256": digest(before),
        "token_fit": fit,
        "inference_started": False,
        "execution_enabled": False,
        "calibration_eligible": False,
    }


def preflight_source_owned(ledger, packet_root, key, read_remote, read_windows, *, transport=None):
    """Bracket HTTP checks with the owned SSH tunnel and native Mac process."""
    manifest, _, _, head = ledger.read()
    experiment = manifest["experiment"]
    require_source_contract(experiment)
    tunnel_before = observe_tunnel(experiment, read_windows)
    process_before = observe_process(experiment, read_remote)
    files = observe_files(experiment, read_remote)
    result = preflight_source_next(ledger, packet_root, key, transport=transport)
    for entry in files:
        observed = read_remote(
            "set -eu\n/usr/bin/stat -Lf '%z|%m|%i' \"$1\"\n",
            entry["path"],
            timeout=30,
        ).strip()
        if observed != f"{entry['bytes']}|{entry['mtime']}|{entry['inode']}":
            raise ValueError("runtime file changed after hashing")
    process_after = observe_process(experiment, read_remote)
    tunnel_after = observe_tunnel(experiment, read_windows)
    if (
        tunnel_before != tunnel_after
        or process_before != process_after
        or ledger.read()[3] != head
        or result["journal_head_sha256"] != head
    ):
        raise ValueError("owned process, tunnel or journal changed across preflight")
    return {
        **result,
        "owned_tunnel": tunnel_before,
        "owned_process": process_before,
        "runtime_files": files,
    }
