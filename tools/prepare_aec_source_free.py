"""Prepare local AEC comparison inputs containing only the rubric, task and candidate."""

import json
import re

from prepare_aec_api_evaluation import ROOT, prepare
from prepare_aec_development_review import REVIEW, prepare_review
from run_aec_development import pin

from aia_mp1.analysis import file_hash
from aia_mp1.assessment import exclusive, load_assessment, read_json, read_text, save_new
from aia_mp1.frontier_inputs import paired_messages, validate_paired_message
from aia_mp1.tracing import digest


def phrases(text):
    words = re.findall(r"[\w@.]+", text.casefold())
    return {tuple(words[i : i + 15]) for i in range(len(words) - 14)}


def build(root):
    packet, baseline = prepare(root, "v3")
    selected = prepare_review(root)["selected_ids"]
    _, _, development, rubric = load_assessment(root, REVIEW)
    _, _, records, _ = load_assessment(root, baseline["source_assessment"])
    if rubric != read_json(packet / "rubric.json"):
        raise ValueError("Development and assessed rubrics differ")
    cases = {r["item_id"]: r for r in development}
    groups = {"development": [cases[k] for k in selected], "baseline": records}
    if len(records) != 50 or len(selected) != 10 or set(selected) & {r["item_id"] for r in records}:
        raise ValueError("Expected ten disjoint development answers and fifty assessed answers")
    prompt = (packet / "prompt.md").read_text(encoding="utf-8").strip() + (
        "\n\nThis comparison supplies only the authored task and candidate. "
        "Evaluate the written answer using the rubric. Do not cite unseen documentation or claim execution."
    )
    out = root / "api-source-free-preparation-001"
    out.mkdir(exist_ok=True)
    with exclusive(out):
        fingerprints = {}
        for name, items in groups.items():
            rows = []
            for record in items:
                row = paired_messages(prompt, rubric, record)
                validate_paired_message(row, prompt, rubric)
                body = json.loads(row["messages"][1]["content"])
                values = [record["reference_context"]["task"]["brief"]]
                for value in body["untrusted_item"].values():
                    values.extend(value if isinstance(value, list) else [value])
                sent_phrases = set().union(*(phrases(v) for v in values))
                for source in record["reference_context"]["sources"]:
                    if sent_phrases & phrases(source["text"]):
                        raise ValueError("Task or answer repeats a fifteen-word source passage")
                rows.append(row)
            path = out / f"{name}-requests.json"
            if not path.exists():
                save_new(path, rows)
            if json.loads(read_text(path)) != rows:
                raise ValueError("Frozen source-free requests differ")
            fingerprints[name] = {"count": len(rows), "file_sha256": file_hash(path)}
        manifest = {
            "purpose": "Offline preparation. Contains no inference dispatch capability.",
            "inputs": fingerprints,
            "rubric_sha256": digest(rubric),
            "prompt_sha256": digest(prompt),
            "source_check": "Allowlisted task and candidate fields. No 15-word contiguous overlap with each item's local source summaries.",
            "assessed_reference_sha256": baseline["source_references"][
                baseline["source_assessment"]
            ],
            "development_reference": file_hash(
                root / "api-development-comparison-001/review-checkpoint.json"
            ),
        }
        return pin(out / "manifest.json", manifest)


if __name__ == "__main__":
    print(json.dumps(build(ROOT.resolve()), indent=2))
