"""Compare the common v3 judge with one version-specific review checklist per request."""

import argparse
import json
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from run_aec_development import capture, freeze_development_labels, pin
from screen_aec_devstral import DIRECTORY as CONTROL
from screen_aec_devstral import run as replay_control
from screen_aec_devstral import verify_service
from screen_aec_local_model import SCREEN_MODEL

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.calibration import agreement
from aia_mp1.judge import JudgeConfig

DIRECTORY = "api-development-devstral-specialty-001"
PACK_SHA = "878854bc28a977256d203b16966ce5c1b334ba655622b0c7a5ddceb77be6e341"

# These review questions follow the five source profiles approved on November 10.
# They are shared by every task using a profile and contain no example decisions.
CHECKLISTS = {
    "aec-revit-2025": "Trace the document, collector, element, parameter and value as distinct objects. Check which object owns each member, the element selection, the parameter's storage type and the units of a returned value. For a change, verify that the correct element can be edited and the transaction reaches its claimed outcome. For a read, verify that the proposed operation can actually produce the requested report.",
    "gis-arcpy-3r0": "Trace the workspace, dataset path, schema, rows and cursor as distinct objects. Check that every selected field exists at the time of the read, that tuple positions correspond to the supplied field list and that resources are released before any conflicting operation. For geometry or geoprocessing, check coordinate system, units, argument types and the returned object against the requested result.",
    "struct-openseespy": "Trace the Python calls from model definition through nodes, constraints, materials, elements, loading, analysis and response extraction as applicable. Check dimensions, degrees of freedom, tags, units, argument counts, ordering and return conventions. Distinguish the reference load, its time-dependent factor and the response requested. Check that the proposed model can demonstrate the claimed comparison.",
    "cad-freecad-102": "Trace the document feature, editable properties, linked inputs, recomputation and resulting geometry. Check which object owns each operation and whether a later read would see the updated state. For a Boolean operation verify operand roles. For a measurement identify the quantity, units and an independent check suited to the requested shape.",
    "sim-scipy-1161": "Write down the mathematical problem implied by the candidate's RHS, state order, parameters, initial condition and interval. Compare it with the brief. Check function signatures and array shapes. Distinguish solver steps, output sampling, event detection and termination. Identify what numerical or analytical comparison actually establishes the claimed result.",
}


def specialize(messages, sources):
    context = json.loads(messages[1]["content"])["untrusted_reference_context"]
    (source,) = context["sources"]
    key = source["id"]
    if source != sources[key] or context["task"]["source_refs"] != [key]:
        raise ValueError("Request does not match a single approved versioned source")
    instruction = (
        f"\n\nSpecialty review for {source['version']}. {CHECKLISTS[key]} "
        "Apply the relevant checks to the obligations in this brief. Other possible operations in this specialty are outside the requested task. Use the six supplied rubric dimensions for the decisions."
    )
    return [messages[0] | {"content": messages[0]["content"] + instruction}, *messages[1:]]


def run(root, stage):
    baseline = root / CONTROL
    replay_control(root, "replay")
    protocol = read_json(baseline / "protocol.json")
    pack = root.parent / "references/engineering-v1.json"
    if file_hash(pack) != PACK_SHA:
        raise ValueError("Approved source pack changed")
    sources = {s["id"]: s for s in read_json(pack)["sources"]}
    inputs = read_json(root / SCREEN_MODEL / "requests.json")
    requests = {k: specialize(v, sources) for k, v in inputs.items()}
    parent, assessment, records, _ = load_assessment(root, REVIEW)
    ids = assessment["selected_ids"]
    selected = [r for r in records if r["item_id"] in ids]
    if set(requests) != set(ids) or len(ids) != 10:
        raise ValueError("Matched ten-case selection required")
    directory = root / DIRECTORY
    directory.mkdir(exist_ok=True)
    with exclusive(directory):
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(directory / "review-checkpoint.json") != protocol["human_reference"]:
            raise ValueError("Blind reference changed")
        pin(directory / "requests.json", requests)
        pin(
            directory / "protocol.json",
            {
                "development_only": True,
                "case_ids": ids,
                "model": protocol["model"],
                "advance_rule": protocol["advance_rule"],
                "attempts_per_case": 1,
                "max_starts": 10,
                "control_sha256": file_hash(baseline / "report.json"),
                "human_reference": protocol["human_reference"],
                "source_pack": PACK_SHA,
                "checklists": CHECKLISTS,
                "code_sha256": file_hash(Path("tools/screen_aec_specialty.py")),
                "requests_sha256": file_hash(directory / "requests.json"),
            },
        )
        if stage == "prepare":
            return {"cases": len(ids), "checklists": len(CHECKLISTS)}
        deployment = read_json(directory / "deployment.json")
        settings = {k: v for k, v in protocol["model"].items() if k != "authentication"}
        cfg = JudgeConfig.model_validate(
            read_json(root / "judge-preparation-v1/judge.json") | settings
        )
        if stage == "score":
            verify_service(
                directory, cfg, requests, read_json(baseline / "deployment.json")["parts"]
            )
        results = {}
        for key in ids:
            results[key] = capture(
                directory, key, "control", requests[key], cfg, replay_only=stage == "replay"
            ).model_dump()
        summary = agreement(selected, ids, labels, results)
        previous = read_json(baseline / "report.json")["summary"]

        def disagreements(s):
            return {(x["item_id"], x["dimension"]) for x in s["disagreements"]}

        before, after = disagreements(previous), disagreements(summary)
        changes = {
            d: {
                "fixed": sum(dim == d for _, dim in before - after),
                "broken": sum(dim == d for _, dim in after - before),
            }
            for d in summary["dimensions"]
        }
        segments = {}
        for category in sorted({r["category"] for r in selected}):
            keys = [r["item_id"] for r in selected if r["category"] == category]
            segments[category] = {
                "n": len(keys),
                "matches": {
                    d: sum((k, d) not in after for k in keys) for d in summary["dimensions"]
                },
            }
        pin(
            directory / "report.json",
            {
                "development_only": True,
                "summary": summary,
                "paired": changes,
                "specialties": segments,
                "deployment_sha256": file_hash(directory / "deployment.json"),
                "build": deployment["build"],
                "protocol_sha256": file_hash(directory / "protocol.json"),
                "token_fit_sha256": file_hash(directory / "token-fit.json"),
                "returns": {k: file_hash(directory / "control" / k / "return.json") for k in ids},
            },
        )
        return {
            "valid": len(results),
            "matches": {d: v["matching"] for d, v in summary["dimensions"].items()},
            "paired": changes,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "score", "replay"))
    print(json.dumps(run(ROOT.resolve(), parser.parse_args().stage), indent=2))
