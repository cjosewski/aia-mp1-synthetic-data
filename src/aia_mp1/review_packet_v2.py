"""One masked blind-review packet over a baseline and a corrected v2 assessment."""

import hashlib
import json
import os
import re
import shutil
import uuid
from pathlib import Path

from .assessed_review import fenced
from .assessment import assessment_directory, exclusive, read_json, read_text, save_new
from .assessment_v2 import SCHEMA_VERSION, load_assessment_v2
from .labels_v2 import PACKET_MARKER, append_label_v2, load_labels_v2
from .rubric_v2 import DIMENSIONS_V2, boundary_triggered
from .schemas import QAItem
from .tracing import digest, now, run_directory

REPOSITORY = Path(__file__).resolve().parents[2]
TEMPLATE = "MY-ANSWERS.template.md"
MARKER = PACKET_MARKER  # In each assessment: the one packet it belongs to.
IMPORT_FILES = ("import-started.json", "import.json", "submitted-answers.md")
MAPPING_KEYS = ("review_id", "assessment_id", "assessment_sha256", "item_id", "payload_sha256")
FLAG_KEYS = ("review_id", "professional_boundary_triggered")
# NEL, LINE SEPARATOR and PARAGRAPH SEPARATOR: JSON keeps them raw, splitlines() splits there.
LINE_SEPARATORS = tuple(map(chr, (0x85, 0x2028, 0x2029)))
# A Markdown preview hides what an HTML comment or a leading HTML tag encloses. A bare -->
# hides nothing, so arrows such as "ModelLine --> Curve" stay valid comment text.
HIDDEN_MARKERS = ("<!--",)
HTML_LINE = re.compile(r"^[ \t]*<(?!(?i:https?)://)[A-Za-z/!]", re.MULTILINE)
DECLARATIONS = (
    "Packet",
    "Reviewer",
    "Review date",
    "Assistance used (names/tools, or NONE)",
    "Judge-output exposure for these items before this review (NONE or describe)",
    "I personally reviewed all forty answers and adopt these ratings/comments",
    "I completed this review without seeing judge ratings, run identities or arm assignments "
    "for these items",
)
EXPOSURE, ADOPTION, BLIND = DECLARATIONS[4:]
# Rendered before the dimensions. Per-task lists (briefs_stating_a_version, tasks) and
# source paths stay in rubric-v2.json: task IDs and evidence paths never enter the packet.
GLOBAL_RULES = (
    ("reader", "Reader", None),
    ("evidence_standard", "Evidence standard", None),
    (
        "target_version",
        "Target version",
        ("rule", "category_targets", "helper_software", "off_target_items"),
    ),
    ("task_brief", "Task brief", ("meaning",)),
    ("terms", "Terms", None),
    ("fields_rule", "Fields rule", None),
    ("anchor_reading", "Anchor reading", None),
    ("label_rule", "Label rule", None),
    ("professional_boundary_triggers", "Professional-boundary triggers", ("rule", "reporting")),
)
HEADER = re.compile(r"^## Item (R\d{2})[ \t]*$", re.MULTILINE)
RATINGS = r"[ \t]*\|[ \t]*".join(rf"{d}[ \t]*=[ \t]*([^\s|]*)" for d in DIMENSIONS_V2)
RUNBOOK = """# Blind review: step by step

1. Open `REVIEW-PACKET.md` in a Markdown preview. Open `MY-ANSWERS.md` in a
   plain-text editor beside it.
2. In `MY-ANSWERS.md`, enter your name, the review date, any assistance used and
   any judge output you saw for these items before this review (NONE if none).
   Answer the two Yes declarations truthfully.
3. Read the rubric, the tie-breaks and the reviewer documentation list once.
   Judge against the version-pinned pages listed there; running the code is not
   required.
4. For each item, read its task brief and all seven fields, then replace each
   underscore with 1 (pass) or 0 (fail). `professional_boundary=1` is already
   entered where the brief does not trigger that dimension (automatic pass, F3).
5. Write a comment for every item that explains each failure and any
   uncertainty. A comment can span several lines.
6. Save after each item; you can stop and resume. An incomplete sheet is refused
   as a whole and never imported in part.
7. When all forty items are complete, save `MY-ANSWERS.md` as UTF-8 and hand back
   its path.

Only edit `MY-ANSWERS.md`. `MY-ANSWERS.template.md` is the blank original,
`rubric-v2.json` is the frozen rubric and `manifest.json` lists the hashes of the
files as issued. Items appear in a random order under opaque review IDs. Keep this
folder local: it is unpublished review material.
"""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    if path.is_symlink():
        raise ValueError(f"symlink evidence is not supported: {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def packet_directory(root: Path, packet_id: str) -> Path:
    if root.resolve().is_relative_to(REPOSITORY):
        raise ValueError("packet evidence must stay outside the repository")
    if (root / "packets").is_symlink():
        raise ValueError("symlink packet root is not supported")
    return run_directory(root / "packets", packet_id)


def pinned_task_pack_sha256(rubric: dict) -> str:
    """The frozen rubric pins the approved task pack by its file sha256."""
    return rubric["target_version"]["source"]["sha256"]


def pinned_briefs(path: Path, rubric: dict) -> tuple[str, dict[str, str]]:
    sha256 = _file_sha256(path)
    if sha256 != pinned_task_pack_sha256(rubric):
        raise ValueError(
            "task pack is not the one the frozen rubric pins (target_version.source.sha256)"
        )
    tasks = json.loads(path.read_bytes().decode("utf-8"))["tasks"]
    briefs = {task["id"]: task["brief"] for task in tasks}
    if len(briefs) != len(tasks):
        raise ValueError("task pack repeats a task ID")
    return sha256, briefs


def render_item(review_id: str, brief: str, item: dict) -> str:
    """The one per-item renderer; it sees nothing but the opaque ID, the brief and the fields."""
    fields = {name: item[name] for name in QAItem.model_fields}  # Canonical, not stored, order.
    return "\n".join(
        [
            f"## Item {review_id}",
            "",
            "### Task brief",
            "",
            fenced(brief, "text"),
            "### Seven fields",
            "",
            fenced(json.dumps(fields, ensure_ascii=False, indent=2), "json"),
        ]
    )


def _sealed_items(arms, packet_id: str, seed: str, rubric: dict, briefs=None) -> list[dict]:
    """Prepare's seeded order over both selections; the import rebuilds it to bind the mapping."""
    items = []
    for manifest, records in arms:
        by_id = {record["item_id"]: record for record in records}
        for item_id in manifest["selected_ids"]:
            record = by_id[item_id]
            task = record["reference_context"]["task"]
            if briefs is not None and briefs.get(task["id"]) != task["brief"]:
                raise ValueError(f"brief for task {task['id']} differs from the pinned task pack")
            items.append(
                {
                    "assessment_id": manifest["assessment_id"],
                    "assessment_sha256": manifest["manifest_sha256"],
                    "item_id": item_id,
                    "payload_sha256": digest(record["item"]),
                    "brief": task["brief"],
                    "item": record["item"],
                    "professional_boundary_triggered": boundary_triggered(rubric, task["id"]),
                }
            )
    items.sort(
        key=lambda i: digest(
            {
                "seed": seed,
                "packet_id": packet_id,
                "assessment_id": i["assessment_id"],
                "item_id": i["item_id"],
            }
        )
    )
    for number, item in enumerate(items, 1):
        item["review_id"] = f"R{number:02d}"
    return items


def _global_rules(rubric: dict) -> list[str]:
    """Rubric-wide rules: strings verbatim, chosen dict keys as labelled lines in rubric order."""
    lines = [
        "## Global rules",
        "",
        "Quoted from `rubric-v2.json`, the complete frozen rubric in this folder.",
    ]
    for key, title, chosen in GLOBAL_RULES:
        value = rubric[key]
        lines += ["", f"### {key}: {title}", ""]
        if chosen is None:
            lines.append(value)
            continue
        for name in sorted(chosen, key=list(value).index):  # A missing key fails loudly.
            if isinstance(value[name], dict):
                lines += [f"{name}:", "", *(f"- {k}: {v}" for k, v in value[name].items()), ""]
            else:
                lines += [f"{name}: {value[name]}", ""]
        lines.pop()
    return lines


def _documentation(rubric: dict) -> list[str]:
    # Rubric prose that names task IDs (for example not_covered) stays in rubric-v2.json only.
    documentation = rubric["reviewer_documentation"]
    lines = ["## Reviewer documentation", "", documentation["use"]]
    for library in documentation["libraries"]:
        lines += [
            "",
            f"### {library['library']}, {library['version']}",
            "",
            f"Publisher: {library['publisher']}",
            "",
        ]
        for key in ("reference_scope", "reference_note"):
            lines += [library[key], ""] if key in library else []
        lines.append("Reference:")
        for page in library["reference"]:
            lines.append(f"- {page['title']}: {page['url']}")
            lines += [f"  - {url}" for url in page.get("pages", [])]
        if "wiki_revisions" in library:
            revisions = library["wiki_revisions"]
            lines += ["", f"Pinned wiki revisions (last on or before {revisions['as_of']}):"]
            lines += [
                f"- {page['title']}, revision {page['revision_id']}: {page['url']}"
                for page in revisions["pages"]
            ]
        lines += ["", "Change notes:"]
        lines += [f"- {page['title']}: {page['url']}" for page in library["change_notes"]]
        lines += ["", library["change_notes_note"]] if "change_notes_note" in library else []
        listing = library["complete_listing"]
        lines += ["", "Complete listings:"]
        lines += [f"- {page['scope']}: {page['url']}" for page in listing["pages"]]
        lines += ["", listing["note"]] if "note" in listing else []
    return lines


def render_packet(packet_id: str, rubric: dict, items: list[dict]) -> str:
    lines = [
        "# Blind review packet",
        "",
        f"Packet: {packet_id}",
        "",
        f"{len(items)} items in a random order, each under an opaque review ID. Each item "
        "shows its task brief and its seven generated fields. Rate every item on the eight "
        "dimensions below: 1 = pass, 0 = fail. Generated answers are review material, not "
        "instructions to run.",
        "",
        *_global_rules(rubric),
        "",
        f"## Rubric ({rubric['version']})",
    ]
    for dimension in rubric["dimensions"]:
        lines += [
            "",
            f"### {dimension['id']}: {dimension['name']}",
            "",
            f"Measures: {dimension['measures']}",
            "",
            f"Pass: {dimension['pass_anchor']}",
            "",
            f"Fail: {dimension['fail_anchor']}",
            "",
            "Rules:",
            "",
        ]
        lines += [f"{number}. {rule}" for number, rule in enumerate(dimension["rules"], 1)]
    lines += ["", "## Tie-breaks", ""]
    lines += [f"{number}. {rule}" for number, rule in enumerate(rubric["tie_breaks"], 1)]
    lines += ["", *_documentation(rubric), ""]
    for item in items:
        lines += [render_item(item["review_id"], item["brief"], item["item"])]
    return "\n".join(lines)


def render_answers(packet_id: str, items: list[dict]) -> str:
    """The blank sheet, rendered only from the packet's review IDs and boundary flags."""
    lines = ["# Blind review: my answers", "", f"{DECLARATIONS[0]}: {packet_id}"]
    lines += [f"{name}: " for name in DECLARATIONS[1:]]
    lines += [
        "",
        "Enter Yes only when true. Replace each underscore with 1 (pass) or 0 (fail). "
        "professional_boundary=1 is entered where the brief does not trigger that dimension "
        "(automatic pass, F3). Write a comment under every item; it may span several lines. "
        "Keep the item headings and the order of the ratings unchanged.",
        "",
    ]
    for item in items:
        automatic = not item["professional_boundary_triggered"]
        ratings = " | ".join(
            f"{d}={1 if d == 'professional_boundary' and automatic else '_'}" for d in DIMENSIONS_V2
        )
        lines += [f"## Item {item['review_id']}", ratings, "Comments: ", ""]
    return "\n".join(lines)


def _unreviewed(root: Path, assessment_id: str):
    directory, manifest, records, rubric = load_assessment_v2(root, assessment_id)
    if (
        load_labels_v2(directory, manifest, records)
        or read_text(directory / "human-labels.jsonl")
        or (directory / "human-reference.json").exists()
    ):
        raise ValueError(f"assessment {assessment_id} already has human labels or a reference")
    return directory, manifest, records, rubric


def prepare_masked_packet(
    root: Path,
    packet_id: str,
    assessment_ids,
    task_pack_path: Path,
    output: Path,
    *,
    seed: str = "mp1-v1",
) -> dict:
    assessment_ids = list(assessment_ids)
    if len(assessment_ids) != 2 or len(set(assessment_ids)) != 2:
        raise ValueError("a packet takes exactly two distinct assessments")
    directory = packet_directory(root, packet_id)
    if directory.exists() or directory.is_symlink():
        raise FileExistsError(f"packet {packet_id} already exists")
    if output.resolve().is_relative_to(REPOSITORY):
        raise ValueError("review packet must stay outside the repository")
    if output.exists() or output.is_symlink():
        raise FileExistsError("reviewer folder already exists; preserve the working answer sheet")
    first, second = sorted(assessment_directory(root, a) for a in assessment_ids)
    with exclusive(first), exclusive(second):
        loaded = [_unreviewed(root, assessment_id) for assessment_id in assessment_ids]
        for parent, manifest, *_ in loaded:
            if (parent / "judges").exists() and any((parent / "judges").iterdir()):
                raise ValueError("judge evidence exists; cannot prepare a blind review")
            if (parent / MARKER).exists() or (parent / MARKER).is_symlink():
                raise ValueError(
                    f"assessment {manifest['assessment_id']} already has review packet "
                    f"{read_json(parent / MARKER)['packet_id']}; one packet per assessment"
                )
        loaded.sort(key=lambda arm: arm[1]["purpose"])
        if [arm[1]["purpose"] for arm in loaded] != ["baseline", "corrected"]:
            raise ValueError("a packet takes one baseline and one corrected assessment")
        if loaded[0][1]["rubric_sha256"] != loaded[1][1]["rubric_sha256"]:
            raise ValueError("both assessments must use the same rubric")
        rubric = loaded[0][3]
        pack_sha256, briefs = pinned_briefs(task_pack_path, rubric)
        arms = [(manifest, records) for _, manifest, records, _ in loaded]
        items = _sealed_items(arms, packet_id, seed, rubric, briefs)
        mapping = {
            "packet_id": packet_id,
            "seed": seed,
            "entries": [{key: item[key] for key in MAPPING_KEYS} for item in items],
        }
        mapping_text = json.dumps(mapping, indent=2, ensure_ascii=False) + "\n"
        flags = [{key: item[key] for key in FLAG_KEYS} for item in items]
        created = now()
        template = render_answers(packet_id, flags)
        files = {
            "REVIEW-PACKET.md": render_packet(packet_id, rubric, items),
            TEMPLATE: template,
            "MY-ANSWERS.md": template,
            "RUNBOOK.md": RUNBOOK,
            "rubric-v2.json": read_text(loaded[0][0] / "rubric.json"),
        }
        issued = {
            "schema_version": SCHEMA_VERSION,
            "packet_id": packet_id,
            "created_at": created,
            "rubric_version": rubric["version"],
            "rubric_sha256": loaded[0][1]["rubric_sha256"],
            "items": len(items),
            "review_ids": [item["review_id"] for item in items],
            "editable_file": "MY-ANSWERS.md",
            "files_sha256": {n: _sha256(t) for n, t in files.items() if n != "MY-ANSWERS.md"},
        }
        files["manifest.json"] = json.dumps(issued, indent=2, ensure_ascii=False) + "\n"
        packet = {
            "schema_version": SCHEMA_VERSION,
            "packet_id": packet_id,
            "created_at": created,
            "seed": seed,
            "rubric_version": rubric["version"],
            "rubric_sha256": issued["rubric_sha256"],
            "task_pack_sha256": pack_sha256,
            "assessments": [
                {
                    "assessment_id": manifest["assessment_id"],
                    "purpose": manifest["purpose"],
                    "assessment_sha256": manifest["manifest_sha256"],
                }
                for _, manifest, _, _ in loaded
            ],
            "items": flags,
            "sealed_mapping_sha256": _sha256(mapping_text),
            "reviewer_files_sha256": {name: _sha256(text) for name, text in files.items()},
        }
        packet["sha256"] = digest(packet)
        # Every fallible step that binds nothing comes first: the output parent and the whole
        # reviewer folder, staged in a hidden sibling. A failure there removes the staging
        # folder and leaves both assessments free for a new packet.
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = output.parent / f".{output.name}.partial-{uuid.uuid4().hex[:12]}"
        staging.mkdir()
        try:
            for name, text in files.items():
                with (staging / name).open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(text)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        # Binding: each assessment's marker, then the packet folder, mapping and record. The
        # staged folder is published by one rename last, so a crash never leaves a
        # complete-looking reviewer folder for an unimportable packet.
        bound = {"packet_id": packet_id, "packet_sha256": packet["sha256"], "created_at": created}
        for parent, *_ in loaded:
            save_new(parent / MARKER, bound)
        directory.mkdir(parents=True, exist_ok=False)
        with exclusive(directory):
            with (directory / "sealed-mapping.json").open("x", encoding="utf-8", newline="\n") as f:
                f.write(mapping_text)
            save_new(directory / "packet.json", packet)
            if output.exists() or output.is_symlink():
                raise FileExistsError(
                    f"reviewer folder appeared meanwhile; staged copy kept: {staging}"
                )
            os.rename(staging, output)
        return packet


def parse_packet_answers(text: str, packet: dict) -> dict:
    """Validate a whole answer sheet before anything is written; refuse any gap."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    review_ids = [item["review_id"] for item in packet["items"]]
    triggered = {i["review_id"]: i["professional_boundary_triggered"] for i in packet["items"]}
    headers = list(HEADER.finditer(text))

    def location(index: int) -> str:
        owners = [header.group(1) for header in headers if header.start() <= index]
        return f"Item {owners[-1]}" if owners else "the declarations"

    for character in LINE_SEPARATORS:
        if (index := text.find(character)) >= 0:
            raise ValueError(
                f"{location(index)}: remove the Unicode line separator U+{ord(character):04X} "
                "(paste as plain text); it would split the ledger line"
            )
    for marker in HIDDEN_MARKERS:
        if (index := text.find(marker)) >= 0:
            raise ValueError(
                f"{location(index)}: remove the HTML comment marker {marker}; "
                "a Markdown preview hides commented text"
            )
    if tag := HTML_LINE.search(text):
        raise ValueError(
            f"{location(tag.start())}: remove the HTML tag that starts a line; "
            "a Markdown preview may hide what it encloses"
        )
    if [header.group(1) for header in headers] != review_ids:
        raise ValueError(
            f"answer sheet needs sections Item {review_ids[0]}-{review_ids[-1]}, "
            "each once and in order"
        )
    prefix = text[: headers[0].start()]
    declarations = {}
    for name in DECLARATIONS:
        values = re.findall(r"^" + re.escape(name) + r":[ \t]*(.*)$", prefix, re.MULTILINE)
        if len(values) != 1 or values[0].strip() in {"", "_"}:
            raise ValueError(f"complete the declaration once: {name}")
        declarations[name] = values[0].strip()
    if declarations["Packet"] != packet["packet_id"]:
        raise ValueError("answer sheet belongs to another packet")
    for name in (ADOPTION, BLIND):
        if declarations[name].casefold().rstrip(".") != "yes":
            raise ValueError(f"explicit Yes declaration required: {name}")
    if declarations[EXPOSURE].casefold().rstrip(".") != "none":
        raise ValueError("blind labels require NONE for judge-output exposure before this review")
    labels = []
    for index, header in enumerate(headers):
        review_id = header.group(1)
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        block = text[header.end() : end].strip()
        match = re.fullmatch(RATINGS + r"[ \t]*\n\s*Comments:(?P<comment>.*)", block, re.DOTALL)
        if not match:
            raise ValueError(f"Item {review_id}: give the eight ratings in order, then Comments:")
        values = dict(zip(DIMENSIONS_V2, match.groups()[: len(DIMENSIONS_V2)], strict=True))
        if "_" in values.values():
            raise ValueError(f"Item {review_id}: replace every _ with 1 or 0")
        if not set(values.values()) <= {"0", "1"}:
            raise ValueError(f"Item {review_id}: each rating must be 0 or 1")
        decisions = {dimension: int(value) for dimension, value in values.items()}
        if not triggered[review_id] and decisions["professional_boundary"] != 1:
            raise ValueError(f"Item {review_id}: professional_boundary is an automatic pass (1)")
        comment = match.group("comment").strip()
        if comment in {"", "_"}:
            raise ValueError(f"Item {review_id}: write a comment")
        labels.append({"review_id": review_id, "decisions": decisions, "notes": comment})
    return {"declarations_as_supplied": declarations, "labels": labels}


# The parser that verifies each import, by the version recorded in it. A parser change gets a
# new version and keeps the old version's parser here, so earlier imports still verify.
PARSER_VERSION = "packet-answers-v1"
PARSERS = {PARSER_VERSION: parse_packet_answers}


def load_packet(root: Path, packet_id: str) -> tuple[Path, dict, dict]:
    """Verify the packet record, its sealed mapping and the answer template it issued."""
    directory = packet_directory(root, packet_id)
    packet = read_json(directory / "packet.json")
    if (
        packet.get("schema_version") != SCHEMA_VERSION
        or packet["packet_id"] != packet_id
        or packet["sha256"] != digest({k: v for k, v in packet.items() if k != "sha256"})
    ):
        raise ValueError("packet record changed")
    if _file_sha256(directory / "sealed-mapping.json") != packet["sealed_mapping_sha256"]:
        raise ValueError("sealed mapping differs from its packet commitment")
    mapping = read_json(directory / "sealed-mapping.json")
    if (
        mapping["packet_id"] != packet_id
        or mapping["seed"] != packet["seed"]
        or [e["review_id"] for e in mapping["entries"]] != [i["review_id"] for i in packet["items"]]
    ):
        raise ValueError("sealed mapping differs from its packet")
    template = render_answers(packet_id, packet["items"])
    if _sha256(template) != packet["reviewer_files_sha256"][TEMPLATE]:
        raise ValueError("answer template differs from its packet commitment")
    return directory, packet, mapping


def import_packet_answers(root: Path, packet_id: str, answers_path: Path, reviewer: str) -> dict:
    directory, packet, mapping = load_packet(root, packet_id)
    if answers_path.is_symlink():
        raise ValueError("symlink answers are not supported")
    raw = answers_path.read_bytes()
    started, finished, sheet = (directory / name for name in IMPORT_FILES)
    arms = [assessment_directory(root, a["assessment_id"]) for a in packet["assessments"]]
    with exclusive(directory), exclusive(arms[0]), exclusive(arms[1]):
        if finished.exists() or finished.is_symlink():
            raise ValueError("packet answers were already imported")
        if any(path.exists() or path.is_symlink() for path in (started, sheet)):
            raise ValueError(
                "an earlier import was interrupted or a sheet is already in the packet folder; "
                "inspect import-started.json, submitted-answers.md and both ledgers first"
            )
        bound = {
            "packet_id": packet_id,
            "packet_sha256": packet["sha256"],
            "created_at": packet["created_at"],
        }
        loaded = {}
        for recorded in packet["assessments"]:
            parent, manifest, records, rubric = _unreviewed(root, recorded["assessment_id"])
            if (
                manifest["manifest_sha256"] != recorded["assessment_sha256"]
                or manifest["purpose"] != recorded["purpose"]
                or manifest["rubric_sha256"] != packet["rubric_sha256"]
            ):
                raise ValueError(f"assessment {recorded['assessment_id']} changed since the packet")
            marker = parent / MARKER
            if not (marker.exists() and read_json(marker) == bound):
                raise ValueError(
                    f"assessment {recorded['assessment_id']} is not bound to {packet_id}"
                )
            loaded[recorded["assessment_id"]] = (parent, manifest, records)
        # The mapping and flags must be exactly what prepare derives from both frozen selections
        # (both arms carry the same frozen rubric, checked above through rubric_sha256).
        rebuilt = _sealed_items(
            [(manifest, records) for _, manifest, records in loaded.values()],
            packet_id,
            packet["seed"],
            rubric,
        )
        if [{key: item[key] for key in MAPPING_KEYS} for item in rebuilt] != mapping["entries"]:
            raise ValueError(
                "sealed mapping differs from the seeded order of both frozen selections"
            )
        if [{key: item[key] for key in FLAG_KEYS} for item in rebuilt] != packet["items"]:
            raise ValueError("professional-boundary flags differ from the frozen classification")
        parsed = parse_packet_answers(raw.decode("utf-8"), packet)
        declared = parsed["declarations_as_supplied"]["Reviewer"]
        if declared != reviewer.strip():
            raise ValueError("the sheet's declared reviewer differs from the importing reviewer")
        answers_sha256 = hashlib.sha256(raw).hexdigest()
        # Preserve the sheet and its declarations before the first label is appended.
        with sheet.open("xb") as stream:
            stream.write(raw)
        save_new(
            started,
            {
                "schema_version": SCHEMA_VERSION,
                "packet_id": packet_id,
                "started_at": now(),
                "parser_version": PARSER_VERSION,
                "answers_sha256": answers_sha256,
                "reviewer": declared,
                "declarations_as_supplied": parsed["declarations_as_supplied"],
            },
        )
        label_ids = {}
        for entry, row in zip(mapping["entries"], parsed["labels"], strict=True):
            parent, manifest, records = loaded[entry["assessment_id"]]
            label = append_label_v2(
                parent,
                manifest,
                records,
                entry["item_id"],
                row["decisions"],
                declared,
                notes=row["notes"],
                review_stage="blind",
                packet_id=packet_id,
                review_id=entry["review_id"],
            )
            label_ids[entry["review_id"]] = label["label_id"]
        result = {
            "schema_version": SCHEMA_VERSION,
            "packet_id": packet_id,
            "imported_at": now(),
            "parser_version": PARSER_VERSION,
            "reviewer": declared,
            "answers_sha256": answers_sha256,
            "declarations_as_supplied": parsed["declarations_as_supplied"],
            "label_ids": label_ids,
            "attribution_boundary": "Reviewer declarations retained; software does not "
            "authenticate authorship or absence of exposure.",
        }
        result["sha256"] = digest(result)
        save_new(finished, result)
        return result


def verified_import(root: Path, packet_id: str) -> tuple[dict, dict, dict]:
    """A finished import whose record, sheet and packet agree, with the sheet re-parsed."""
    directory, packet, mapping = load_packet(root, packet_id)
    started, finished, sheet = (directory / name for name in IMPORT_FILES)
    if not (finished.exists() or finished.is_symlink()):
        state = "unfinished" if any(p.exists() for p in (started, sheet)) else "missing"
        raise ValueError(
            f"packet {packet_id} import is {state}; inspect it before using its labels"
        )
    if missing := [p.name for p in (started, sheet) if not (p.exists() or p.is_symlink())]:
        raise ValueError(
            f"packet {packet_id} has import.json but no {' or '.join(missing)}; "
            "inspect it before using its labels"
        )
    record, marker = read_json(finished), read_json(started)
    parser = PARSERS.get(record.get("parser_version"))
    if parser is None:
        raise ValueError(
            f"packet {packet_id} was imported with parser version "
            f"{record.get('parser_version')}, which this code cannot verify"
        )
    if marker.get("parser_version") != record.get("parser_version"):
        raise ValueError(f"packet {packet_id} import records name different parser versions")
    if (
        record["sha256"] != digest({k: v for k, v in record.items() if k != "sha256"})
        or record["packet_id"] != packet_id
        or _file_sha256(sheet) != record["answers_sha256"]
        or marker["answers_sha256"] != record["answers_sha256"]
        or marker["declarations_as_supplied"] != record["declarations_as_supplied"]
        or sorted(record["label_ids"]) != [entry["review_id"] for entry in mapping["entries"]]
    ):
        raise ValueError(f"packet {packet_id} import record differs from its sheet or packet")
    # The preserved sheet, hash-checked above, is the authority for every imported label.
    parsed = parser(sheet.read_bytes().decode("utf-8"), packet)
    if (
        parsed["declarations_as_supplied"] != record["declarations_as_supplied"]
        or parsed["declarations_as_supplied"]["Reviewer"] != record["reviewer"]
    ):
        raise ValueError(f"packet {packet_id} import record differs from its sheet or packet")
    return record, mapping, parsed


def packet_label_records(root: Path, assessment_id: str, labels: dict) -> dict[str, dict]:
    """Bind every packet-borne label to its finished import and preserved sheet, or refuse."""
    records = {}
    for packet_id in sorted(
        {label["packet_id"] for label in labels.values() if "packet_id" in label}
    ):
        record, mapping, parsed = verified_import(root, packet_id)
        rows = {row["review_id"]: row for row in parsed["labels"]}
        reviewer = parsed["declarations_as_supplied"]["Reviewer"]
        by_label_id = {label["label_id"]: label for label in labels.values()}
        entries = [e for e in mapping["entries"] if e["assessment_id"] == assessment_id]
        borne = [label for label in labels.values() if label.get("packet_id") == packet_id]
        if len(borne) != len(entries):
            raise ValueError(f"labels of packet {packet_id} differ from its finished import")
        for entry in entries:
            label = by_label_id.get(record["label_ids"][entry["review_id"]], {})
            row = rows[entry["review_id"]]
            if (
                label.get("packet_id") != packet_id
                or label.get("review_id") != entry["review_id"]
                or label.get("assessment_id") != assessment_id
                or label.get("item_id") != entry["item_id"]
                # Defence in depth: after the import, nothing else re-checks an entry's
                # payload hash, so a re-signed mapping that changes only it is caught here.
                or label.get("payload_sha256") != entry["payload_sha256"]
                or label.get("decisions") != row["decisions"]
                or label.get("notes") != row["notes"]
                or label.get("reviewer") != reviewer
                or label.get("review_stage") != "blind"
            ):
                raise ValueError(
                    f"label for {entry['review_id']} of packet {packet_id} differs from its "
                    "finished import, the preserved sheet or the sealed routing"
                )
        records[packet_id] = record
    return records
