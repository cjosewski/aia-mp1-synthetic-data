"""Durable recovery schedule journal, without live dispatch or semantic approval."""

import json
from pathlib import Path

from .assessment import exclusive
from .evidence_judge import _unique_keys
from .factcheck_stages import load_json, new_json
from .recovery_schedule import replay
from .tracing import append_record, digest, now, write_checkpoint


def contract_hash():
    root = Path(__file__).parent
    code = {
        name: digest((root / name).read_text("utf-8"))
        for name in (
            "recovery_ledger.py",
            "recovery_schedule.py",
            "recovery_transport.py",
            "recovery_packet.py",
            "recovery_requests.py",
            "recovery_preflight.py",
            "recovery_process.py",
            "recovery_tunnel.py",
            "recovery_wire.py",
            "model_client.py",
            "factcheck_transport.py",
            "recovery_audit_bridge.py",
            "recovery_checks.py",
            "recovery_evidence.py",
            "recovery_runtime.py",
            "recovery_scoring.py",
            "factcheck.py",
            "tracing.py",
            "assessment.py",
            "factcheck_stages.py",
            "evidence_judge.py",
        )
    }
    project = root.parents[1]
    for name in ("tools/recovery_windows_tunnel.ps1", "uv.lock", "pyproject.toml"):
        code[name] = digest((project / name).read_text("utf-8"))
    return digest(code)


class RecoveryLedger:
    """Append and checkpoint under one writer; interrupted tails require inspection.

    Payload hashes establish identity, not truth. The future runner must generate
    completion/audit statuses using the recovery validators before appending.
    """

    def __init__(self, directory: Path):
        if any(p.is_symlink() for p in (directory, *directory.parents)):
            raise ValueError("symlink ledger paths are not supported")
        self.directory = directory.resolve()
        if self.directory.is_relative_to(Path(__file__).resolve().parents[2]):
            raise ValueError("recovery evidence must stay outside Git")

    @classmethod
    def create(cls, directory: Path, case_ids: list[str], experiment: dict):
        replay(case_ids, [])
        if not isinstance(experiment, dict) or not experiment:
            raise ValueError("frozen experiment identity is required")
        ledger = cls(directory)
        ledger.directory.mkdir(parents=True, exist_ok=False)
        manifest = {
            "protocol": "recovery-journal-v1",
            "case_ids": case_ids,
            "experiment": experiment,
            "contract_sha256": contract_hash(),
        }
        new_json(ledger.directory / "manifest.json", manifest)
        new_json(ledger.directory / "head.json", {"count": 0, "sha256": digest(manifest)})
        return ledger

    @staticmethod
    def check_payload(record, payload):
        field = {
            "start": "request_sha256",
            "finish": "completion_sha256",
            "audit": "audit_sha256",
            "transport_failure": "failure_sha256",
            "response_identity_failure": "completion_sha256",
        }.get(record.get("kind"))
        if field is None or record.get(field) != digest(payload):
            raise ValueError("event does not match its retained payload")

    def read(self):
        manifest = load_json(self.directory / "manifest.json")
        if (
            set(manifest) != {"protocol", "case_ids", "experiment", "contract_sha256"}
            or manifest["protocol"] != "recovery-journal-v1"
            or manifest["contract_sha256"] != contract_hash()
        ):
            raise ValueError("recovery manifest or implementation changed")
        head = digest(manifest)
        records = []
        path = self.directory / "events.jsonl"
        if path.is_symlink():
            raise ValueError("symlink event journal is not supported")
        if path.exists():
            text = path.read_text("utf-8")
            if text and not text.endswith("\n"):
                raise ValueError("incomplete event tail; preserve and inspect")
            for line in text.splitlines():
                envelope = json.loads(line, object_pairs_hook=_unique_keys)
                if set(envelope) != {"previous", "timestamp", "record", "payload", "sha256"}:
                    raise ValueError("unexpected journal envelope")
                unsigned = {k: envelope[k] for k in ("previous", "timestamp", "record", "payload")}
                if envelope["previous"] != head or envelope["sha256"] != digest(unsigned):
                    raise ValueError("journal chain changed")
                if not isinstance(envelope["timestamp"], str) or not envelope["timestamp"].strip():
                    raise ValueError("journal timestamp is missing")
                self.check_payload(envelope["record"], envelope["payload"])
                records.append(envelope["record"])
                head = envelope["sha256"]
        state = replay(manifest["case_ids"], records)
        if load_json(self.directory / "head.json") != {"count": len(records), "sha256": head}:
            raise ValueError("event/head mismatch; preserve and inspect")
        return manifest, records, state, head

    def append(self, record: dict, payload: dict | str):
        """Persist a validated scheduling event and its complete redacted artifact."""
        with exclusive(self.directory):
            manifest, records, _, head = self.read()
            self.check_payload(record, payload)
            state = replay(manifest["case_ids"], records + [record])
            envelope = {"previous": head, "timestamp": now(), "record": record, "payload": payload}
            envelope["sha256"] = digest(envelope)
            append_record(self.directory / "events.jsonl", envelope)
            write_checkpoint(
                self.directory / "head.json",
                {"count": len(records) + 1, "sha256": envelope["sha256"]},
            )
            return state
