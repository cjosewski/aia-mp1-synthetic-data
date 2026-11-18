"""One bounded, source-blind candidate-applicability diagnostic on the owned Mac."""

import argparse
import json
import platform
from copy import deepcopy
from pathlib import Path

import httpx
from v15_remote import remote

from aia_mp1.evidence_judge import completion_json
from aia_mp1.factcheck_stages import load_json, new_json
from aia_mp1.factcheck_transport import LocalServer
from aia_mp1.model_client import InstructorClient
from aia_mp1.recovery_candidate_challenge import (
    CandidateApplicabilityChallenge,
    challenge_request,
    inspect_candidate_challenge,
)
from aia_mp1.recovery_candidate_wire import prepare_challenge_wire
from aia_mp1.recovery_evidence import parse_plan
from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.recovery_packet import require_ready
from aia_mp1.recovery_preflight import _observe
from aia_mp1.recovery_process import observe_files, observe_process
from aia_mp1.recovery_source_contract import require_source_contract
from aia_mp1.recovery_source_refs import SourceObservations
from aia_mp1.recovery_tunnel import observe_tunnel, read_windows_tunnel
from aia_mp1.tracing import digest, now


def _code_hash():
    project = Path(__file__).resolve().parents[1]
    return digest(
        {
            str(path.relative_to(project)): digest(path.read_text("utf-8"))
            for path in (
                project / "src/aia_mp1/recovery_candidate_challenge.py",
                project / "src/aia_mp1/recovery_candidate_wire.py",
                project / "tools/recovery_candidate_probe.py",
            )
        }
    )


def _saved_source(source_journal, packet):
    ledger = RecoveryLedger(source_journal)
    manifest, records, state, head = ledger.read()
    require_source_contract(manifest["experiment"])
    require_ready(packet, manifest["experiment"]["packet_sha256"])
    if (
        len(records) != 3
        or [row["kind"] for row in records] != ["start", "finish", "audit"]
        or state["halt"] != "semantic_audit_rejected"
    ):
        raise ValueError("expected the preserved first rejected source-ID response")
    item = manifest["case_ids"][0]
    plan = parse_plan(load_json(packet / item / "plan.json"))
    content = load_json(packet / item / "input.json")
    envelopes = [
        json.loads(line)
        for line in (source_journal / "events.jsonl").read_text("utf-8").splitlines()
    ]
    raw = envelopes[1]["payload"]
    observations = SourceObservations.model_validate(completion_json(raw))
    body = challenge_request(plan, content, observations)
    return manifest, head, raw, plan, content, observations, body


def _challenge_experiment(source):
    experiment = deepcopy(source["experiment"])
    experiment["owned_process"]["remote_root"] = (
        "/Users/chadjosewski/AIA/MP1-handoff/MP1-CANDIDATE-CHALLENGE-20261118"
    )
    experiment["owned_tunnel"]["pid"] = 0  # observed PID supplied only at execution
    return experiment


def _prepared(root, packet, source_journal):
    source, head, raw, plan, content, observations, body = _saved_source(source_journal, packet)
    prompt = (root / "prompt.txt").read_text("utf-8")
    if not prompt.strip():
        raise ValueError("challenge prompt missing")
    policy = source["experiment"]["transport_policy"]
    request = {
        "model": policy["model"],
        "temperature": 0.1,
        "max_tokens": 8192,
        "timeout_seconds": 1200,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(body, separators=(",", ":"), ensure_ascii=False),
            },
        ],
    }
    return source, head, raw, plan, content, observations, body, request


def prepare(root, packet, source_journal):
    source, head, raw, _, _, _, body, request = _prepared(root, packet, source_journal)
    if (root / "manifest.json").exists():
        raise ValueError("challenge manifest already exists")
    receipt = prepare_challenge_wire(request)
    experiment = _challenge_experiment(source)
    manifest = {
        "protocol": "candidate-applicability-diagnostic-v1",
        "allocation": {"max_starts": 1, "case_id": source["case_ids"][0]},
        "source_journal_head": head,
        "source_raw_sha256": digest(raw),
        "source_contract_sha256": source["experiment"]["source_contract_sha256"],
        "packet_sha256": source["experiment"]["packet_sha256"],
        "challenge_body_sha256": digest(body),
        "prompt_sha256": digest(request["messages"][0]["content"]),
        "challenge_code_sha256": _code_hash(),
        "request_sha256": digest(request),
        "wire_sha256": receipt["wire_sha256"],
        "experiment": experiment,
        "calibration_eligible": False,
    }
    new_json(root / "manifest.json", manifest)
    new_json(root / "request.json", request)
    new_json(root / "wire.json", receipt)
    return {
        "status": "prepared",
        "supported_checks": len(body["supported_checks"]),
        "model_starts": 0,
    }


class _SingleTransport(httpx.BaseTransport):
    def __init__(self, expected_wire, endpoint):
        self.expected_wire = expected_wire
        self.inner = httpx.HTTPTransport(retries=0)
        self.endpoint = endpoint
        self.calls = 0

    def handle_request(self, request):
        self.calls += 1
        if (
            self.calls != 1
            or request.method != "POST"
            or str(request.url) != self.endpoint + "/chat/completions"
            or json.loads(request.content) != self.expected_wire
        ):
            raise ValueError("challenge dispatch differs from frozen single wire")
        return self.inner.handle_request(request)

    def close(self):
        self.inner.close()


def execute(root, packet, source_journal, tunnel_pid, key):
    manifest = load_json(root / "manifest.json")
    if (root / "start.json").exists() or any(
        (root / name).exists() for name in ("response.json", "failure.json")
    ):
        raise ValueError("one diagnostic start already consumed or outcome needs inspection")
    source, head, raw, plan, content, observations, body, request = _prepared(
        root, packet, source_journal
    )
    receipt = prepare_challenge_wire(request)
    if (
        manifest["protocol"] != "candidate-applicability-diagnostic-v1"
        or manifest["allocation"] != {"max_starts": 1, "case_id": source["case_ids"][0]}
        or manifest["source_journal_head"] != head
        or manifest["source_raw_sha256"] != digest(raw)
        or manifest["source_contract_sha256"] != source["experiment"]["source_contract_sha256"]
        or manifest["packet_sha256"] != source["experiment"]["packet_sha256"]
        or manifest["challenge_body_sha256"] != digest(body)
        or manifest["prompt_sha256"] != digest(request["messages"][0]["content"])
        or manifest["challenge_code_sha256"] != _code_hash()
        or manifest["request_sha256"] != digest(request)
        or manifest["wire_sha256"] != receipt["wire_sha256"]
        or manifest["experiment"] != _challenge_experiment(source)
        or load_json(root / "request.json") != request
        or load_json(root / "wire.json") != receipt
    ):
        raise ValueError("frozen challenge preparation changed")
    experiment = deepcopy(manifest["experiment"])
    if tunnel_pid <= 1 or experiment["owned_tunnel"]["pid"] != 0:
        raise ValueError("invalid dynamically observed tunnel PID")
    experiment["owned_tunnel"]["pid"] = tunnel_pid
    before_tunnel = observe_tunnel(experiment, read_windows_tunnel)
    before_process = observe_process(experiment, remote)
    files = observe_files(experiment, remote)
    endpoint = experiment["transport_policy"]["endpoint"]
    server = LocalServer(endpoint, key)
    try:
        expected = experiment["server_properties"]
        before_server = _observe(server, expected, request["model"])
        fit = server.token_fit(receipt["wire"], expected["default_generation_settings"]["n_ctx"])
        after_server = _observe(server, expected, request["model"])
    finally:
        server.close()
    for entry in files:
        observed = remote(
            "set -eu\n/usr/bin/stat -Lf '%z|%m|%i' \"$1\"\n", entry["path"], timeout=30
        ).strip()
        if observed != f"{entry['bytes']}|{entry['mtime']}|{entry['inode']}":
            raise ValueError("runtime file changed after hashing")
    after_process = observe_process(experiment, remote)
    after_tunnel = observe_tunnel(experiment, read_windows_tunnel)
    if (
        not fit["fits"]
        or before_server != after_server
        or before_process != after_process
        or before_tunnel != after_tunnel
        or (root / "start.json").exists()
    ):
        raise ValueError("challenge preflight failed or ownership changed")
    preflight = {
        "observed_at": now(),
        "owned_tunnel": before_tunnel,
        "owned_process": before_process,
        "runtime_files": files,
        "server_properties": before_server,
        "token_fit": fit,
        "request_sha256": digest(request),
        "wire_sha256": receipt["wire_sha256"],
        "model_starts": 0,
        "calibration_eligible": False,
    }
    new_json(root / "preflight.json", preflight)
    new_json(
        root / "start.json",
        {
            "started_at": now(),
            "preflight_sha256": digest(preflight),
            "request_sha256": digest(request),
            "allocation": "one-start",
        },
    )
    guard = _SingleTransport(receipt["wire"], endpoint)
    with InstructorClient(
        base_url=endpoint,
        api_key=key,
        model=request["model"],
        mode="json",
        temperature=request["temperature"],
        max_tokens=request["max_tokens"],
        timeout_seconds=request["timeout_seconds"],
        response_model=CandidateApplicabilityChallenge,
        _transport=guard,
    ) as client:
        result = client.generate(request["messages"])
    raw = result.raw_response
    if raw is not None:
        new_json(root / "response.json", {"raw": raw, "received_at": now(), "model_starts": 1})
    if guard.calls != 1 or raw is None:
        new_json(
            root / "failure.json",
            {
                "error_type": result.error_type,
                "outcome": "unknown_or_transport_failure",
                "consumed_starts": 1,
                "observed_http_calls": guard.calls,
            },
        )
        return {"status": "failure_recorded", "consumed_starts": 1}
    if not isinstance(raw, dict) or raw.get("model") != request["model"]:
        return {"status": "response_identity_failure", "model_starts": 1}
    try:
        challenge = CandidateApplicabilityChallenge.model_validate(completion_json(raw))
        report = inspect_candidate_challenge(plan, content, observations, challenge)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError):
        return {"status": "invalid_response_retained", "model_starts": 1}
    return {"status": "response_retained_for_audit", **report, "model_starts": 1}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "execute"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--source-journal", type=Path, required=True)
    parser.add_argument("--tunnel-pid", type=int)
    args = parser.parse_args()
    if platform.system() != "Linux" or "microsoft" not in platform.release().lower():
        parser.error("run this diagnostic in WSL2 Ubuntu")
    if args.root.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error("diagnostic artifacts must stay outside Git")
    if args.command == "prepare":
        result = prepare(args.root, args.packet, args.source_journal)
    else:
        if args.tunnel_pid is None:
            parser.error("--tunnel-pid is required for execute")
        result = execute(
            args.root, args.packet, args.source_journal, args.tunnel_pid, "local-only-placeholder"
        )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
