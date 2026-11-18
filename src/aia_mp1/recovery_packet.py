"""Read-only preparation gate; readiness is not semantic truth or authorization."""

import re
from collections import Counter

from .factcheck import source_file
from .factcheck_stages import load_json
from .recovery_audit_bridge import case_binding
from .recovery_evidence import EvidencePlan, evidence_request, inspect_evidence, parse_plan
from .schemas import CATEGORIES
from .tracing import digest


def inspect_packet(root):
    """Rebuild each draft from verified sources and inspect every preparation entry.

    No files are written, no human ratings are read, and no accepting fact audit
    is manufactured. A structurally valid packet with holds remains not ready.
    """

    def read(relative):
        return load_json(source_file(root, relative))

    selection = read("selection.json")
    rubric = read("rubric.json")
    cases = selection.get("cases", [])
    protocol = selection.get("protocol")
    if protocol not in {"recovery-preparation-v1", "recovery-preparation-v2"} or len(cases) != 10:
        raise ValueError("expected ten frozen recovery preparation cases")
    ids = [case["item_id"] for case in cases]
    if len(set(ids)) != 10 or any(
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", item) for item in ids
    ):
        raise ValueError("case IDs must be distinct safe directory names")
    if Counter(case["category"] for case in cases) != Counter(
        {category: 2 for category in CATEGORIES}
    ):
        raise ValueError("recovery requires exactly two cases per category")
    bindings, holds, gaps, insufficient, snapshots = {}, [], [], [], []
    total = 0
    for item in ids:
        content = read(f"{item}/input.json")
        plan = parse_plan(read(f"{item}/plan.json"))
        if not isinstance(plan, EvidencePlan):
            raise ValueError("prepared packet requires evidence v2 or v3")
        report = inspect_evidence(plan, content, rubric, root / "sources")
        if report != read(f"{item}/structural-report.json"):
            raise ValueError("saved structural report differs from source replay")
        request = evidence_request(plan, content, rubric, root / "sources")
        if request != read(f"{item}/verifier-input-draft.json"):
            raise ValueError("draft request differs from verified evidence")
        review = read(f"{item}/preparation-review.json")
        if review.get("item_id") != item or review.get("plan_sha256") != report["plan_sha256"]:
            raise ValueError("preparation review belongs to different inputs")
        if review.get("origin") != "assistant_preparation_review":
            raise ValueError("unexpected preparation review origin")
        for field in ("reviewer", "reviewed_at"):
            if not isinstance(review.get(field), str) or not review[field].strip():
                raise ValueError("preparation review attribution is required")
        entries = review["entries"]
        if [entry["check_id"] for entry in entries] != [check.check_id for check in plan.checks]:
            raise ValueError("preparation review must cover every ordered check exactly once")
        item_holds = []
        item_insufficient = []
        for entry, check in zip(entries, plan.checks, strict=True):
            statuses = {"prepared_for_verifier", "hold"}
            if protocol == "recovery-preparation-v2":
                statuses.add("prepared_insufficient")
            if (
                entry.get("parent_check_id") != check.parent_check_id
                or entry.get("status") not in statuses
                or entry.get("fact_verdict") is not None
                or entry.get("fact_audit_accepted") is not False
                or not isinstance(entry.get("reason"), str)
                or not entry["reason"].strip()
            ):
                raise ValueError("invalid preparation entry or fabricated fact acceptance")
            if entry["status"] == "hold":
                item_holds.append(check.check_id)
                holds.append(
                    {"item_id": item, "check_id": check.check_id, "reason": entry["reason"]}
                )
            if entry["status"] == "prepared_insufficient":
                if check.kind != "technical_claim" or not check.sources:
                    raise ValueError("insufficient preparation needs a bound technical claim")
                item_insufficient.append(check.check_id)
                insufficient.append(
                    {"item_id": item, "check_id": check.check_id, "reason": entry["reason"]}
                )
        if review.get("source_or_question_holds") != item_holds:
            raise ValueError("summary hides or invents preparation holds")
        if (
            protocol == "recovery-preparation-v2"
            and review.get("insufficient_claims") != item_insufficient
        ):
            raise ValueError("summary hides or invents insufficient claims")
        gaps.extend({"item_id": item, "check_id": check} for check in report["source_gaps"])
        bindings[item] = case_binding(plan, content, rubric)
        snapshots.append({"binding": bindings[item], "review": review})
        total += len(plan.checks)
    return {
        "protocol": protocol,
        "packet_sha256": digest({"selection": selection, "rubric": rubric, "cases": snapshots}),
        "case_bindings": bindings,
        "cases": len(cases),
        "checks": total,
        "holds": holds,
        "insufficient_claims": insufficient,
        "source_gaps": gaps,
        "preparation_ready": not holds and not gaps,
        "semantic_audits_required": True,
        "execution_enabled": False,
        "calibration_eligible": False,
    }


def require_ready(root, expected_sha256=None):
    report = inspect_packet(root)
    if expected_sha256 is not None and report["packet_sha256"] != expected_sha256:
        raise ValueError("preparation differs from frozen packet")
    if not report["preparation_ready"]:
        raise ValueError("unresolved preparation holds or source gaps prevent execution")
    return report
