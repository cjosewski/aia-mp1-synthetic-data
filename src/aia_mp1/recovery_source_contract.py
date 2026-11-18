"""Versioned source-ID implementation identity layered over the v1 journal."""

from pathlib import Path

from .recovery_ledger import contract_hash
from .tracing import digest

SOURCE_MODULES = (
    "recovery_source_refs.py",
    "recovery_source_scoring.py",
    "recovery_source_wire.py",
    "recovery_source_audit.py",
    "recovery_source_requests.py",
    "recovery_source_preflight.py",
    "recovery_source_transport.py",
    "recovery_source_runner.py",
    "recovery_source_contract.py",
)


def source_contract_hash() -> str:
    root = Path(__file__).parent
    code = {name: digest((root / name).read_text("utf-8")) for name in SOURCE_MODULES}
    cli = root.parents[1] / "tools/recovery_source_next.py"
    code["tools/recovery_source_next.py"] = digest(cli.read_text("utf-8"))
    return digest(
        {"protocol": "recovery-source-contract-v1", "base": contract_hash(), "code": code}
    )


def require_source_contract(experiment: dict) -> None:
    if experiment.get("source_contract_sha256") != source_contract_hash():
        raise ValueError("frozen source-ID implementation differs")
