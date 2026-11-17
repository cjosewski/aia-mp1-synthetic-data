"""Synthetic runtime-evidence attacks; no actual experiment, labels or model findings."""

import hashlib
import json
from copy import deepcopy

import pytest
from test_compact_evidence import sample as sample
from test_factcheck import bundle as bundle
from test_recovery_checks import packet as packet
from test_recovery_checks import span
from test_recovery_evidence import audit_for
from test_recovery_evidence import evidence as evidence
from test_recovery_scoring import scoring as scoring

from aia_mp1.recovery_checks import Observations, Span
from aia_mp1.recovery_evidence import (
    EvidencePlan,
    RuntimeEvidencePlan,
    evidence_request,
    inspect_evidence,
    main,
    parse_plan,
    validate_evidence_plan,
)
from aia_mp1.recovery_runtime import runtime_context
from aia_mp1.recovery_scoring import (
    Effect,
    RuntimeFactAudit,
    build_scoring_input,
    inspect_scores,
    scoring_request,
)
from aia_mp1.recovery_scoring import main as scoring_main
from aia_mp1.tracing import digest


@pytest.fixture
def runtime(evidence):
    plan, content, rubric, root = deepcopy(evidence)

    def artifact(name, text):
        (root / name).write_text(text, encoding="utf-8")
        return {"path": name, "sha256": hashlib.sha256(text.encode()).hexdigest()}

    result = {
        "cases": [
            {
                "case": "synthetic_case",
                "returncode": 0,
                "stdout": "SYNTHETIC result α=7. Not a real finding.\n",
                "stderr": "",
                "timeout": False,
            }
        ]
    }
    record = {
        "record_id": "P0001",
        "author": "Synthetic author",
        "origin": "assistant_authored",
        "created_at": "synthetic-time",
        "scope": "Synthetic test only",
        "limitations": "No real execution; no universal conclusions.",
        "provenance_limitations": "Synthetic identity; not a measured runtime.",
        "scheduled_cases": ["synthetic_case"],
        "protocol": artifact("runtime-protocol.txt", "Synthetic protocol: one synthetic_case."),
        "script": artifact("runtime-script.txt", "# Synthetic script fixture, never executed.\n"),
        "dependency_lock": artifact("runtime-lock.txt", "Synthetic lock fixture."),
        "identities": [artifact("runtime-identity.txt", "Synthetic version only.")],
        "raw_result": artifact("runtime-result.json", json.dumps(result, ensure_ascii=False)),
        "permission": artifact(
            "runtime-permission.json",
            json.dumps(
                {
                    "origin": "standalone_personal_research",
                    "allowed_uses": ["judge_context", "local_evidence"],
                }
            ),
        ),
    }
    plan["protocol"] = "recovery-evidence-v3"
    plan["runtime_records"] = [record]
    child = next(c for c in plan["checks"] if c["evidence_kind"] == "api_contract")
    child["evidence_kind"] = "runtime_observation"
    child["sources"] = [{"passage_id": "P.P0001.synthetic_case.stdout", "version": digest(record)}]
    return plan, content, rubric, root


def typed(data):
    return RuntimeEvidencePlan.model_validate(data[0])


def inspect(data, rows=None):
    return inspect_evidence(typed(data), *data[1:], rows)


def observations(data):
    plan = typed(data)
    catalog = validate_evidence_plan(plan, *data[1:])
    return Observations.model_validate(
        {
            "plan_sha256": digest(data[0]),
            "observations": [
                {
                    "check_id": c.check_id,
                    "status": "supported",
                    "explanation": "Synthetic only.",
                    "citations": [
                        span(c.sources[0].passage_id, catalog[c.sources[0].passage_id]["text"])
                    ],
                }
                for c in plan.checks
            ],
        }
    )


def runtime_audit(data, rows):
    return RuntimeFactAudit.model_validate(
        {
            **audit_for(data[0], rows).model_dump(),
            "runtime_records": [
                {
                    "record_id": "P0001",
                    "accepted": True,
                    "version_and_build_applicable": True,
                    "scheduled_cases_complete": True,
                    "script_matches_outputs": True,
                    "qualifiers_and_limits_reviewed": True,
                    "explanation": "Synthetic audit only.",
                }
            ],
        }
    )


def update_result(data, change):
    record = data[0]["runtime_records"][0]
    path = data[3] / record["raw_result"]["path"]
    value = json.loads(path.read_text())
    change(value)
    path.write_text(json.dumps(value), encoding="utf-8")
    record["raw_result"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    for check in data[0]["checks"]:
        if check["evidence_kind"] == "runtime_observation":
            for source in check["sources"]:
                source["version"] = digest(record)


def test_runtime_is_distinct_and_preserves_both_model_views(runtime):
    assert isinstance(parse_plan(runtime[0]), RuntimeEvidencePlan)
    report = inspect(runtime)
    assert report["empirical_applicability_audit"] == "required"
    assert report["calibration_eligible"] is False and report["model_calls"] == 0
    assert report["unresolved_runtime_checks"] == []
    rows = observations(runtime)
    full = build_scoring_input(typed(runtime), *runtime[1:], rows, runtime_audit(runtime, rows))
    verifier = evidence_request(typed(runtime), *runtime[1:])
    scorer = scoring_request(full)
    assert scorer["protocol"] == "recovery-scoring-v3"
    assert scorer["runtime_records"] == verifier["runtime_records"]
    record = scorer["runtime_records"][0]
    assert record["origin"] == "assistant_authored"
    assert record["limitations"] == runtime[0]["runtime_records"][0]["limitations"]
    assert set(record["artifacts"]) == {
        "protocol",
        "script",
        "dependency_lock",
        "raw_result",
        "permission",
    }
    assert "Synthetic audit" not in json.dumps(scorer)
    assert record["passages"][0]["text"].endswith("Not a real finding.\n")
    scorer["runtime_records"][0]["limitations"] = "changed copy"
    assert full["runtime_records"][0]["limitations"] != "changed copy"


@pytest.mark.parametrize(
    "role", ["protocol", "script", "dependency_lock", "raw_result", "permission", "identity"]
)
def test_changed_bytes_reject_before_a_model_view(runtime, role):
    record = runtime[0]["runtime_records"][0]
    item = record["identities"][0] if role == "identity" else record[role]
    with (runtime[3] / item["path"]).open("a") as f:
        f.write(" altered")
    with pytest.raises(ValueError, match="bytes changed"):
        evidence_request(typed(runtime), *runtime[1:])


@pytest.mark.parametrize("path", ["../escape", "/absolute", "C:/outside", "folder\\escape"])
def test_runtime_paths_cannot_escape_snapshot(runtime, path):
    runtime[0]["runtime_records"][0]["script"]["path"] = path
    with pytest.raises(ValueError):
        inspect(runtime)


@pytest.mark.parametrize(
    "attack", ["omitted", "extra", "duplicate", "renamed", "missing_stream", "bool_exit_code"]
)
def test_capture_accounting_and_types_reject_selective_or_incomplete_records(runtime, attack):
    def change(value):
        cases = value["cases"]
        if attack == "omitted":
            cases.clear()
        elif attack in {"extra", "duplicate"}:
            cases.append(deepcopy(cases[0]))
            if attack == "extra":
                cases[-1]["case"] = "unscheduled"
        elif attack == "renamed":
            cases[0]["case"] = "different"
        elif attack == "missing_stream":
            cases[0]["stdout"] = None
        else:
            cases[0]["returncode"] = True

    update_result(runtime, change)
    with pytest.raises(ValueError):
        inspect(runtime)


@pytest.mark.parametrize(
    "attack",
    [
        "document_as_runtime",
        "runtime_as_document",
        "reasoning_as_runtime",
        "unbound_record",
        "duplicate_record",
        "missing_d3",
        "stale_version",
        "duplicate_schedule",
        "role_reuse",
    ],
)
def test_runtime_authority_and_lineage_attacks(runtime, attack):
    plan = runtime[0]
    child = next(c for c in plan["checks"] if c["evidence_kind"] == "runtime_observation")
    if attack == "document_as_runtime":
        child["sources"] = deepcopy(
            next(c for c in plan["checks"] if c["evidence_kind"] == "api_contract")["sources"]
        )
    elif attack == "runtime_as_document":
        child["evidence_kind"] = "api_contract"
    elif attack == "reasoning_as_runtime":
        note = plan["reasoning_notes"][0]
        child["sources"] = [{"passage_id": f"E.{note['note_id']}", "version": digest(note)}]
    elif attack == "unbound_record":
        child["sources"] = []
    elif attack == "duplicate_record":
        plan["runtime_records"].append(deepcopy(plan["runtime_records"][0]))
    elif attack == "missing_d3":
        child["dimensions"].remove("D3")
    elif attack == "stale_version":
        plan["runtime_records"][0]["limitations"] += " changed"
    elif attack == "duplicate_schedule":
        plan["runtime_records"][0]["scheduled_cases"] *= 2
    else:
        plan["runtime_records"][0]["dependency_lock"] = deepcopy(
            plan["runtime_records"][0]["script"]
        )
    with pytest.raises(ValueError):
        inspect(runtime)


@pytest.mark.parametrize("unknown", ["timeout", "missing_returncode", "other_case_timeout"])
def test_unresolved_outcome_cannot_hide_behind_successful_case(runtime, unknown):
    if unknown == "other_case_timeout":
        runtime[0]["runtime_records"][0]["scheduled_cases"].append("uncertain_case")

    def change(value):
        if unknown == "other_case_timeout":
            value["cases"].append(
                {
                    "case": "uncertain_case",
                    "returncode": None,
                    "stdout": None,
                    "stderr": None,
                    "timeout": True,
                }
            )
        elif unknown == "timeout":
            value["cases"][0]["timeout"] = True
        else:
            value["cases"][0]["returncode"] = None

    update_result(runtime, change)
    assert inspect(runtime)["unresolved_runtime_checks"]
    rows = observations(runtime)
    with pytest.raises(ValueError, match="timed-out"):
        inspect(runtime, rows)
    target = next(
        c["check_id"] for c in runtime[0]["checks"] if c["evidence_kind"] == "runtime_observation"
    )
    next(r for r in rows.observations if r.check_id == target).status = "insufficient"
    with pytest.raises(ValueError, match="unresolved facts"):
        build_scoring_input(typed(runtime), *runtime[1:], rows, runtime_audit(runtime, rows))


@pytest.mark.parametrize(
    "attack",
    [
        "legacy",
        "missing",
        "duplicate",
        "accepted",
        "version_and_build_applicable",
        "scheduled_cases_complete",
        "script_matches_outputs",
        "qualifiers_and_limits_reviewed",
    ],
)
def test_runtime_audit_is_required_per_record(runtime, attack):
    rows = observations(runtime)
    audit = runtime_audit(runtime, rows)
    if attack == "legacy":
        audit = audit_for(runtime[0], rows)
    elif attack == "missing":
        audit.runtime_records = []
    elif attack == "duplicate":
        audit.runtime_records *= 2
    else:
        setattr(audit.runtime_records[0], attack, False)
    with pytest.raises(ValueError):
        build_scoring_input(typed(runtime), *runtime[1:], rows, audit)


def test_v2_cannot_smuggle_runtime_fields(runtime):
    value = deepcopy(runtime[0])
    value["protocol"] = "recovery-evidence-v2"
    with pytest.raises(ValueError):
        EvidencePlan.model_validate(value)


def test_unpermitted_research_cannot_enter_model_context(runtime):
    record = runtime[0]["runtime_records"][0]
    path = runtime[3] / record["permission"]["path"]
    path.write_text(json.dumps({"origin": "research_only", "allowed_uses": ["local_evidence"]}))
    record["permission"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="permission"):
        runtime_context(typed(runtime).runtime_records, runtime[3])


def test_citation_cannot_borrow_an_unbound_stream(runtime):
    update_result(
        runtime, lambda value: value["cases"][0].update(stderr="Synthetic warning only.\n")
    )
    rows = observations(runtime)
    check = next(c for c in typed(runtime).checks if c.evidence_kind == "runtime_observation")
    row = next(r for r in rows.observations if r.check_id == check.check_id)
    row.citations = [
        Span.model_validate(span("P.P0001.synthetic_case.stderr", "Synthetic warning only.\n"))
    ]
    with pytest.raises(ValueError, match="outside"):
        inspect(runtime, rows)


def test_stale_runtime_audit_cannot_follow_a_revised_plan(runtime):
    rows = observations(runtime)
    audit = runtime_audit(runtime, rows)
    runtime[0]["runtime_records"][0]["provenance_limitations"] += " Changed identity timing."
    update_result(runtime, lambda value: None)
    revised_rows = observations(runtime)
    with pytest.raises(ValueError, match="lineage"):
        build_scoring_input(typed(runtime), *runtime[1:], revised_rows, audit)


def test_symlink_runtime_artifact_is_rejected(runtime, tmp_path):
    record = runtime[0]["runtime_records"][0]
    outside = tmp_path / "outside-runtime-script"
    outside.write_text("synthetic outside")
    path = runtime[3] / record["script"]["path"]
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        inspect(runtime)


def test_runtime_cli_reports_unknown_outcomes_without_dispatch(runtime, capsys):
    update_result(runtime, lambda value: value["cases"][0].update(returncode=None))
    plan, content, rubric, root = runtime
    args = ["--sources", str(root)]
    for name, value in (("plan", plan), ("input", content), ("rubric", rubric)):
        path = root / f"cli-{name}.json"
        path.write_text(json.dumps(value))
        args += [f"--{name}", str(path)]
    assert main(args) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["unresolved_runtime_checks"] and result["model_calls"] == 0


def test_legacy_plan_cli_failure_is_controlled(packet, capsys):
    plan, content, rubric, root, _ = packet
    args = ["--sources", str(root)]
    for name, value in (("plan", plan), ("input", content), ("rubric", rubric)):
        path = root / f"legacy-{name}.json"
        path.write_text(json.dumps(value))
        args += [f"--{name}", str(path)]
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)["type"] == "ValueError"


def test_runtime_preserves_mixed_case_experiment_ids(runtime):
    runtime[0]["runtime_records"][0]["scheduled_cases"] = ["synthetic_scaled_E"]
    update_result(runtime, lambda value: value["cases"][0].update(case="synthetic_scaled_E"))
    for check in runtime[0]["checks"]:
        if check["evidence_kind"] == "runtime_observation":
            check["sources"][0]["passage_id"] = "P.P0001.synthetic_scaled_E.stdout"
    wire = evidence_request(typed(runtime), *runtime[1:])
    assert wire["runtime_records"][0]["scheduled_cases"] == ["synthetic_scaled_E"]
    assert wire["runtime_records"][0]["captures"][0]["case"] == "synthetic_scaled_E"


def test_v3_scoring_cli_requires_both_audits_and_stays_development(
    runtime, scoring, tmp_path, capsys
):
    raw, content, rubric, root = runtime
    plan = typed(runtime)
    rows = observations(runtime)
    audit = runtime_audit(runtime, rows)
    payload = build_scoring_input(plan, content, rubric, root, rows, audit)
    _, scores, score_audit = scoring
    scores.scoring_input_sha256 = digest(payload)
    for dimension, fields in payload["dimensions"].items():
        getattr(scores, dimension).effects = [
            Effect(check_id=k, effect="supports", explanation="Synthetic only.")
            for k in fields["required_checks"]
        ]
    score_audit.scores_sha256 = digest(scores.model_dump(mode="json"))
    args = ["--sources", str(root)]
    for name, value in (
        ("plan", raw),
        ("input", content),
        ("rubric", rubric),
        ("observations", rows.model_dump()),
        ("fact-audit", audit.model_dump()),
        ("scores", scores.model_dump()),
    ):
        path = tmp_path / f"v3-{name}.json"
        path.write_text(json.dumps(value))
        args += [f"--{name}", str(path)]
    assert scoring_main(args) == 1
    assert json.loads(capsys.readouterr().out)["judgment"] is None
    path = tmp_path / "v3-score-audit.json"
    path.write_text(json.dumps(score_audit.model_dump()))
    assert scoring_main(args + ["--score-audit", str(path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "audited_development" and not report["calibration_eligible"]
    assert report["model_calls"] == 0
    assert report == inspect_scores(plan, content, rubric, root, rows, audit, scores, score_audit)
