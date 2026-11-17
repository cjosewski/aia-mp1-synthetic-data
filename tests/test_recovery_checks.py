"""Synthetic adversarial checks only; no real reviews, factual findings or calls."""

import json
from copy import deepcopy

import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle

from aia_mp1.recovery_checks import CheckPlan, Observations, Span, check_span, inspect_offline, main
from aia_mp1.tracing import digest


@pytest.fixture
def packet(bundle):
    experiment, root = bundle
    content = experiment.cases[0].content
    checks = []
    for key, passage in content["passage_catalog"].items():
        if passage["authority"] not in {"candidate", "task"}:
            continue
        kind, dimensions = "technical_claim", ["D1", "D3"]
        if key == "R.task":
            kind, dimensions = "task_obligation", ["D1", "D5"]
        elif key in {"C.question", "C.equipment_problem"}:
            kind, dimensions = "context", ["D5"]
        if key.startswith("C.tips."):
            dimensions.append("D6")
        if key == "C.safety_info":
            dimensions.append("D2")
        checks.append(
            {
                "check_id": f"K{len(checks) + 1:04d}",
                "kind": kind,
                "subject": span(key, passage["text"]),
                "question": "Synthetic structural test; citation may not support the claim.",
                "dimensions": dimensions,
                "sources": [{"passage_id": "R.fact.0", "version": "synthetic-v1"}],
            }
        )
    plan = {
        "protocol": "recovery-offline-v1",
        "input_sha256": digest(content),
        "rubric_sha256": digest(experiment.rubric),
        "checks": checks,
    }
    observations = [
        {
            "check_id": check["check_id"],
            "status": "supported",
            "citations": [span("R.fact.0", content["primary_excerpts"][0]["text"])],
            "explanation": "Synthetic unsupported assertion for structural testing only.",
        }
        for check in checks
    ]
    return plan, content, experiment.rubric, root, observations


def span(identifier, text):
    return {"passage_id": identifier, "start": 0, "end": len(text), "quote": text}


def inspect(packet, observations=True):
    plan, content, rubric, root, rows = packet
    response = (
        Observations.model_validate(
            {
                "plan_sha256": digest(plan),
                "observations": rows,
            }
        )
        if observations
        else None
    )
    return inspect_offline(CheckPlan.model_validate(plan), content, rubric, root, response)


def test_exact_citations_never_certify_semantic_truth_or_calibration(packet):
    before = deepcopy(packet[:3])
    report = inspect(packet)
    assert report["structural_status"] == "awaiting_semantic_audit"
    assert report["semantic_audit"] == "required"
    assert report["calibration_eligible"] is False
    assert report["model_calls"] == 0
    assert packet[:3] == before
    assert not {"judgment", "agreement", "human_labels"} & report.keys()


@pytest.mark.parametrize("subject", ["C.tips.0", "R.task", "C.steps.1"])
def test_omitted_tip_task_or_step_is_rejected(packet, subject):
    plan = packet[0]
    plan["checks"] = [c for c in plan["checks"] if c["subject"]["passage_id"] != subject]
    for i, check in enumerate(plan["checks"], 1):
        check["check_id"] = f"K{i:04d}"
    with pytest.raises(ValueError, match="uncovered"):
        inspect(packet, False)


@pytest.mark.parametrize("mutation", ["kind", "tip_dimension", "safety_dimension", "task_source"])
def test_technical_claims_cannot_bypass_primary_evidence_or_review(packet, mutation):
    check = next(
        c
        for c in packet[0]["checks"]
        if c["subject"]["passage_id"]
        == ("C.safety_info" if mutation == "safety_dimension" else "C.tips.0")
    )
    if mutation == "kind":
        check["kind"] = "context"
    elif mutation == "tip_dimension":
        check["dimensions"].remove("D6")
    elif mutation == "safety_dimension":
        check["dimensions"].remove("D2")
    else:
        check["sources"] = [{"passage_id": "R.task", "version": "frozen-task"}]
    with pytest.raises(ValueError):
        inspect(packet, False)


@pytest.mark.parametrize(
    "mutation",
    ["prose_id", "candidate_as_source", "wrong_version", "changed_quote", "overlap", "human_label"],
)
def test_wrong_roles_versions_text_and_hidden_labels_fail(packet, mutation):
    check = packet[0]["checks"][0]
    if mutation == "prose_id":
        check["check_id"] = "This is a rubric requirement, not an ID."
    elif mutation == "candidate_as_source":
        check["sources"][0]["passage_id"] = "C.answer"
    elif mutation == "wrong_version":
        check["sources"][0]["version"] = "synthetic-v2"
    elif mutation == "changed_quote":
        check["subject"]["quote"] += " invented"
    elif mutation == "human_label":
        packet[0]["human_label"] = {"D1": 1}
    else:
        clone = deepcopy(check)
        clone["check_id"] = f"K{len(packet[0]['checks']) + 1:04d}"
        packet[0]["checks"].append(clone)
    with pytest.raises(ValueError):
        inspect(packet, False)


def test_source_gap_cannot_be_a_pass_or_silent_default(packet):
    packet[0]["checks"][0]["sources"] = []
    report = inspect(packet, False)
    assert report["source_gaps"] == ["K0001"]
    with pytest.raises(ValueError):
        inspect(packet)
    packet[4][0].update(status="insufficient", citations=[])
    report = inspect(packet)
    assert report["structural_status"] == "unresolved"
    assert report["unresolved"] == ["K0001"]


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "foreign", "uncited", "invented"])
def test_incomplete_or_invented_observations_fail(packet, mutation):
    rows = packet[4]
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif mutation == "foreign":
        rows[0]["citations"][0] = span("R.task", packet[1]["passage_catalog"]["R.task"]["text"])
    elif mutation == "uncited":
        rows[0]["citations"] = []
    else:
        rows[0]["citations"][0]["quote"] = "Invented evidence"
    with pytest.raises(ValueError):
        inspect(packet)


def test_old_response_cannot_follow_changed_check_or_source(packet):
    plan, content, rubric, root, rows = packet
    response = Observations.model_validate({"plan_sha256": digest(plan), "observations": rows})
    plan["checks"][0]["question"] = "Different synthetic check."
    with pytest.raises(ValueError, match="different checklist"):
        inspect_offline(CheckPlan.model_validate(plan), content, rubric, root, response)
    (root / "reader.txt").write_text("Changed source.", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        inspect(packet, False)


def test_contradictions_are_retained_without_automatic_dimension_scores(packet):
    packet[4][0]["status"] = "contradicted"
    report = inspect(packet)
    assert report["contradicted"] == ["K0001"]
    assert report["calibration_eligible"] is False


def test_unicode_offsets_and_whitespace_preserve_exact_evidence():
    text = "  Synthetic α finding.\n"
    citation = Span.model_validate(span("R.fact.0", text))
    assert citation.quote == text
    check_span(citation, {"R.fact.0": {"text": text}})
    citation.end = len(text.encode("utf-8"))
    with pytest.raises(ValueError, match="exact"):
        check_span(citation, {"R.fact.0": {"text": text}})


@pytest.mark.parametrize("field", ["input_sha256", "rubric_sha256"])
def test_changed_frozen_identity_fails_before_response(packet, field):
    packet[0][field] = "0" * 64
    with pytest.raises(ValueError, match="fingerprint"):
        inspect(packet, False)


def test_offline_cli_reports_gaps_and_errors_without_mutating_inputs(packet, tmp_path, capsys):
    plan, content, rubric, root, rows = packet
    plan["checks"][0]["sources"] = []
    arguments = ["--sources", str(root)]
    paths = []
    for name, value in (("plan", plan), ("input", content), ("rubric", rubric)):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        arguments += [f"--{name}", str(path)]
        paths.append(path)
    before = [p.read_bytes() for p in paths]
    assert main(arguments) == 1
    assert json.loads(capsys.readouterr().out)["source_gaps"] == ["K0001"]
    assert [p.read_bytes() for p in paths] == before
    paths[0].write_text('{"sensitive": "DO_NOT_ECHO"}', encoding="utf-8")
    assert main(arguments) == 2
    assert "DO_NOT_ECHO" not in capsys.readouterr().out
