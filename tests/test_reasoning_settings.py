"""Explicit reasoning settings must reach the wire and match qualification evidence."""

import json

import httpx
import pytest
from assessed_fixtures import fixture_config, qualified_judge
from test_model_client import completion, make_client, qa_payload

from aia_mp1.judge import JudgeConfig
from aia_mp1.qualification import validate_qualification


@pytest.mark.parametrize("effort", [None, "high"])
def test_reasoning_wire_is_explicit_only_when_selected(effort):
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(json.dumps(qa_payload())))

    with make_client(handler, reasoning_effort=effort) as client:
        assert client.generate([{"role": "user", "content": "Synthetic only"}]).item is not None
    assert len(calls) == 1
    if effort is None:
        assert "reasoning_effort" not in calls[0]
    else:
        assert calls[0]["reasoning_effort"] == effort


def test_reasoning_receipt_cannot_silently_change_inference(tmp_path):
    generator = fixture_config(tmp_path)
    config = qualified_judge(tmp_path, generator)
    assessment = {
        "generator_model_identity": generator.model_identity,
        "generator_model_sha256": generator.model_sha256,
    }
    assert "reasoning_effort" not in config.public_settings()
    validate_qualification(config, assessment)
    high = config.model_copy(update={"reasoning_effort": "high"})
    with pytest.raises(ValueError, match="settings"):
        validate_qualification(high, assessment)
    path = tmp_path / "qualification.json"
    receipt = json.loads(path.read_text())
    receipt["settings"]["reasoning_effort"] = "high"
    path.write_text(json.dumps(receipt))
    assert (
        validate_qualification(high, assessment)["receipt"]["settings"]["reasoning_effort"]
        == "high"
    )
    with pytest.raises(ValueError, match="settings"):
        validate_qualification(config, assessment)
    with pytest.raises(ValueError):
        JudgeConfig(base_url=generator.base_url, model="synthetic", reasoning_effort="unrecognized")
