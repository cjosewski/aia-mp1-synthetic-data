"""Synthetic V8.1 protocol accounting and instruction-boundary regressions."""

import json

import pytest
from test_factcheck import bundle as bundle
from test_factcheck import sample as sample

from aia_mp1.factcheck_stages import Experiment, request_for


@pytest.mark.parametrize("protocol,prior", [("v8-development", 95), ("v8.1-development", 92)])
def test_revision_cannot_reuse_previous_allocation(bundle, protocol, prior):
    experiment, _ = bundle
    data = experiment.model_dump()
    data.update(protocol=protocol, prior_starts=prior)
    with pytest.raises(ValueError, match="prior request count"):
        Experiment.model_validate(data)


def test_v81_checklist_includes_every_passage_not_source_metadata(bundle):
    experiment, _ = bundle
    data = experiment.model_dump()
    data.update(protocol="v8.1-development", prior_starts=95)
    revised = Experiment.model_validate(data)
    case = revised.cases[0]
    before = request_for(experiment, experiment.cases[0], "facts", None)
    after = request_for(revised, case, "facts", None)
    marker = "\n\nApplication reference and coverage lists:\n"
    instructions = json.loads(after["messages"][0]["content"].split(marker)[1])
    assert set(instructions["required_candidate_ids"]) == {
        key for key in case.content["passage_index"] if key.startswith("C.")
    }
    assert instructions["allowed_task_refs"] == ["R.task"]
    assert instructions["allowed_primary_source_refs"] == ["R.fact.0"]
    assert "synthetic-reader" not in str(instructions)
    assert before["messages"][1] == after["messages"][1]
    assert before["response_schema"] == after["response_schema"]
    assert request_for(experiment, experiment.cases[0], "control", None) == request_for(
        revised, case, "control", None
    )
