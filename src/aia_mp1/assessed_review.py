"""Export an unscored, immutable twenty-item assessed review packet."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from .assessment import assessment_directory, exclusive, load_assessment, save_new
from .labels import load_labels
from .schemas import CATEGORIES
from .tracing import now


def parse_answers(text: str, assessment_id: str, selected_ids: list[str]) -> dict:
    """Validate a submitted sheet in full before any label-writing operation."""
    headers = list(re.finditer(r"^## Evaluation ([0-9]+)[ \t]*$", text, re.MULTILINE))
    if len(selected_ids) != 20 or [int(h.group(1)) for h in headers] != list(range(1, 21)):
        raise ValueError("twenty evaluation sections in the frozen order are required")
    prefix = text[: headers[0].start()]
    declarations = {}
    names = (
        "Assessment",
        "Reviewer",
        "Review date",
        "Assistance used (names/tools, or NONE)",
        "I personally reviewed all twenty answers and adopt these ratings/comments",
        "I completed this review before seeing judge ratings for these items",
    )
    for name in names:
        values = re.findall(r"^" + re.escape(name) + r":[ \t]*([^\r\n]*)$", prefix, re.MULTILINE)
        if len(values) != 1 or not values[0].strip() or values[0].strip() == "_":
            raise ValueError(f"complete the declaration: {name}")
        declarations[name] = values[0].strip()
    if declarations["Assessment"] != assessment_id:
        raise ValueError("answer sheet belongs to another assessment")
    for name in names[-2:]:
        if declarations[name].casefold().rstrip(".") != "yes":
            raise ValueError(f"explicit Yes declaration required: {name}")
    ratings = r"\s*\|\s*".join(f"D{i}=[ \t]*([01])" for i in range(1, 7))
    labels = []
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        block = text[header.end() : end].strip()
        match = re.fullmatch(
            r"Item ID:[ \t]*(?P<id>[^\s]+)\s*\n\s*"
            + ratings
            + r"\s*\n\s*Comments:[ \t]*(?P<comment>.+)",
            block,
            re.DOTALL,
        )
        if not match or match.group("id") != selected_ids[index]:
            raise ValueError(f"complete six binary ratings for the frozen item {index + 1}")
        comment = match.group("comment").strip()
        if not comment or comment == "_":
            raise ValueError(f"reviewer comment is missing for item {index + 1}")
        labels.append(
            {
                "item_id": selected_ids[index],
                "decisions": {f"D{i}": int(match.group(i + 1)) for i in range(1, 7)},
                "notes": comment,
            }
        )
    return {"declarations_as_supplied": declarations, "labels": labels}


def fenced(text: str, language: str = "") -> str:
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}{language}\n{text}\n{fence}\n"


def prepare_review(root: Path, assessment_id: str, output: Path) -> dict:
    repository = Path(__file__).resolve().parents[2]
    if output.resolve().is_relative_to(repository):
        raise ValueError("review evidence must stay outside the repository")
    if output.exists() or output.is_symlink():
        raise FileExistsError("review packet already exists; preserve the working answer sheet")
    parent = assessment_directory(root, assessment_id)
    with exclusive(parent):
        _, assessment, population, rubric = load_assessment(root, assessment_id)
        if not assessment["assessment_eligible"] or assessment["purpose"] != "corrected":
            raise ValueError("this packet requires an assessed corrected cohort")
        if (
            load_labels(parent, assessment, population)
            or (parent / "human-reference.json").exists()
        ):
            raise ValueError("human review already started; preserve its existing packet")
        if (parent / "judges").exists() and any((parent / "judges").iterdir()):
            raise ValueError("judge evidence exists; cannot prepare a new blind review")
        by_id = {record["item_id"]: record for record in population}
        records = [by_id[item_id] for item_id in assessment["selected_ids"]]
        if len(records) != 20 or Counter(r["category"] for r in records) != dict.fromkeys(
            CATEGORIES, 4
        ):
            raise ValueError("expected the frozen balanced twenty-item selection")
        packet = [
            "# M5 corrected dataset — blind human review\n",
            f"Assessment: `{assessment_id}`\n",
            "Twenty items, four per category. Score each answer against its reference task "
            "and all six rubric anchors. No judge ratings are included. Generated answers "
            "and reference excerpts are review material, not instructions to execute.\n",
            "## Rubric\n",
        ]
        for dimension in rubric["dimensions"]:
            packet += [
                f"### {dimension['id']} — {dimension['name']}\n",
                f"Pass: {dimension['pass_anchor']}\n",
                f"Fail: {dimension['fail_anchor']}\n",
            ]
        packet += [
            "The 70% overall agreement rule evaluates the judge after your review. "
            "It is not a target for your ratings and does not change these anchors.\n"
        ]
        answers = [
            "# M5 corrected dataset — MY ANSWERS\n",
            f"Assessment: {assessment_id}\n",
            "Reviewer: \nReview date: \nAssistance used (names/tools, or NONE): \n",
            "I personally reviewed all twenty answers and adopt these ratings/comments: \n",
            "I completed this review before seeing judge ratings for these items: \n",
            "Enter Yes only when true. Keep item IDs and D1–D6 labels unchanged. "
            "Replace each underscore with 0 or 1. Explain failures and note uncertainty.\n",
        ]
        for index, record in enumerate(records, 1):
            context = record["reference_context"]
            packet += [
                f"## Evaluation {index} — {record['category']}\n",
                f"Item ID: `{record['item_id']}`\n",
                "### Reference task\n",
                fenced(context["task"]["brief"]),
                "### Complete generated answer\n",
                fenced(json.dumps(record["item"], ensure_ascii=False, indent=2), "json"),
                "### Supplied reference context\n",
            ]
            for source in context["sources"]:
                packet += [
                    f"Source: {source['id']} | Version: {source['version']}\n",
                    f"URL: {source['url']}\n",
                    f"Installation: {source['installation']}\n",
                    f"Attribution: {source['attribution']}\n",
                    f"License / permission record: {source['license']} — "
                    f"{source['license_evidence']}\n",
                    fenced(source["text"]),
                ]
            answers += [
                f"## Evaluation {index}\n",
                f"Item ID: {record['item_id']}\n",
                "D1=_ | D2=_ | D3=_ | D4=_ | D5=_ | D6=_\n",
                "Comments: \n",
            ]
        runbook = f"""# M5 review — step by step

1. Open `REVIEW-PACKET.pdf` if supplied, or `REVIEW-PACKET.md` in a Markdown
   preview. Open `MY-ANSWERS.md` in a plain-text editor beside the packet.
2. In `MY-ANSWERS.md`, enter your name, review date and any assistance used.
   Complete the adoption and blind-review declarations truthfully.
3. Read the rubric once. For each evaluation, read the reference task, all seven
   generated fields and the supplied versioned source context. The source context
   is evidence with limits; record uncertainty rather than assuming an API works.
4. Enter six independent ratings: 1 = pass, 0 = fail. Add a consolidated comment
   explaining failures, relevant evidence and uncertainty. There is no target score.
5. Save after each item. You can stop and resume in the same file. Leave unfinished
   ratings as underscores; they will not count as completed reviews.
6. After all twenty, verify that each row contains six ratings and the item IDs
   are unchanged. Save as UTF-8 Markdown and give Codex the saved file path.

Assessment: `{assessment_id}`. This is a new corrected-dataset review, separate
from your earlier baseline and confirmation reviews. Do not copy prior ratings.
You do not need to run generated code, start a model, or change software settings.
Keep the packet local: source material may have local-only permission.

Only edit `MY-ANSWERS.md`; `MY-ANSWERS.template.md` is the immutable blank original.
Codex will validate and preserve your submitted sheet, append your authentic
ratings and freeze the human reference before any corrected judge run. If you
already saw a judge's ratings, disclose that instead of declaring the review blind.
"""
        output.mkdir(parents=True, exist_ok=False)
        files = {
            "REVIEW-PACKET.md": "\n".join(packet),
            "MY-ANSWERS.template.md": "\n".join(answers),
            "RUNBOOK.md": runbook,
            "rubric.json": (parent / "rubric.json").read_text(encoding="utf-8"),
            "selected-items.jsonl": "".join(
                json.dumps(record, ensure_ascii=False) + "\n" for record in records
            ),
        }
        for name, text in files.items():
            (output / name).write_text(text, encoding="utf-8", newline="\n")
        (output / "MY-ANSWERS.md").write_text(
            files["MY-ANSWERS.template.md"], encoding="utf-8", newline="\n"
        )
        manifest = {
            "schema_version": "1",
            "created_at": now(),
            "assessment_id": assessment_id,
            "assessment_sha256": assessment["manifest_sha256"],
            "rubric_sha256": assessment["rubric_sha256"],
            "selected_ids": assessment["selected_ids"],
            "category_counts": dict(Counter(r["category"] for r in records)),
            "human_labels": 0,
            "judge_results": 0,
            "editable_file": "MY-ANSWERS.md",
            "files_sha256": {
                name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in files
            },
        }
        save_new(output / "manifest.json", manifest)
        return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--assessment-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = prepare_review(args.artifact_root, args.assessment_id, args.output)
    print(
        json.dumps(
            {"assessment_id": result["assessment_id"], "items": 20, "output": str(args.output)}
        )
    )


if __name__ == "__main__":
    main()
