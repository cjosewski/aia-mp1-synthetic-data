"""Synthetic source-ID observations; no real-item ratings or accepting audits."""

from copy import deepcopy

import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_evidence import evidence as evidence

from aia_mp1.recovery_evidence import EvidencePlan
from aia_mp1.recovery_source_refs import (
    SourceObservations,
    inspect_source_observations,
    source_request,
)
from aia_mp1.tracing import digest


def response_for(plan):
    return {
        "protocol": "recovery-source-refs-v1",
        "plan_sha256": digest(plan),
        "observations": [
            {
                "check_id": check["check_id"],
                "status": "supported",
                "sources": [deepcopy(check["sources"][0])],
                "explanation": "Synthetic claim; semantic truth remains unaudited.",
            }
            for check in plan["checks"]
        ],
    }


def inspect(evidence, response):
    plan, content, rubric, root = evidence
    return inspect_source_observations(
        EvidencePlan.model_validate(plan),
        content,
        rubric,
        root,
        SourceObservations.model_validate(response),
    )


def test_source_ids_do_not_claim_truth_or_calibration(evidence):
    plan, content, rubric, root = evidence
    request = source_request(EvidencePlan.model_validate(plan), content, rubric, root)
    assert request["observation_protocol"] == "recovery-source-refs-v1"
    assert request["checks"][0]["sources"] == plan["checks"][0]["sources"]
    report = inspect(evidence, response_for(plan))
    assert report["checks"] == len(plan["checks"])
    assert report["semantic_audit"] == "required"
    assert report["calibration_eligible"] is False


@pytest.mark.parametrize(
    "change",
    ["foreign", "version", "duplicate", "empty", "missing", "reorder", "stale_plan"],
)
def test_source_identity_and_coverage_attacks_fail(evidence, change):
    plan = evidence[0]
    response = response_for(plan)
    first = response["observations"][0]
    if change == "foreign":
        first["sources"][0]["passage_id"] = "R.unbound"
    elif change == "version":
        first["sources"][0]["version"] = "wrong-version"
    elif change == "duplicate":
        first["sources"].append(deepcopy(first["sources"][0]))
    elif change == "empty":
        first["sources"] = []
    elif change == "missing":
        response["observations"].pop()
    elif change == "reorder":
        response["observations"][0], response["observations"][1] = (
            response["observations"][1],
            response["observations"][0],
        )
    else:
        response["plan_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        inspect(evidence, response)


def test_insufficient_finding_remains_unresolved(evidence):
    response = response_for(evidence[0])
    response["observations"][0]["status"] = "insufficient"
    response["observations"][0]["sources"] = []
    report = inspect(evidence, response)
    assert report["unresolved"] == ["K0001"]
    assert report["calibration_eligible"] is False
