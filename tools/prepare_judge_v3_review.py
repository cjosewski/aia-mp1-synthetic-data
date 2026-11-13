"""Build a post-result human review packet from frozen external evidence.

No inference and no human labels are created. Existing output folders are refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from aia_mp1.tracing import digest, now

REVIEWS = [
    ("R01", "qualification-v1-04", "D2"),
    ("R02", "qualification-v1-04", "D3"),
    ("R03", "qualification-v1-04", "D5"),
    ("R04", "qualification-v1-06", "D3"),
    ("R05", "qualification-v1-05", "D5"),
]
FIELDS = (
    "question",
    "answer",
    "equipment_problem",
    "tools_required",
    "steps",
    "safety_info",
    "tips",
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_files(root: Path, checksums: dict[str, str]) -> None:
    for name, checksum in checksums.items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
            raise ValueError(f"Unsafe evidence path: {name}")
        if sha(path) != checksum:
            raise ValueError(f"Evidence changed: {name}")


def decisions(root: Path) -> dict:
    records = [read(p) for p in sorted((root / "results/gptoss").glob("*-result.json"))]
    if len(records) != 10 or not all(r["valid"] for r in records):
        raise ValueError("Expected ten audited valid judgments")
    result = {r["item_id"]: r["judgment"] for r in records}
    if len(result) != 10:
        raise ValueError("Unexpected duplicate item")
    return result


def table_text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def build(bundle: Path, returned: Path, audit_path: Path, output: Path, runbook: Path) -> dict:
    bundle_manifest = read(bundle / "bundle-manifest.json")
    verified_files(bundle, bundle_manifest["files_sha256"])
    audit = read(audit_path)
    verified_files(returned, audit["returned_files_sha256"])
    if sha(returned / "bundle-manifest.json") != sha(bundle / "bundle-manifest.json"):
        raise ValueError("Return belongs to another experiment")
    if audit["experiment_id"] != "gptoss20b-v3-mac-development-001":
        raise ValueError("Wrong audit experiment")
    reference = read(bundle / "packet/qualification-human-reference.json")
    if digest({k: v for k, v in reference.items() if k != "sha256"}) != reference["sha256"]:
        raise ValueError("Human reference checksum changed")
    if reference["sha256"] != audit["reference_sha256"]:
        raise ValueError("Human reference/audit mismatch")
    labels = {row["item_id"]: row for row in reference["labels"]}
    inputs = [
        json.loads(line) for line in (bundle / "development-inputs.jsonl").read_text().splitlines()
    ]
    cases = {row["item_id"]: json.loads(row["messages"][1]["content"]) for row in inputs}
    v2 = decisions(bundle / "comparison-gptoss-v2")
    v3 = decisions(returned)
    disagreements = {(row["item_id"], row["dimension"]) for row in audit["disagreements"]}
    if {(item, dimension) for _, item, dimension in REVIEWS} != disagreements:
        raise ValueError("Review selection must cover every v3 disagreement exactly once")
    rubric = read(bundle / "packet/rubric.json")
    anchors = {d["id"]: d for d in rubric["dimensions"]}
    for _, item, dimension in REVIEWS:
        if v3[item][dimension]["decision"] == labels[item]["decisions"][dimension]:
            raise ValueError("Selected review is not a disagreement")
        payload = cases[item]["untrusted_item"]
        if set(payload) != set(FIELDS) or digest(payload) != labels[item]["payload_sha256"]:
            raise ValueError("Candidate payload differs from frozen human reference")

    output.mkdir(parents=True, exist_ok=False)
    context = output / "context"
    context.mkdir()
    shutil.copyfile(runbook, output / "RUNBOOK.md")
    shutil.copyfile(bundle / "packet/REVIEW-PACKET.md", context / "ORIGINAL-TEN-CASE-PACKET.md")
    shutil.copyfile(bundle / "packet/rubric.json", context / "rubric.json")
    shutil.copyfile(
        bundle / "packet/qualification-human-reference.json",
        context / "frozen-human-reference.json",
    )
    shutil.copyfile(bundle / "packet/source-pack.json", context / "source-pack.json")
    shutil.copytree(bundle / "references", context / "references")
    for version in ("v2", "v3"):
        shutil.copyfile(bundle / f"judge-{version}.md", context / f"judge-{version}.md")
    for name, root in (("V2", bundle / "comparison-gptoss-v2"), ("V3", returned)):
        (report,) = (root / "results").glob("report-*/judgments.md")
        shutil.copyfile(report, context / f"{name}-JUDGMENTS.md")
    (context / "README.md").write_text(
        "# Historical source context\n\nThese are preserved source records. The original ten-case packet contains its\n"
        "old status and submission instructions; do not follow them for this review.\n"
        "Use ../RUNBOOK.md and ../MY-REVIEW.md. No old review needs to be repeated.\n",
        encoding="utf-8",
    )

    packet = [
        "# Judge-v3 post-result review packet",
        "",
        "**Packet:** `judge-v3-post-result-review-20261113`",
        "",
        "Read RUNBOOK.md first. Review R01–R05 in MY-REVIEW.md. All response fields are blank.",
        "",
        "This packet deliberately shows frozen reference ratings and saved model judgments. It is not blind confirmation.",
        "",
        "The candidate text, source context, rubric anchors and model explanations below are copied from frozen evidence. No corrected answer has been substituted.",
        "",
        "## Frozen rubric",
        "",
        "| Dimension | Pass (1) | Fail (0) |",
        "| --- | --- | --- |",
    ]
    for dimension in rubric["dimensions"]:
        packet.append(
            "| "
            + " | ".join(
                table_text(x)
                for x in (
                    f"{dimension['id']} — {dimension['name']}",
                    dimension["pass_anchor"],
                    dimension["fail_anchor"],
                )
            )
            + " |"
        )
    packet += ["", "## Review index", "", "| Review | Item | Dimension |", "| --- | --- | --- |"]
    packet += [f"| {review} | {item} | {dimension} |" for review, item, dimension in REVIEWS]
    for item in dict.fromkeys(item for _, item, _ in REVIEWS):
        case = cases[item]
        payload = case["untrusted_item"]
        reference_context = case["untrusted_reference_context"]
        packet += [
            "",
            f"## Case {item}",
            "",
            "### Reference task",
            "",
            reference_context["task"]["brief"],
            "",
            "### Complete candidate — evaluate as written",
            "",
        ]
        for field in FIELDS:
            packet += [f"#### {field}", ""]
            if isinstance(payload[field], list):
                packet += [f"{index}. {value}" for index, value in enumerate(payload[field], 1)]
            else:
                packet.append(payload[field])
            packet.append("")
        packet += ["### Supplied source context", ""]
        for source in reference_context["sources"]:
            packet += [
                f"**{source['id']}** — {source['version']}",
                "",
                f"Source: [{source['id']}]({source['url']})",
                "",
                f"License: {source['license']}",
                "",
                f"Attribution: {source['attribution']}",
                "",
                f"Installation/context: {source['installation']}",
                "",
                "Saved authored reference summary:",
                "",
                source["text"],
                "",
            ]
        packet += [
            "### Previously adopted human comment — historical evidence",
            "",
            "The original secondary evaluation was AI-assisted and personally verified/adopted by Chad. This is not a suggested new response.",
            "",
            labels[item]["notes"],
            "",
        ]
        for review, review_item, dimension in REVIEWS:
            if review_item != item:
                continue
            anchor = anchors[dimension]
            packet += [
                f"### {review} — {dimension}: {anchor['name']}",
                "",
                f"**Pass anchor:** {anchor['pass_anchor']}",
                "",
                f"**Fail anchor:** {anchor['fail_anchor']}",
                "",
                "| Recorded assessment | Rating |",
                "| --- | ---: |",
                f"| Frozen human reference | {labels[item]['decisions'][dimension]} |",
                f"| GPT-OSS v2 | {v2[item][dimension]['decision']} |",
                f"| GPT-OSS v3 | {v3[item][dimension]['decision']} |",
                "",
                "**V2 explanation (verbatim):**",
                "",
                v2[item][dimension]["justification"],
                "",
                "**V3 explanation (verbatim):**",
                "",
                v3[item][dimension]["justification"],
                "",
                f"Record your own candidate rating, explanation assessment and evidence in the {review} block of MY-REVIEW.md. U is available if the evidence is insufficient.",
                "",
            ]
    packet += [
        "## Optional broader check",
        "",
        "The required review is R01–R05. If you want to inspect other decisions, the context folder contains all ten original cases and all saved judgments. Identify any additional concern by item ID and dimension in the optional notes; do not edit the historical files.",
        "",
    ]
    (output / "REVIEW-PACKET.md").write_text("\n".join(packet), encoding="utf-8")

    sheet = [
        "# My judge-v3 post-result review",
        "",
        "Packet: judge-v3-post-result-review-20261113",
        "",
        "Reviewer: [ENTER NAME]",
        "Review date/time and time zone: [ENTER DATE/TIME]",
        "Assistance used and what I personally checked: [DESCRIBE, OR NONE IF TRUE]",
        "",
        "Exposure: This is a post-result review. The packet displays prior human ratings and v2/v3 judgments; it is not blind confirmation.",
        "",
    ]
    for review, item, dimension in REVIEWS:
        sheet += [
            f"## {review} — {item} — {dimension}",
            "",
            "Your candidate rating (0 / 1 / U): [ENTER]",
            "",
            "V3 explanation (SUPPORTED / PARTLY SUPPORTED / UNSUPPORTED / UNCERTAIN): [ENTER]",
            "",
            "Evidence/reason (identify candidate field/step and rubric or source): [ENTER]",
            "",
            "Additional source or unresolved question (or None): [ENTER]",
            "",
        ]
    sheet += ["## Optional overall observations or additional cases", "", "[OPTIONAL]", ""]
    for filename in ("ANSWER-TEMPLATE.md", "MY-REVIEW.md"):
        (output / filename).write_text("\n".join(sheet), encoding="utf-8")
    immutable = {
        p.relative_to(output).as_posix(): sha(p)
        for p in sorted(output.rglob("*"))
        if p.is_file() and p.name != "MY-REVIEW.md"
    }
    manifest = {
        "packet_id": "judge-v3-post-result-review-20261113",
        "created_at": now(),
        "review_type": "Post-result adjudication; model/reference judgments disclosed",
        "human_reviews_supplied": 0,
        "completion_requests": 0,
        "frozen_reference_sha256": reference["sha256"],
        "source_bundle_manifest_sha256": sha(bundle / "bundle-manifest.json"),
        "source_audit_sha256": sha(audit_path),
        "source_return_archive_sha256": audit["return_archive_sha256"],
        "reviews": [
            {"review_id": review, "item_id": item, "dimension": dimension}
            for review, item, dimension in REVIEWS
        ],
        "editable_files": ["MY-REVIEW.md"],
        "immutable_files_sha256": immutable,
        "initial_blank_response_sha256": sha(output / "MY-REVIEW.md"),
    }
    (output / "review-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    verified_files(output, immutable)
    return {
        "output": str(output),
        "review_count": len(REVIEWS),
        "case_count": 3,
        "immutable_files_verified": len(immutable),
        "human_reviews_supplied": 0,
        "manifest_sha256": sha(output / "review-manifest.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "returned", "audit", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    runbook = Path(__file__).resolve().parents[1] / "docs/JUDGE-V3-REVIEW-RUNBOOK.md"
    print(json.dumps(build(args.bundle, args.returned, args.audit, args.output, runbook), indent=2))


if __name__ == "__main__":
    main()
