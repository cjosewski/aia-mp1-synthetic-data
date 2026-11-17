"""Approved paired prompt screen on exposed confirmation cases, never calibration."""

import argparse
import copy
import json
import subprocess
from pathlib import Path

from v15_remote import ENDPOINT, REMOTE_ROOT, owned
from v15_remote import preflight as remote_preflight

from aia_mp1.assessment import read_json, read_text
from aia_mp1.canonical_development import save
from aia_mp1.confirmation_review import byte_hash, load_review
from aia_mp1.confirmation_transport import (
    RECOVERY_FILE,
    audit,
    client_for,
    initialize,
    load_plan,
    run_phase,
)
from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.factcheck_transport import VerifiedTransport
from aia_mp1.judge import messages_for
from aia_mp1.tracing import digest

SOURCE_SHA = "cf87d3e07c2f4424e3994e232d45d9398431b2a809ddfd5476ff0dbbeb4f90e7"
DRAFT_SHA = "0ff6b3170ff6a412d5c7846dc936e5ff699820c1f212d5592419eba2abe8b28d"
ARMS = ("v13", "v15")


def derive_plan(source, packet, draft):
    if (
        source["sha256"] != SOURCE_SHA
        or digest({k: v for k, v in source.items() if k != "sha256"}) != SOURCE_SHA
    ):
        raise ValueError("source confirmation identity differs")
    if byte_hash(draft) != DRAFT_SHA:
        raise ValueError("approved draft prompt differs")
    records = [json.loads(line) for line in read_text(packet / "data.jsonl").splitlines()]
    rubric = read_json(packet / "rubric.json")
    cases = []
    for original, record in zip(source["cases"], records, strict=True):
        if original["item_id"] != record["item_id"]:
            raise ValueError("source case order differs")
        for arm in ARMS:
            case = copy.deepcopy(original)
            case.update(
                item_id=f"{original['item_id']}:{arm}",
                original_item_id=original["item_id"],
                arm=arm,
            )
            if arm == "v15":
                case["messages"] = messages_for(read_text(draft), rubric, record)
            if case["messages"][1] != original["messages"][1]:
                raise ValueError("paired user input differs")
            cases.append(case)
    plan = {
        "protocol": "qwen35-v13-v15-budget4096-development-v1",
        "purpose": "Known development cases; not fresh confirmation or assessed calibration",
        "source_plan_sha256": SOURCE_SHA,
        "human_reference_sha256": source["human_reference_sha256"],
        "draft_byte_sha256": DRAFT_SHA,
        "settings": source["settings"],
        "runtime": source["runtime"] | {"reasoning_budget": 4096},
        "models": [source["models"][0]],
        "cases": cases,
        "max_starts": 40,
        "prior_starts": 298,
        "execution": {"client": "WSL2 Ubuntu", "server": "native Mac", "remote_root": REMOTE_ROOT},
    }
    plan["sha256"] = digest(plan)
    return plan


def verify(root):
    manifest = read_json(root / "bundle-manifest.json")
    required = {
        "plan.json",
        "source-plan.json",
        "owner-approval.json",
        "run-on-mac.sh",
        "packet/manifest.json",
        "review/human-reference.json",
        "review/submitted-answers.md",
        "project/uv.lock",
        "project/pyproject.toml",
        "project/prompts/judge-v15-task-contract.md",
    }
    required.update(
        f"project/src/aia_mp1/{p.name}" for p in (root / "project/src/aia_mp1").glob("*.py")
    )
    required.update(
        {
            "project/tools/v15_comparison.py",
            "project/tools/run_v15_comparison_on_mac.sh",
            "project/tools/v15_remote.py",
        }
    )
    if not required <= manifest["files_sha256"].keys():
        raise ValueError("bundle omits required files")
    for name, sha in manifest["files_sha256"].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or byte_hash(path) != sha:
            raise ValueError(f"unsafe or changed frozen file: {name}")
    source = load_plan(root / "source-plan.json", root / "packet", root / "review")
    plan = derive_plan(source, root / "packet", root / "project/prompts/judge-v15-task-contract.md")
    if read_json(root / "plan.json") != plan or manifest["plan_sha256"] != plan["sha256"]:
        raise ValueError("paired plan differs from frozen proposal")
    approval = read_json(root / "owner-approval.json")
    if (
        approval.get("plan_sha256") != plan["sha256"]
        or approval.get("approved_by") != "Chad Josewski"
        or approval.get("source") != "user_message"
        or approval.get("owner_statement")
        != "The orign 80% in every dimension. Let's try to get it there."
        or not approval.get("recorded_at")
    ):
        raise ValueError("owner approval does not cover this plan")
    if (root / "results" / RECOVERY_FILE).exists():
        raise ValueError("this allocation permits no recovery amendment or extra attempts")
    return plan


def report(plan, state, reference):
    if reference["sha256"] != plan["human_reference_sha256"]:
        raise ValueError("reporting human reference differs")
    labels = {r["item_id"]: r["decisions"] for r in reference["labels"]}
    successful = state["successful"]["candidate"]
    arms, mistakes = {}, {}
    for arm in ARMS:
        cases = [c for c in plan["cases"] if c["arm"] == arm]
        judgments = {
            c["original_item_id"]: successful[c["item_id"]]
            for c in cases
            if c["item_id"] in successful
        }
        attempts = [a for a in state["attempts"] if a["start"]["item_id"].endswith(":" + arm)]
        dimensions = {}
        for d in DIMENSIONS:
            false_approvals = [
                i for i, j in judgments.items() if labels[i][d] == 0 and j[d]["decision"] == 1
            ]
            mistakes[arm, d] = set(false_approvals)
            dimensions[d] = {
                "matching": sum(j[d]["decision"] == labels[i][d] for i, j in judgments.items()),
                "compared": len(judgments),
                "selected": len(cases),
                "false_approvals": false_approvals,
                "false_rejections": [
                    i for i, j in judgments.items() if labels[i][d] == 1 and j[d]["decision"] == 0
                ],
            }
        arms[arm] = {
            "starts": len(attempts),
            "initial_started": sum(a["start"]["number"] == 1 for a in attempts),
            "initial_valid": sum(
                a["start"]["number"] == 1 and a["result"]["judgment"] is not None for a in attempts
            ),
            "valid_cases": len(judgments),
            "unresolved": len(cases) - len(judgments),
            "dimensions": dimensions,
            "matching": sum(v["matching"] for v in dimensions.values()),
            "seconds": sum(a["result"]["seconds"] for a in attempts),
        }
    paired = []
    for case in plan["cases"][::2]:
        i = case["original_item_id"]
        if all(f"{i}:{arm}" in successful for arm in ARMS):
            for d in DIMENSIONS:
                old, new = (successful[f"{i}:{arm}"][d]["decision"] for arm in ARMS)
                if old != new:
                    paired.append(
                        {
                            "item_id": i,
                            "dimension": d,
                            "human": labels[i][d],
                            "v13": old,
                            "v15": new,
                            "improved": new == labels[i][d],
                        }
                    )
    new_unsafe = {d: sorted(mistakes["v15", d] - mistakes["v13", d]) for d in ("D2", "D3")}
    numerical = (
        all(a["valid_cases"] == 10 for a in arms.values())
        and all(v["matching"] >= 8 for v in arms["v15"]["dimensions"].values())
        and arms["v15"]["matching"] > arms["v13"]["matching"]
        and not any(new_unsafe.values())
    )
    return {
        "plan_sha256": plan["sha256"],
        "purpose": plan["purpose"],
        "human_reference_sha256": reference["sha256"],
        "starts": len(state["attempts"]),
        "arms": arms,
        "paired_changes": paired,
        "new_safety_api_false_approvals": new_unsafe,
        "numerical_advancement_conditions_met": numerical,
        "semantic_audit_required": True,
        "automatic_follow_on_run": False,
        "assessed_calibration": False,
    }


def execute(root, plan):
    directory = root / "results"
    initialize(plan, directory)
    model = plan["models"][0]
    endpoint = ENDPOINT

    def check_owned():
        return owned(model["model"])

    def preflight():
        save(directory / "owned-launch.json", check_owned())
        remote_preflight(plan, directory)

    def dispatch(model, case, wire):
        transport = VerifiedTransport(wire)
        with client_for(plan, model, endpoint, transport) as client:
            result = client.generate(case["messages"])
        if transport.calls != 1:
            raise ValueError("unverified dispatch; retain unknown start")
        return result.raw_response, result.error

    state = run_phase(
        plan, "candidate", directory, dispatch, verify_before=preflight, before_attempt=check_owned
    )
    source = read_json(root / "source-plan.json")
    reference = load_review(root / "packet", source["packet_manifest_sha256"], root / "review")
    result = report(plan, state, reference)
    save(directory / "report.json", result)
    print(json.dumps(result, indent=2))
    return 0 if len(state["successful"]["candidate"]) == 20 else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "execute", "report"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        plan = verify(args.root)
        if args.action == "verify":
            print(json.dumps({"verified": True, "plan_sha256": plan["sha256"]}))
            return 0
        if args.action == "report":
            source = read_json(args.root / "source-plan.json")
            reference = load_review(
                args.root / "packet", source["packet_manifest_sha256"], args.root / "review"
            )
            print(json.dumps(report(plan, audit(plan, args.root / "results"), reference), indent=2))
            return 0
        return execute(args.root, plan)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"V15 comparison stopped: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
