"""Reproduce the predeclared six-dimensional Qwen development comparison offline."""

import argparse
import json

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from review_aec_qwen_control import run as review_control
from review_aec_qwen_examples import DIRECTORY as EXAMPLES
from review_aec_qwen_examples import run as review_examples
from review_aec_technical import DIRECTORY as TECHNICAL
from review_aec_technical import run as review_technical
from run_aec_development import DIRECTORY as CONTROL
from run_aec_development import freeze_development_labels, pin

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.calibration import agreement


def assemble(root, stage):
    directory = root / TECHNICAL
    plan = directory / "composite-plan.json"
    if stage == "replay" and not plan.is_file():
        raise ValueError("Replaying the comparison requires its recorded composite plan")
    for verify in (review_control, review_examples, review_technical):
        verify(root, stage)
    mapping = {
        "D1": EXAMPLES,
        "D2": EXAMPLES,
        "D3": TECHNICAL,
        "D4": CONTROL,
        "D5": TECHNICAL,
        "D6": TECHNICAL,
    }
    parent, assessment, records, _ = load_assessment(root, REVIEW)
    ids = assessment["selected_ids"]
    with exclusive(directory):
        pin(
            plan,
            {
                "development_only": True,
                "mapping": mapping,
                "protocols": {
                    v: file_hash(root / v / "protocol.json") for v in set(mapping.values())
                },
                "minimum_matches_per_dimension": 8,
                "require_all_ten_and_explanation_audit": True,
                "rule": "Use the same predeclared stages on all ten cases. Retain the original v3 D4. Results determine whether to advance the entire method; do not substitute the highest scoring stage per case or dimension.",
            },
        )
        if stage == "prepare":
            return {"cases": len(ids), "method": mapping}
        labels = freeze_development_labels(directory, parent, assessment, records)
        scores = {}
        for k in ids:
            technical = read_json(directory / "technical" / k / "return.json")["parsed"]
            original = read_json(root / CONTROL / "control" / k / "return.json")["parsed"]
            scores[k] = {**technical, "D4": original["D4"]}
            for d in ("D1", "D2"):
                scores[k][d] = read_json(root / EXAMPLES / d / k / "return.json")["parsed"]
        result = agreement([r for r in records if r["item_id"] in ids], ids, labels, scores)
        pin(
            directory / "composite-report.json",
            {
                "development_only": True,
                "summary": result,
                "source_reports": {
                    name: file_hash(root / name / file)
                    for name, file in (
                        (EXAMPLES, "report.json"),
                        (TECHNICAL, "report.json"),
                        (CONTROL, "control-report.json"),
                    )
                },
                "plan_sha256": file_hash(plan),
            },
        )
        return {
            "coverage_complete": result["coverage_complete"],
            "matches": {d: v["matching"] for d, v in result["dimensions"].items()},
            "sha256": file_hash(directory / "composite-report.json"),
        }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("prepare", "replay"))
    print(json.dumps(assemble(ROOT.resolve(), p.parse_args().stage), indent=2))
