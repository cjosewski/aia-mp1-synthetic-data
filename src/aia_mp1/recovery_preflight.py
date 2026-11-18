"""Read-only live capacity checks; never allocate or dispatch an inference."""

from .factcheck_transport import PROPERTIES, LocalServer
from .recovery_requests import prepare_next
from .tracing import digest, now


def _observe(server, expected, model):
    props = server.json("/props")
    models = server.json("/v1/models").get("data")
    health = server.json("/health")
    if (
        health.get("status") != "ok"
        or not isinstance(models, list)
        or len(models) != 1
        or models[0].get("id") != model
        or props.get("model_path") != model
        or any(props.get(key) != expected[key] for key in expected)
    ):
        raise ValueError("live model or server properties differ from frozen runtime")
    return {key: props[key] for key in expected}


def preflight_next(ledger, packet_root, key, *, transport=None):
    """Rebuild the next exact request and check it against a healthy fixed server.

    This does not verify remote process ownership or weight files and is not an
    execution permit. The eventual runner must persist this evidence and connect
    those checks at the dispatch boundary; old preflight results cannot be reused.
    """
    manifest, _, _, head = ledger.read()
    expected = manifest["experiment"].get("server_properties")
    fields = {*PROPERTIES, "model_path"}
    if not isinstance(expected, dict) or set(expected) != fields:
        raise ValueError("frozen build, template, settings, slots and model path are required")
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
        raise ValueError("frozen runtime requires positive context, one slot and a template/build")
    prepared = prepare_next(ledger, packet_root)
    model = prepared["request"]["model"]
    if expected["model_path"] != model:
        raise ValueError("frozen runtime model differs from request")
    server = LocalServer(prepared["endpoint"], key, transport)
    try:
        before = _observe(server, expected, model)
        fit = server.token_fit(prepared["receipt"]["wire"], context)
        after = _observe(server, expected, model)
        if before != after or ledger.read()[3] != head:
            raise ValueError("runtime or journal changed during token preflight")
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
