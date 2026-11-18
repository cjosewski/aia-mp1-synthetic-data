"""Synthetic export boundary tests; no authentic source excerpt is exported."""

from copy import deepcopy

import pytest

from aia_mp1.evaluation_schemas import DIMENSIONS
from aia_mp1.frontier_inputs import paired_messages, validate_paired_message
from aia_mp1.schemas import CATEGORIES

RUBRIC = {
    "version": "synthetic",
    "adaptation_source": "PRIVATE_RUBRIC_URL_SENTINEL",
    "dimensions": [
        {
            "id": dimension,
            "name": dimension,
            "pass_anchor": "Synthetic pass anchor.",
            "fail_anchor": "Synthetic fail anchor.",
            "adaptation_source": "PRIVATE_RUBRIC_URL_SENTINEL",
        }
        for dimension in DIMENSIONS
    ],
}


@pytest.fixture
def synthetic_record():
    category = CATEGORIES[0]
    return {
        "item_id": "synthetic-001",
        "category": category,
        "item": {
            "question": "How do I inspect a synthetic object?",
            "answer": "Create the object, inspect it, then report the result.",
            "equipment_problem": "Synthetic object inspection",
            "tools_required": ["SyntheticTool"],
            "steps": ["Create the object", "Inspect the object", "Report the result"],
            "safety_info": "Use a disposable object to avoid altering saved work.",
            "tips": ["Check the returned status before reporting success."],
        },
        "reference_context": {
            "task": {
                "id": "synthetic-task",
                "brief": "Inspect a disposable synthetic object.",
                "category": category,
                "source_refs": ["private-source"],
            },
            "sources": [
                {
                    "id": "private-source",
                    "excerpt": "LOCAL_ONLY_EXCERPT_SENTINEL",
                    "export_permission": "local_only",
                }
            ],
        },
    }


def test_paired_wire_excludes_local_source_and_labels(synthetic_record):
    prompt, rubric = "Synthetic judge prompt", RUBRIC
    result = paired_messages(prompt, rubric, synthetic_record)
    wire = str(result["messages"])
    assert "LOCAL_ONLY_EXCERPT_SENTINEL" not in wire
    assert "private-source" not in wire
    assert "PRIVATE_RUBRIC_URL_SENTINEL" not in wire
    assert "human" not in result
    assert result["category"] == synthetic_record["category"]
    validate_paired_message(result, prompt, rubric)


@pytest.mark.parametrize("attack", ["permission", "category", "source_key", "prompt", "hash"])
def test_source_and_wire_tampering_fails(synthetic_record, attack):
    prompt, rubric = "Synthetic judge prompt", RUBRIC
    record = deepcopy(synthetic_record)
    if attack == "permission":
        record["reference_context"]["sources"][0]["export_permission"] = "unknown"
        with pytest.raises(ValueError):
            paired_messages(prompt, rubric, record)
        return
    if attack == "category":
        record["reference_context"]["task"]["category"] = CATEGORIES[1]
        with pytest.raises(ValueError):
            paired_messages(prompt, rubric, record)
        return
    result = paired_messages(prompt, rubric, record)
    if attack == "source_key":
        import json

        body = json.loads(result["messages"][1]["content"])
        body["untrusted_reference_context"]["sources"] = ["LOCAL_ONLY_EXCERPT_SENTINEL"]
        result["messages"][1]["content"] = json.dumps(body)
    elif attack == "prompt":
        result["messages"][0]["content"] = "Changed judge prompt"
    else:
        result["messages_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        validate_paired_message(result, prompt, rubric)
