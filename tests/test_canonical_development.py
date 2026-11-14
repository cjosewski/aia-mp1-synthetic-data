"""Synthetic V9 request accounting and exact wire checks; no model inference."""

import copy
import json

import pytest

from aia_mp1.canonical_development import (
    MODEL_SHA,
    SETTINGS,
    audit,
    parse,
    run,
    save,
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
