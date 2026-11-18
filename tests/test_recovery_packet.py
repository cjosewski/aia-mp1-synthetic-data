"""Synthetic preparation manifests; these are not real technical reviews."""

import json
import shutil

import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_evidence import evidence as evidence

from aia_mp1.recovery_evidence import evidence_request, inspect_evidence, parse_plan
from aia_mp1.recovery_packet import inspect_packet, require_ready
from aia_mp1.schemas import CATEGORIES
from aia_mp1.tracing import digest


def save(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def prepared(evidence, tmp_path):
    plan, content, rubric, sources = evidence
    root = tmp_path / "prepared"
    root.mkdir()
    shutil.copytree(sources, root / "sources")
    cases = [
        {"item_id": f"synthetic-{i}", "category": category}
        for i, category in enumerate(list(CATEGORIES) * 2)
    ]
    save(root / "selection.json", {"protocol": "recovery-preparation-v1", "cases": cases})
    save(root / "rubric.json", rubric)
    parsed = parse_plan(plan)
    for case in cases:
        folder = root / case["item_id"]
        folder.mkdir()
        for name, value in {
            "plan": plan,
            "input": content,
            "structural-report": inspect_evidence(parsed, content, rubric, root / "sources"),
            "verifier-input-draft": evidence_request(parsed, content, rubric, root / "sources"),
            "preparation-review": {
                "item_id": case["item_id"],
                "plan_sha256": digest(plan),
                "reviewer": "Synthetic reviewer",
                "origin": "assistant_preparation_review",
                "reviewed_at": "test-only",
                "source_or_question_holds": [],
                "entries": [
                    {
                        "check_id": c["check_id"],
                        "parent_check_id": c["parent_check_id"],
                        "status": "prepared_for_verifier",
                        "reason": "Synthetic preparation only",
                        "fact_verdict": None,
                        "fact_audit_accepted": False,
                    }
                    for c in plan["checks"]
                ],
            },
        }.items():
            save(folder / f"{name}.json", value)
    return root


def test_ready_packet_is_not_authorized_or_calibrated(prepared):
    report = require_ready(prepared)
    assert report["cases"] == 10 and report["preparation_ready"]
    assert report["semantic_audits_required"]
    assert not report["execution_enabled"] and not report["calibration_eligible"]
    with pytest.raises(ValueError, match="frozen"):
        require_ready(prepared, "a" * 64)


def test_explicit_hold_blocks_readiness(prepared):
    path = prepared / "synthetic-0/preparation-review.json"
    review = json.loads(path.read_text())
    review["entries"][0]["status"] = "hold"
    review["source_or_question_holds"] = [review["entries"][0]["check_id"]]
    save(path, review)
    assert len(inspect_packet(prepared)["holds"]) == 1
    with pytest.raises(ValueError, match="holds"):
        require_ready(prepared)


def test_versioned_insufficient_claim_stays_visible_without_fact_verdict(prepared):
    selection_path = prepared / "selection.json"
    selection = json.loads(selection_path.read_text())
    selection["protocol"] = "recovery-preparation-v2"
    save(selection_path, selection)
    for i in range(10):
        path = prepared / f"synthetic-{i}/preparation-review.json"
        review = json.loads(path.read_text())
        review["insufficient_claims"] = []
        if i == 0:
            plan = json.loads((prepared / "synthetic-0/plan.json").read_text())
            index = next(
                j
                for j, c in enumerate(plan["checks"])
                if c["kind"] == "technical_claim" and c["sources"]
            )
            entry = review["entries"][index]
            entry["status"] = "prepared_insufficient"
            entry["reason"] = "Synthetic evidence does not establish the asserted behavior"
            review["insufficient_claims"] = [entry["check_id"]]
        save(path, review)
    report = require_ready(prepared)
    assert report["holds"] == [] and len(report["insufficient_claims"]) == 1
    assert not report["calibration_eligible"]
    path = prepared / "synthetic-0/preparation-review.json"
    review = json.loads(path.read_text())
    review["insufficient_claims"] = ["K9999"]
    save(path, review)
    with pytest.raises(ValueError, match="insufficient"):
        require_ready(prepared)


@pytest.mark.parametrize(
    "attack",
    ["hidden_hold", "omitted_check", "fact_acceptance", "draft", "source", "category", "path"],
)
def test_tampered_or_incomplete_packet_rejected(prepared, attack):
    path = prepared / "synthetic-0/preparation-review.json"
    review = json.loads(path.read_text())
    if attack == "hidden_hold":
        review["entries"][0]["status"] = "hold"
    elif attack == "omitted_check":
        review["entries"].pop()
    elif attack == "fact_acceptance":
        review["entries"][0]["fact_audit_accepted"] = True
    elif attack == "draft":
        save(prepared / "synthetic-0/verifier-input-draft.json", {})
    elif attack == "source":
        (prepared / "sources/permission.txt").write_text("Changed permission")
    else:
        selection_path = prepared / "selection.json"
        selection = json.loads(selection_path.read_text())
        if attack == "category":
            selection["cases"][0]["category"] = "simulation"
        else:
            selection["cases"][0]["item_id"] = "../outside"
        save(selection_path, selection)
    save(path, review)
    with pytest.raises(ValueError):
        inspect_packet(prepared)
