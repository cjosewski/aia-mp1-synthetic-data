"""Synthetic V9 request accounting and exact wire checks; no model inference."""

import copy
import json

import pytest

from aia_mp1.canonical_development import (
    MODEL_SHA,
    SETTINGS,
    audit,
    compose,
    parse,
    run,
    save,
    schema_for,
    schema_identity,
    validate_plan,
    verify_runtime,
    wire_for,
)
from aia_mp1.evaluation_schemas import DIMENSIONS, Judgment
from aia_mp1.tracing import digest


@pytest.fixture
def fixture(tmp_path):
    plan = {
        "protocol": "v9-canonical-development",
        "prior_starts": 99,
        "max_starts": 20,
        "settings": SETTINGS,
        "model_sha256": MODEL_SHA,
        "model": "synthetic-native-model",
        "cases": [
            {
                "item_id": f"qualification-v1-{i:02d}",
                "messages": [
                    {"role": "system", "content": "Synthetic only."},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "untrusted_item": {"question": f"Synthetic {i}"},
                                "untrusted_reference_context": {},
                            }
                        ),
                    },
                ],
            }
            for i in range(1, 11)
        ],
    }
    directory = tmp_path / "ledger"
    directory.mkdir()
    save(
        directory / "manifest.json",
        {"plan_sha256": digest(plan), "schema_sha256": digest(Judgment.model_json_schema())},
    )
    return plan, directory


def completion(model="synthetic-native-model", finish="stop"):
    judgment = {d: {"decision": 1, "justification": "Synthetic test only."} for d in DIMENSIONS}
    return {
        "model": model,
        "choices": [{"finish_reason": finish, "message": {"content": json.dumps(judgment)}}],
    }


def test_exact_wire_and_complete_run(fixture):
    plan, directory = fixture
    wire = wire_for(plan, plan["cases"][0])
    assert wire["max_tokens"] == 8192 and wire["reasoning_effort"] == "high"
    calls = []

    def dispatch(case, wire):
        # The start is persisted before the external dispatch.
        calls.append(case["item_id"])
        assert (directory / f"{len(calls):03d}-start.json").exists()
        return completion(), None

    state = run(plan, directory, dispatch)
    assert len(calls) == len(state["successful"]) == 10
    assert len(run(plan, directory, dispatch)["attempts"]) == 10
    assert len(calls) == 10


def test_two_failures_stop_and_cannot_be_resumed(fixture):
    plan, directory = fixture
    calls = []

    def dispatch(case, wire):
        calls.append(case)
        return completion(finish="length"), "Synthetic output exhaustion"

    state = run(plan, directory, dispatch)
    assert len(calls) == 2 and not state["successful"]
    assert run(plan, directory, dispatch)["consecutive_failures"] == 2
    assert len(calls) == 2


def test_unknown_outcome_blocks_without_new_dispatch(fixture):
    plan, directory = fixture

    def interrupted(case, wire):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run(plan, directory, interrupted)
    with pytest.raises(ValueError, match="unknown request outcome"):
        run(plan, directory, lambda *_: pytest.fail("must not dispatch"))


def test_raw_response_and_plan_mutations_rejected(fixture):
    plan, directory = fixture
    run(plan, directory, lambda *_: (completion(), None))
    path = directory / "001-result.json"
    result = json.loads(path.read_text())
    result["judgment"]["D1"]["decision"] = 0
    result["sha256"] = digest({k: v for k, v in result.items() if k != "sha256"})
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match="raw completion"):
        audit(plan, directory)
    changed = copy.deepcopy(plan)
    changed["settings"] = SETTINGS | {"max_tokens": 4096}
    with pytest.raises(ValueError, match="protocol"):
        audit(changed, directory)
    assert parse(completion(model="unexpected-model"), plan["model"]) is None
    assert parse(completion(finish="length"), plan["model"]) is None
    assert parse(None, plan["model"]) is None


def test_restart_nonce_does_not_relax_model_or_prompt_checks():
    expected = {
        "properties": {
            "media_marker": "random-first-start",
            "chat_template": "pinned",
            "default_generation_settings": {"n_ctx": 16384, "temperature": 0.1},
        },
        "token_checks": [{"rendered_prompt_sha256": "pinned", "prompt_tokens": 100}],
    }
    observed = copy.deepcopy(expected)
    observed["properties"]["media_marker"] = "random-second-start"
    verify_runtime(expected, observed)
    assert expected["properties"]["media_marker"] == "random-first-start"
    observed["properties"]["default_generation_settings"]["n_ctx"] = 8192
    with pytest.raises(ValueError, match="runtime changed"):
        verify_runtime(expected, observed)
    observed = copy.deepcopy(expected)
    observed["token_checks"][0]["rendered_prompt_sha256"] = "changed"
    with pytest.raises(ValueError, match="runtime changed"):
        verify_runtime(expected, observed)


def test_v10_allocation_does_not_reuse_v9_budget(fixture):
    plan, _ = fixture
    changed = copy.deepcopy(plan)
    changed["protocol"] = "v10-canonical-development"
    with pytest.raises(ValueError, match="budget"):
        validate_plan(changed)
    changed["prior_starts"] = 109
    validate_plan(changed)


@pytest.fixture
def isolated(fixture, tmp_path):
    original, _ = fixture
    plan = copy.deepcopy(original)
    plan.update(protocol="v11-isolated-development", prior_starts=119, max_starts=40)
    plan["cases"] = []
    for case in original["cases"]:
        for stage in ("core", "context"):
            part = copy.deepcopy(case)
            part.update(
                item_id=f"{case['item_id']}:{stage}", original_item_id=case["item_id"], stage=stage
            )
            part["messages"][0]["content"] = f"Synthetic {stage} only."
            plan["cases"].append(part)
    directory = tmp_path / "isolated"
    directory.mkdir()
    save(
        directory / "manifest.json",
        {"plan_sha256": digest(plan), "schema_sha256": schema_identity(plan)},
    )
    return plan, directory


def stage_completion(plan, case):
    raw = completion()
    full = json.loads(raw["choices"][0]["message"]["content"])
    subset = {d: full[d] for d in schema_for(plan, case).model_fields}
    raw["choices"][0]["message"]["content"] = json.dumps(subset)
    return raw


def test_isolated_composition_requires_both_new_calls(isolated):
    plan, directory = isolated
    calls = []

    # Inspect partial completion after dispatch is fully persisted, not while
    # its fsynced start correctly represents an unknown outcome.
    def complete(case, wire):
        calls.append(case["item_id"])
        assert wire["messages"][-1] == case["messages"][1]
        return stage_completion(plan, case), None

    state = run(plan, directory, complete)
    assert len(calls) == len(state["successful"]) == 20
    assert len(compose(plan, state)) == 10
    partial = copy.deepcopy(state)
    del partial["successful"]["qualification-v1-01:context"]
    assert "qualification-v1-01" not in compose(plan, partial)
    assert len(compose(plan, partial)) == 9
    run(plan, directory, lambda *_: pytest.fail("completed stages must not rerun"))


def test_isolated_rejects_extra_dimensions_and_changed_input(isolated):
    plan, directory = isolated
    # A full six-dimension answer violates either isolated schema.
    for case in plan["cases"][:2]:
        assert parse(completion(), plan["model"], schema_for(plan, case)) is None
    calls = []

    def dispatch(case, wire):
        calls.append(case["item_id"])
        if case["stage"] == "core":
            return stage_completion(plan, case), None
        return completion(), None

    state = run(plan, directory, dispatch)
    assert len(calls) == 3 and state["consecutive_failures"] == 2
    assert compose(plan, state) == {}
    assert len(state["successful"]) == 1
    changed = copy.deepcopy(plan)
    changed["cases"][1]["messages"][1]["content"] = json.dumps(
        {"untrusted_item": {"question": "Changed"}, "untrusted_reference_context": {}}
    )
    with pytest.raises(ValueError, match="identical original input"):
        validate_plan(changed)
    changed = copy.deepcopy(plan)
    changed["prior_starts"] = 109
    with pytest.raises(ValueError, match="budget"):
        validate_plan(changed)


def test_presentation_preserves_original_values_and_canonical_schema(fixture, tmp_path):
    original, _ = fixture
    plan = copy.deepcopy(original)
    plan.update(protocol="v12-presentation-development", prior_starts=139)
    with pytest.raises(ValueError, match="serialization"):
        validate_plan(plan)
    for case, old in zip(plan["cases"], original["cases"]):
        case["messages"][1]["content"] = json.dumps(
            json.loads(old["messages"][1]["content"]), ensure_ascii=False, indent=2
        )
        assert json.loads(case["messages"][1]["content"]) == json.loads(
            old["messages"][1]["content"]
        )
        assert case["messages"][0] == old["messages"][0]
    validate_plan(plan)
    assert schema_identity(plan) == schema_identity(original)
    assert wire_for(plan, plan["cases"][0])["messages"][-1] == plan["cases"][0]["messages"][1]
    directory = tmp_path / "presentation"
    directory.mkdir()
    save(
        directory / "manifest.json",
        {"plan_sha256": digest(plan), "schema_sha256": schema_identity(plan)},
    )
    state = run(plan, directory, lambda *_: (completion(), None))
    assert len(compose(plan, state)) == len(state["attempts"]) == 10
