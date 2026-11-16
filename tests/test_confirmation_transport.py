"""Synthetic model responses and human declarations; no real inference or labels."""

import json

import pytest
from test_confirmation_review import packet  # noqa: F401 -- shared synthetic fixture

from aia_mp1 import confirmation_transport as transport_module
from aia_mp1.canonical_development import QWEN_MODEL_SHA, QWEN_SETTINGS, save
from aia_mp1.confirmation_review import byte_hash, freeze_review, load_review
from aia_mp1.confirmation_transport import (
    GENERATOR_SHA,
    RUNTIME,
    audit,
    comparison_report,
    initialize,
    load_plan,
    main,
    make_plan,
    next_phase,
    record_external_recovery,
    run_phase,
    verify_thinking_template,
    wire_for,
)
from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.tracing import digest


@pytest.fixture
def confirmation(packet, tmp_path):  # noqa: F811 -- pytest resolves the imported fixture
    directory, _, answers = packet
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(
        settings=QWEN_SETTINGS,
        candidate_model_sha256=QWEN_MODEL_SHA,
        comparison_model_sha256=GENERATOR_SHA,
        prior_starts=190,
        maximum_new_starts=40,
        maximum_attempts_per_case_model=2,
        runtime=RUNTIME,
    )
    manifest_path.write_text(json.dumps(manifest))
    sha = byte_hash(manifest_path)
    review = tmp_path / "review"
    freeze_review(directory, sha, answers, review)
    models = {
        "candidate": "/synthetic/Qwen_Qwen3.5-122B-A10B-Q4_K_M-00001-of-00002.gguf",
        "comparator": "/synthetic/Qwen3-30B-A3B-Q4_K_M.gguf",
    }
    plan = make_plan(directory, sha, review, models)
    path = tmp_path / "plan.json"
    save(path, plan)
    ledger = tmp_path / "ledger"
    initialize(plan, ledger)
    return plan, path, directory, review, ledger


def completion(model, finish="stop"):
    return {
        "model": model["model"],
        "choices": [
            {
                "finish_reason": finish,
                "message": {
                    "content": json.dumps(
                        {d: {"decision": 1, "justification": "Synthetic only."} for d in DIMENSIONS}
                    )
                },
            }
        ],
    }


def test_matched_inputs_no_labels_and_two_phase_accounting(confirmation):
    plan, path, packet_dir, review, ledger = confirmation
    assert load_plan(path, packet_dir, review) == plan
    wires = [wire_for(plan, m, plan["cases"][0]) for m in plan["models"]]
    assert {k: v for k, v in wires[0].items() if k != "model"} == {
        k: v for k, v in wires[1].items() if k != "model"
    }
    assert "reasoning_effort" not in wires[0]
    assert "Synthetic test reviewer" not in json.dumps(wires)
    calls = []

    def dispatch(model, case, wire):
        calls.append((model["phase"], case["item_id"]))
        assert (ledger / f"{len(calls):03d}-start.json").exists()
        return completion(model), None

    state = run_phase(plan, "candidate", ledger, dispatch)
    assert len(calls) == 10 and next_phase(plan, state) == "comparator"
    with pytest.raises(ValueError, match="next permitted"):
        run_phase(plan, "candidate", ledger, dispatch)
    state = run_phase(plan, "comparator", ledger, dispatch)
    assert len(calls) == 20 and next_phase(plan, state) is None
    reference = load_review(packet_dir, plan["packet_manifest_sha256"], review)
    report = comparison_report(plan, state, reference)
    assert report["cumulative_starts"] == 210
    for result in report["models"].values():
        assert result["initial_valid"] == result["valid_cases"] == 10
        assert result["dimensions"]["D1"]["false_approvals"] == 10
        assert result["unresolved"] == 0


def test_retry_is_retained_and_initial_denominator_not_recovered(confirmation):
    plan, _, packet_dir, review, ledger = confirmation
    calls = 0

    def dispatch(model, case, wire):
        nonlocal calls
        calls += 1
        return completion(model, "length" if calls == 1 else "stop"), None

    state = run_phase(plan, "candidate", ledger, dispatch)
    report = comparison_report(
        plan, state, load_review(packet_dir, plan["packet_manifest_sha256"], review)
    )
    candidate = report["models"]["candidate"]
    assert (
        candidate["starts"],
        candidate["initial_valid"],
        candidate["valid_cases"],
        candidate["retry_starts"],
    ) == (11, 9, 10, 1)
    assert report["models"]["comparator"]["unresolved"] == 10
    assert report["models"]["comparator"]["dimensions"]["D1"]["compared"] == 0


def test_two_failures_block_both_models_without_budget_reset(confirmation):
    plan, _, _, _, ledger = confirmation
    calls = []

    def fail(model, case, wire):
        calls.append(case)
        return None, "Synthetic transport failure"

    state = run_phase(plan, "candidate", ledger, fail)
    assert state["consecutive_failures"] == 2 and len(calls) == 2
    for phase in ("candidate", "comparator"):
        with pytest.raises(ValueError, match="next permitted"):
            run_phase(plan, phase, ledger, fail)
    assert len(calls) == 2


def test_unknown_outcome_blocks_replay_and_dispatch(confirmation):
    plan, _, _, _, ledger = confirmation

    def interrupted(*args):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_phase(plan, "candidate", ledger, interrupted)
    assert len(list(ledger.glob("*-start.json"))) == 1
    for phase in ("candidate", "comparator"):
        with pytest.raises(ValueError, match="unknown request outcome"):
            run_phase(plan, phase, ledger, interrupted)


def test_external_recovery_keeps_prefix_and_all_attempt_denominators(confirmation):
    plan, _, packet_dir, review, ledger = confirmation
    calls = []

    def interrupted(model, case, wire):
        calls.append(case["item_id"])
        return (completion(model), None) if len(calls) == 1 else (None, "Connection error.")

    state = run_phase(plan, "candidate", ledger, interrupted)
    assert len(calls) == 3 and next_phase(plan, state) is None
    original = {p.name: p.read_bytes() for p in ledger.glob("*.json")}
    receipt = record_external_recovery(
        plan,
        ledger,
        {
            "reported_by": "Synthetic owner",
            "incident_statement": "Synthetic external shutdown",
            "availability_statement": "Synthetic host now available",
        },
    )
    assert receipt["after_serial"] == 3
    with pytest.raises(ValueError, match="already recorded"):
        record_external_recovery(plan, ledger, {})
    resumed = []

    def success(model, case, wire):
        resumed.append(case["item_id"])
        return completion(model), None

    state = run_phase(plan, "candidate", ledger, success)
    assert resumed == [c["item_id"] for c in plan["cases"][1:]]
    assert json.loads((ledger / "004-start.json").read_text())["number"] == 3
    assert all((ledger / name).read_bytes() == data for name, data in original.items())
    state = run_phase(plan, "comparator", ledger, success)
    report = comparison_report(
        plan, state, load_review(packet_dir, plan["packet_manifest_sha256"], review)
    )
    assert report["starts"] == 22 and report["cumulative_starts"] == 212
    assert report["models"]["candidate"]["initial_valid"] == 9
    assert report["models"]["candidate"]["retry_starts"] == 2
    assert report["models"]["candidate"]["valid_cases"] == 10
    assert report["protocol_amendment"] == receipt
    (ledger / "001-result.json").write_text("changed")
    with pytest.raises(ValueError, match="prefix changed"):
        audit(plan, ledger)


@pytest.mark.parametrize("outcome", ["malformed", "unknown", "third_failure"])
def test_external_recovery_does_not_remove_other_stop_conditions(confirmation, outcome):
    plan, _, _, _, ledger = confirmation
    incident = {
        "reported_by": "Synthetic",
        "incident_statement": "Synthetic shutdown",
        "availability_statement": "Synthetic available",
    }
    if outcome == "unknown":

        def dispatch(*args):
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            run_phase(plan, "candidate", ledger, dispatch)
        with pytest.raises(ValueError, match="unknown request outcome"):
            record_external_recovery(plan, ledger, incident)
    elif outcome == "malformed":
        run_phase(plan, "candidate", ledger, lambda m, c, w: (completion(m, "length"), None))
        with pytest.raises(ValueError, match="external connection-loss"):
            record_external_recovery(plan, ledger, incident)
    else:

        def fail(m, c, w):
            return None, "Connection error."

        run_phase(plan, "candidate", ledger, fail)
        record_external_recovery(plan, ledger, incident)
        state = run_phase(plan, "candidate", ledger, fail)
        # One extra try of the interrupted case, then one failed start on the next case.
        assert len(state["attempts"]) == 4 and state["consecutive_failures"] == 2
        assert next_phase(plan, state) is None
        with pytest.raises(ValueError, match="next permitted"):
            run_phase(plan, "comparator", ledger, fail)


def test_review_tampering_and_unreviewed_input_prevent_cli_dispatch(confirmation, monkeypatch):
    plan, path, packet_dir, review, ledger = confirmation
    monkeypatch.setattr(
        "aia_mp1.confirmation_transport.prepare_runtime",
        lambda *a: pytest.fail("preflight reached"),
    )
    plan["cases"][0]["messages"][1]["content"] += "unreviewed change"
    plan["sha256"] = digest({k: v for k, v in plan.items() if k != "sha256"})
    path.write_text(json.dumps(plan))
    args = [
        "execute",
        "--plan",
        str(path),
        "--packet",
        str(packet_dir),
        "--review",
        str(review),
        "--directory",
        str(ledger),
        "--phase",
        "candidate",
    ]
    assert main(args) == 1
    assert not list(ledger.glob("*-start.json"))


def test_preflight_failure_creates_no_request(confirmation):
    plan, _, _, _, ledger = confirmation

    def invalid_runtime():
        raise ValueError("Synthetic identity mismatch")

    with pytest.raises(ValueError, match="identity mismatch"):
        run_phase(
            plan,
            "candidate",
            ledger,
            lambda *a: pytest.fail("dispatch reached"),
            verify_before=invalid_runtime,
        )
    assert not list(ledger.glob("*-start.json"))


@pytest.mark.parametrize("mutation", ["orphan", "parsed", "wire", "phase", "model"])
def test_ledger_tampering_is_not_repaired(confirmation, mutation):
    plan, _, _, _, ledger = confirmation
    run_phase(plan, "candidate", ledger, lambda m, c, w: (completion(m), None))
    first = ledger / "001-result.json"
    result = json.loads(first.read_text())
    if mutation == "orphan":
        (ledger / "999-result.json").write_text(first.read_text())
    elif mutation in {"wire", "phase"}:
        path = ledger / "001-start.json"
        start = json.loads(path.read_text())
        start["wire_sha256" if mutation == "wire" else "phase"] = "changed"
        path.write_text(json.dumps(start))
    else:
        if mutation == "parsed":
            result["judgment"]["D1"]["decision"] = 0
        else:
            result["raw_response"]["model"] = "wrong model"
        result["sha256"] = digest({k: v for k, v in result.items() if k != "sha256"})
        first.write_text(json.dumps(result))
    with pytest.raises(ValueError):
        audit(plan, ledger)


@pytest.mark.parametrize("defect", [None, "model", "context", "overflow", "thinking"])
def test_native_preflight_records_exact_inputs_and_blocks_drift(confirmation, monkeypatch, defect):
    plan, _, _, _, ledger = confirmation
    model = plan["models"][0]
    calls = []

    class FakeServer:
        def __init__(self, *args):
            pass

        def json(self, path, body=None):
            calls.append(path)
            if path == "/props":
                return {
                    "build_info": RUNTIME["build_info"],
                    "total_slots": 1,
                    "default_generation_settings": {
                        "n_ctx": 4096 if defect == "context" else 16384
                    },
                    "model_path": model["model"],
                    "chat_template": "Synthetic template.",
                }
            if path == "/v1/models":
                return {"data": [{"id": "wrong" if defect == "model" else model["model"]}]}
            if path == "/health":
                return {"status": "ok"}
            if path == "/apply-template":
                return {
                    "prompt": "synthetic"
                    if defect == "thinking"
                    else "<|im_start|>assistant\n<think>\n"
                }
            pytest.fail(f"unexpected endpoint {path}")

        def token_fit(self, wire, context):
            return {
                "fits": defect != "overflow",
                "wire_sha256": digest(wire),
                "context_size": context,
            }

        def close(self):
            pass

    monkeypatch.setattr(transport_module, "LocalServer", FakeServer)
    monkeypatch.setattr(transport_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(transport_module.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(transport_module, "weight_identity", lambda model: model["sha256"])
    if defect:
        with pytest.raises(ValueError):
            transport_module.prepare_runtime(plan, "candidate", ledger, "http://127.0.0.1:8081/v1")
        assert not (ledger / "candidate-runtime.json").exists()
    else:
        first = transport_module.prepare_runtime(
            plan, "candidate", ledger, "http://127.0.0.1:8081/v1"
        )
        assert len(first["token_checks"]) == 10
        transport_module.prepare_runtime(plan, "candidate", ledger, "http://127.0.0.1:8081/v1")
        assert (ledger / "candidate-observation-001.json").exists()
        first["properties"]["chat_template"] = "changed"
        (ledger / "candidate-runtime.json").write_text(json.dumps(first))
        with pytest.raises(ValueError, match="runtime changed"):
            transport_module.prepare_runtime(plan, "candidate", ledger, "http://127.0.0.1:8081/v1")
    assert "/v1/chat/completions" not in calls
    assert not list(ledger.glob("*-start.json"))


def test_comparator_weight_must_match_exact_checksum(tmp_path):
    path = tmp_path / "synthetic.gguf"
    path.write_bytes(b"synthetic test weight only")
    model = {"phase": "comparator", "model": str(path), "sha256": byte_hash(path)}
    assert transport_module.weight_identity(model) == model["sha256"]
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        transport_module.weight_identity(model)


@pytest.mark.parametrize("phase", ["candidate", "comparator"])
def test_native_thinking_prefix_is_model_specific_and_disabled_mode_fails(monkeypatch, phase):
    import hashlib

    template = "Synthetic pinned Qwen3 template"
    monkeypatch.setattr(
        transport_module, "QWEN3_TEMPLATE_SHA", hashlib.sha256(template.encode()).hexdigest()
    )
    properties = {"chat_template": template}
    prefix = "<|im_start|>assistant\n"
    correct = prefix + ("<think>\n" if phase == "candidate" else "")
    verify_thinking_template(phase, properties, "synthetic input\n" + correct)
    with pytest.raises(ValueError, match="native thinking"):
        verify_thinking_template(phase, properties, prefix + "<think>\n\n</think>\n\n")
    wrong = prefix if phase == "candidate" else prefix + "<think>\n"
    with pytest.raises(ValueError, match="native thinking"):
        verify_thinking_template(phase, properties, wrong)
    if phase == "comparator":
        with pytest.raises(ValueError, match="identity differs"):
            verify_thinking_template(phase, {"chat_template": "Different template"}, correct)


def test_missing_human_review_blocks_even_offline_preparation(confirmation, tmp_path):
    plan, _, packet_dir, _, _ = confirmation
    target = tmp_path / "must-not-exist.json"
    assert (
        main(
            [
                "prepare",
                "--packet",
                str(packet_dir),
                "--review",
                str(tmp_path / "missing-review"),
                "--manifest-sha256",
                plan["packet_manifest_sha256"],
                "--plan",
                str(target),
                "--candidate-model",
                plan["models"][0]["model"],
                "--comparator-model",
                plan["models"][1]["model"],
            ]
        )
        == 1
    )
    assert not target.exists()
