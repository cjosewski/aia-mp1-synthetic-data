"""Validate and preserve authentic confirmation reviews; never create ratings."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from .assessment import read_json, read_text, save_new
from .evaluation_schemas import DIMENSIONS
from .judge import messages_for
from .schemas import CATEGORIES, QAItem
from .sources import load_pack
from .tracing import digest, now

ADOPTION = "I personally reviewed these ten answers and adopt the ratings/comments below"
BLIND = (
    "I completed this review before seeing either comparison model's judgments for these examples"
)
ASSISTANCE = "Assistance used (names/tools, or NONE)"


def byte_hash(path):
    if path.is_symlink():
        raise ValueError("symlink review evidence is not supported")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_packet(directory: Path, expected_manifest_sha256: str):
    """Pin the distributed manifest, then reconstruct every model message."""
    if byte_hash(directory / "manifest.json") != expected_manifest_sha256:
        raise ValueError("review packet manifest differs from the distributed identity")
    manifest = read_json(directory / "manifest.json")
    required = {
        "data.jsonl",
        "model-inputs.jsonl",
        "rubric.json",
        "source-pack.json",
        "judge-prompt.md",
    }
    if not required <= set(manifest["files_sha256"]):
        raise ValueError("review packet is missing required immutable files")
    for name, expected in manifest["files_sha256"].items():
        if Path(name).name != name or "\\" in name or name in {".", ".."}:
            raise ValueError("review packet filename must be a simple basename")
        if byte_hash(directory / name) != expected:
            raise ValueError(f"review packet file changed: {name}")
    records = [json.loads(line) for line in read_text(directory / "data.jsonl").splitlines()]
    inputs = [json.loads(line) for line in read_text(directory / "model-inputs.jsonl").splitlines()]
    pack = load_pack(directory / "source-pack.json")
    rubric = read_json(directory / "rubric.json")
    prompt = read_text(directory / "judge-prompt.md")
    sources = {source["id"]: source for source in pack["sources"]}
    ids = [record["item_id"] for record in records]
    if (
        len(ids) != 10
        or len(set(ids)) != 10
        or Counter(record["category"] for record in records) != dict.fromkeys(CATEGORIES, 2)
        or manifest["category_counts"] != dict.fromkeys(CATEGORIES, 2)
        or manifest["source_pack_sha256"] != digest(pack)
        or manifest["rubric_sha256"] != digest(rubric)
        or manifest["prompt_sha256"] != digest(prompt)
        or manifest["human_label_count"] != 0
        or manifest["model_requests"] != 0
    ):
        raise ValueError("confirmation packet identity, balance or preparation boundary differs")
    for record in records:
        QAItem.model_validate(record["item"])
        context = record["reference_context"]
        task = context["task"]
        if (
            record["assessment_eligible"] is not False
            or record["payload_sha256"] != digest(record["item"])
            or context["source_pack_sha256"] != digest(pack)
            or task["category"] != record["category"]
            or not task["source_refs"]
            or context["sources"] != [sources[ref] for ref in task["source_refs"]]
        ):
            raise ValueError("confirmation payload or source lineage differs")
    expected_inputs = [
        {"item_id": record["item_id"], "messages": messages_for(prompt, rubric, record)}
        for record in records
    ]
    if inputs != expected_inputs:
        raise ValueError("confirmation model messages differ from the reviewed inputs")
    return manifest, ids


def parse_answers(text: str, packet_id: str, ids: list[str]):
    """Read only explicitly entered decisions; incomplete or exposed reviews stop."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    headers = list(re.finditer(r"^## C(\d{2}) — ([^\s]+)\s*$", text, re.MULTILINE))
    if [match.group(2) for match in headers] != ids or [
        int(match.group(1)) for match in headers
    ] != list(range(1, 11)):
        raise ValueError("review must contain all ten original IDs once, in order")
    prefix = text[: headers[0].start()]
    fields = {}
    for name in ("Packet", "Reviewer", "Review date", ASSISTANCE, ADOPTION, BLIND):
        found = re.findall(r"^" + re.escape(name) + r":[ \t]*([^\r\n]*)$", prefix, re.MULTILINE)
        if len(found) != 1 or not found[0].strip() or "___" in found[0]:
            raise ValueError(f"review declaration is incomplete: {name}")
        fields[name] = found[0].strip()
    if fields["Packet"] != packet_id:
        raise ValueError("review belongs to another packet")
    for name in (ADOPTION, BLIND):
        if fields[name].casefold().rstrip(".") not in {"yes", "true", "confirmed", "i agree"}:
            raise ValueError(f"explicit affirmative declaration required: {name}")
    ratings_pattern = r"\s*\|\s*".join(d + r"\s*=\s*([01])" for d in DIMENSIONS)
    labels = []
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        block = text[header.end() : end].strip()
        match = re.fullmatch(ratings_pattern + r"\s*\n\s*Comment:\s*(.+)", block, re.DOTALL)
        if not match or "___" in match.group(7) or not match.group(7).strip():
            raise ValueError(f"six explicit binary ratings and a comment required: {ids[index]}")
        labels.append(
            {
                "item_id": ids[index],
                "decisions": {d: int(match.group(i + 1)) for i, d in enumerate(DIMENSIONS)},
                "comment": match.group(7).strip(),
            }
        )
    return {
        "reviewer": fields["Reviewer"],
        "review_date_as_supplied": fields["Review date"],
        "assistance_as_supplied": fields[ASSISTANCE],
        "adoption_as_supplied": fields[ADOPTION],
        "blind_declaration_as_supplied": fields[BLIND],
        "labels": labels,
    }


def freeze_review(packet: Path, manifest_sha256: str, answers: Path, destination: Path):
    manifest, ids = verify_packet(packet, manifest_sha256)
    if answers.is_symlink():
        raise ValueError("symlink answers are not supported")
    raw = answers.read_bytes()
    parsed = parse_answers(raw.decode("utf-8-sig"), manifest["packet_id"], ids)
    repository = Path(__file__).resolve().parents[2]
    if destination.resolve().is_relative_to(repository):
        raise ValueError("raw human evidence must stay outside the repository")
    destination.mkdir(parents=True, exist_ok=False)
    # Preserve partial writes for inspection; never replace an existing freeze.
    with (destination / "submitted-answers.md").open("xb") as stream:
        stream.write(raw)
    reference = {
        "schema_version": "1",
        "packet_id": manifest["packet_id"],
        "packet_manifest_sha256": manifest_sha256,
        "submitted_answers_sha256": hashlib.sha256(raw).hexdigest(),
        "created_at": now(),
        "assessment_eligible": False,
        "attribution_boundary": "Reviewer declarations retained; software does not authenticate authorship or absence of exposure.",
        **parsed,
    }
    reference["sha256"] = digest(reference)
    save_new(destination / "human-reference.json", reference)
    return reference


def load_review(packet: Path, manifest_sha256: str, directory: Path):
    manifest, ids = verify_packet(packet, manifest_sha256)
    reference = read_json(directory / "human-reference.json")
    raw_path = directory / "submitted-answers.md"
    parsed = parse_answers(read_text(raw_path).lstrip("\ufeff"), manifest["packet_id"], ids)
    if (
        reference["sha256"] != digest({k: v for k, v in reference.items() if k != "sha256"})
        or reference["packet_manifest_sha256"] != manifest_sha256
        or reference["packet_id"] != manifest["packet_id"]
        or reference["assessment_eligible"] is not False
        or reference["submitted_answers_sha256"] != byte_hash(raw_path)
        or any(reference[key] != value for key, value in parsed.items())
    ):
        raise ValueError("frozen confirmation review differs from the submitted record")
    return reference


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--freeze-to", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest, ids = verify_packet(args.packet, args.manifest_sha256)
        parse_answers(read_text(args.answers).lstrip("\ufeff"), manifest["packet_id"], ids)
        if args.freeze_to:
            freeze_review(args.packet, args.manifest_sha256, args.answers, args.freeze_to)
        print(
            "Ten complete attributed reviews verified"
            + (" and preserved." if args.freeze_to else ".")
        )
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Review not ready: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
