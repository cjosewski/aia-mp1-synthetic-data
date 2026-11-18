"""Synthetic challenge probes; no assessed ratings or model completions."""

from copy import deepcopy

import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_evidence import evidence as evidence
from test_recovery_source_refs import response_for

from aia_mp1.recovery_candidate_challenge import (
    CandidateApplicabilityChallenge,
    challenge_request,
    inspect_candidate_challenge,
)
from aia_mp1.recovery_candidate_wire import prepare_challenge_wire
from aia_mp1.recovery_evidence import EvidencePlan
from aia_mp1.recovery_source_refs import SourceObservations
from aia_mp1.tracing import digest


def setup_probe(evidence):
    plan_data, content, _, _ = evidence
    plan = EvidencePlan.model_validate(plan_data)
    observations = SourceObservations.model_validate(response_for(plan_data))
    request = challenge_request(plan, content, observations)
    candidate_id = request["candidate_passages"][0]["passage_id"]
    response = {
        "protocol": "candidate-applicability-challenge-v1",
        "plan_sha256": digest(plan_data),
        "observations_sha256": digest(observations.model_dump(mode="json")),
        "findings": [
            {
                "check_id": check["check_id"],
                "verdict": "retain",
                "candidate_passage_ids": [candidate_id],
                "source_refs": [check["source_refs"][0]],
                "prerequisite": "Synthetic candidate operation must actually use the API object.",
                "explanation": "Synthetic claim needs independent technical review.",
            }
            for check in request["supported_checks"]
        ],
    }
    return plan, content, observations, request, response


def test_candidate_challenge_retains_objections_without_releasing_scores(evidence):
    plan, content, observations, request, response = setup_probe(evidence)
    assert request["supported_checks"]
    response["findings"][0]["verdict"] = "reject"
    response["findings"][0]["candidate_passage_ids"] = []
    challenge = CandidateApplicabilityChallenge.model_validate(response)
    report = inspect_candidate_challenge(plan, content, observations, challenge)
    assert report["challenged_support"] == [plan.checks[0].check_id]
    assert report["status"] == "awaiting_technical_audit"
    assert report["calibration_eligible"] is False


def test_unbound_tentative_finding_cannot_enter_challenge(evidence):
    plan, content, observations, _, _ = setup_probe(evidence)
    observations.observations[0].sources[0].passage_id = "R.unbound"
    with pytest.raises(ValueError, match="unbound"):
        challenge_request(plan, content, observations)


def test_challenge_wire_is_exact_and_offline(evidence):
    _, _, _, request, _ = setup_probe(evidence)
    settings = {
        "model": "synthetic-local-model",
        "temperature": 0.1,
        "max_tokens": 128,
        "timeout_seconds": 30,
        "messages": [
            {"role": "system", "content": "Synthetic challenge instructions."},
            {"role": "user", "content": str(request)},
        ],
    }
    receipt = prepare_challenge_wire(settings)
    assert receipt["model_starts"] == 0
    assert receipt["wire"]["messages"][0]["content"].startswith(settings["messages"][0]["content"])
    assert receipt["wire"]["messages"][1] == settings["messages"][1]
    assert receipt["wire_sha256"] == digest(receipt["wire"])


@pytest.mark.parametrize(
    "attack",
    ["missing", "reordered", "foreign_candidate", "foreign_source", "empty_retain", "stale_facts"],
)
def test_candidate_challenge_rejects_lineage_and_reference_attacks(evidence, attack):
    plan, content, observations, _, response = setup_probe(evidence)
    response = deepcopy(response)
    if attack == "missing":
        response["findings"].pop()
    elif attack == "reordered":
        response["findings"].reverse()
    elif attack == "foreign_candidate":
        response["findings"][0]["candidate_passage_ids"] = ["C.not-a-passage"]
    elif attack == "foreign_source":
        response["findings"][0]["source_refs"] = [
            {"passage_id": "R.unbound", "version": "not-frozen"}
        ]
    elif attack == "empty_retain":
        response["findings"][0]["candidate_passage_ids"] = []
    else:
        response["observations_sha256"] = "0" * 64
    challenge = CandidateApplicabilityChallenge.model_validate(response)
    with pytest.raises(ValueError):
        inspect_candidate_challenge(plan, content, observations, challenge)
