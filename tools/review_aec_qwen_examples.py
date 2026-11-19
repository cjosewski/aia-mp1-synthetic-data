"""Add five out-of-task human demonstrations to the frozen Qwen second review."""

import argparse
import itertools
import json
from pathlib import Path

from prepare_aec_api_evaluation import ROOT
from prepare_aec_development_review import REVIEW
from review_aec_qwen_control import DIRECTORY as PREVIOUS
from review_aec_qwen_control import FOCUS, Review
from run_aec_development import DIRECTORY as CONTROL
from run_aec_development import STAGES, capture, freeze_development_labels, pin
from screen_aec_devstral import verify_service
from screen_aec_local_model import SCREEN_MODEL

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json
from aia_mp1.calibration import agreement
from aia_mp1.canonical_development import QWEN_FILES, QWEN_MODEL_SHA
from aia_mp1.judge import JudgeConfig

DIRECTORY = "api-development-qwen-grounded-examples-001"


def demonstrations(target, training, dim):
    """Select using only eligible training examples and their labels."""
    groups = {}
    task = target["untrusted_reference_context"]["task"]
    for key, (case, ratings) in sorted(training.items()):
        other = case["untrusted_reference_context"]["task"]
        if other["id"] == task["id"] or case["untrusted_item"] == target["untrusted_item"]:
            continue
        groups.setdefault(other["category"], []).append((key, case, ratings[dim]))
    if len(groups) != 5:
        raise ValueError("A disjoint example is required from each specialty")

    # Prefer a balanced mix of the two binary grades, then stable item IDs.
    def rank(combo):
        return (
            abs(2 * sum(grade for _, _, grade in combo) - len(combo)),
            tuple(k for k, _, _ in combo),
        )

    chosen = min(itertools.product(*(groups[c] for c in sorted(groups))), key=rank)
    examples = []
    for _, case, grade in chosen:
        item = case["untrusted_item"]
        examples.append(
            {
                "task": case["untrusted_reference_context"]["task"]["brief"],
                "candidate" if dim == "D1" else "safety_info": item
                if dim == "D1"
                else item["safety_info"],
                "human_decision_for_this_example": grade,
            }
        )
    return [k for k, _, _ in chosen], examples


def run(root, stage):
    previous = root / PREVIOUS
    parent, assessment, records, _ = load_assessment(root, REVIEW)
    ids = assessment["selected_ids"]
    protocol = read_json(previous / "protocol.json")
    if (
        ids != protocol["case_ids"]
        or file_hash(previous / "requests.json") != protocol["requests_sha256"]
    ):
        raise ValueError("Earlier second-review inputs differ")
    packets = read_json(previous / "requests.json")
    originals = read_json(root / SCREEN_MODEL / "requests.json")
    cases = {k: json.loads(m[1]["content"]) for k, m in originals.items()}
    cfg = JudgeConfig.model_validate(read_json(root / "judge-preparation-v1/judge.json"))
    if cfg.public_settings() != protocol["settings"] or cfg.model_sha256 != QWEN_MODEL_SHA:
        raise ValueError("Earlier judge settings differ")
    directory = root / DIRECTORY
    directory.mkdir(exist_ok=True)
    with exclusive(directory):
        labels = freeze_development_labels(directory, parent, assessment, records)
        if file_hash(directory / "review-checkpoint.json") != protocol["human_reference"]:
            raise ValueError("Human reference differs")
        requests, selection = {}, {}
        for dim in FOCUS:
            selection[dim] = {}
            requests[dim] = {}
            for k in ids:
                training = {j: (cases[j], labels[j]["decisions"]) for j in ids if j != k}
                chosen, examples = demonstrations(cases[k], training, dim)
                selection[dim][k] = chosen
                before = packets[dim][k]
                prefix = "Use these five independently rated examples to interpret the named rubric. Each example's grade applies only to that example.\n"
                requests[dim][k] = [
                    before[0]
                    | {
                        "content": before[0]["content"]
                        + "\n\n"
                        + prefix
                        + json.dumps(examples, ensure_ascii=False)
                    },
                    before[1],
                ]
        pin(directory / "requests.json", requests)
        pin(
            directory / "protocol.json",
            {
                "development_only": True,
                "case_ids": ids,
                "examples": selection,
                "reference": protocol["human_reference"],
                "settings": cfg.public_settings(),
                "parent_protocol_sha256": file_hash(previous / "protocol.json"),
                "requests_sha256": file_hash(directory / "requests.json"),
                "code_sha256": file_hash(Path("tools/review_aec_qwen_examples.py")),
                "service_check_sha256": file_hash(Path("tools/screen_aec_devstral.py")),
                "max_starts": 20,
                "rule": "One example per specialty, selected without access to the target's grade. Exclude identical tasks and candidate payloads. One second review each on D1 and D2, retain v3 decisions for D3-D6. All ten valid and at least 8/10 on each dimension plus explanation audit.",
            },
        )
        if stage == "prepare":
            return {"requests": sum(map(len, requests.values())), "examples_per_request": 5}
        deployment = read_json(directory / "deployment.json")
        if deployment["parts"] != QWEN_FILES or deployment["reasoning_budget"] != 4096:
            raise ValueError("Different Qwen deployment")
        if stage == "score":
            verify_service(
                directory,
                cfg,
                {f"{d}.{k}": m for d, b in requests.items() for k, m in b.items()},
                QWEN_FILES,
            )
        results = {
            k: capture(
                root / CONTROL, k, "control", originals[k], cfg, replay_only=True
            ).model_dump()
            for k in ids
        }
        changes = {d: {"fixed": 0, "broken": 0} for d in FOCUS}
        returns = {}
        for dim in FOCUS:
            STAGES[dim] = Review
            for k, m in requests[dim].items():
                prev = capture(previous, k, dim, packets[dim][k], cfg, replay_only=True)
                new = capture(directory, k, dim, m, cfg, replay_only=stage == "replay")
                if new.decision != prev.decision:
                    changes[dim][
                        "fixed" if labels[k]["decisions"][dim] == new.decision else "broken"
                    ] += 1
                results[k][dim] = new.model_dump()
                returns[f"{dim}.{k}"] = file_hash(directory / dim / k / "return.json")
        summary = agreement([r for r in records if r["item_id"] in ids], ids, labels, results)
        pin(
            directory / "report.json",
            {
                "development_only": True,
                "summary": summary,
                "paired_vs_second_review": changes,
                "returns": returns,
                "parent_report_sha256": file_hash(previous / "report.json"),
                "protocol_sha256": file_hash(directory / "protocol.json"),
                "deployment_sha256": file_hash(directory / "deployment.json"),
                "token_fit_sha256": file_hash(directory / "token-fit.json"),
            },
        )
        return {
            "matches": {d: v["matching"] for d, v in summary["dimensions"].items()},
            "paired": changes,
        }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("prepare", "score", "replay"))
    print(json.dumps(run(ROOT.resolve(), p.parse_args().stage), indent=2))
