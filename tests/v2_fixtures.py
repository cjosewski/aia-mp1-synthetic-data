"""Entirely synthetic v2 cohorts, task packs and answer sheets, used only in temporary tests."""

import hashlib
import json
from pathlib import Path

from assessed_fixtures import GoodClient, fixture_config
from test_generation import valid_item

from aia_mp1 import review_packet_v2
from aia_mp1.assessment import read_json
from aia_mp1.cohort import freeze_cohort
from aia_mp1.collection import collect
from aia_mp1.model_client import AttemptResult
from aia_mp1.reference_v2 import freeze_reference_v2
from aia_mp1.review_packet_v2 import (
    DECLARATIONS,
    import_packet_answers,
    prepare_masked_packet,
)
from aia_mp1.rubric_v2 import DIMENSIONS_V2
from aia_mp1.schemas import CATEGORIES
from aia_mp1.tracing import digest, read_records

REPO = Path(__file__).resolve().parents[1]
RUBRIC_V2 = REPO / "config/aec-course/rubric-v2.json"
REVIEWER = "Synthetic reviewer"


def v2_config(tmp_path):
    """The assessed fixture, with task IDs the frozen rubric classifies and neutral briefs."""
    config = fixture_config(tmp_path)
    path = Path(config.reference_pack_path)
    pack = json.loads(path.read_text())
    pairs = [(c, n) for c in CATEGORIES for n in range(1, 11)]
    pack["tasks"] = [
        {
            "id": f"{category}-{number:02d}",
            "brief": f"Synthetic brief {index:02d}: count the standalone fixture objects.",
            "category": category,
            "source_refs": ["test-source"],
        }
        for index, (category, number) in enumerate(pairs, 1)
    ]
    path.write_text(json.dumps(pack))
    return config


class OffsetClient(GoodClient):
    """Synthetic items numbered from an offset, so a further cohort has distinct payloads."""

    def __init__(self, offset: int):
        super().__init__()
        self.offset = offset

    def generate(self, messages):
        self.calls += 1
        self.messages.append(messages)
        item = valid_item(self.calls + self.offset)
        return AttemptResult(item, item.model_dump(), None, None, "actual-local-model")


def build_cohort(config, collection_id: str, cohort_id: str, client=None, **changes) -> Path:
    """Collect 50 synthetic items and freeze them; changes alter the generator settings."""
    config = config.model_copy(update=changes)
    root = Path(config.artifact_root)
    collect(config, collection_id, client or GoodClient())
    freeze_cohort(root, collection_id, cohort_id)
    return root


def arms(tmp_path, **corrected):
    """A baseline and a corrected cohort that differ in a prompt variant and any changes."""
    config = v2_config(tmp_path)
    root = build_cohort(config, "arm-a", "cohort-a")
    changes = {"purpose": "corrected", "prompt_variant": "variant-b"} | corrected
    build_cohort(config, "arm-b", "cohort-b", **changes)
    return root, config


def resign_ledger(directory: Path, mutate, index: int = 0) -> None:
    """Rewrite a label ledger with one label changed, keeping its chain and checkpoint valid."""
    path = directory / "human-labels.jsonl"
    previous, lines = None, []
    for number, envelope in enumerate(read_records(path)):
        if number == index:
            mutate(envelope["label"])
        signed = {"label": envelope["label"], "previous_sha256": previous}
        signed["sha256"] = previous = digest(signed)
        lines.append(json.dumps(signed, ensure_ascii=False) + "\n")
    path.write_text("".join(lines))
    checkpoint = read_json(directory / "labels-checkpoint.json")
    checkpoint["ledger_sha256"] = digest("".join(lines))
    (directory / "labels-checkpoint.json").write_text(json.dumps(checkpoint))


def decisions(**changes) -> dict:
    return dict.fromkeys(DIMENSIONS_V2, 1) | changes


def pin_task_pack(monkeypatch, pack: Path) -> None:
    """Let the synthetic pack stand in for the private pack that the frozen rubric pins."""
    pinned = hashlib.sha256(pack.read_bytes()).hexdigest()
    monkeypatch.setattr(review_packet_v2, "pinned_task_pack_sha256", lambda rubric: pinned)


def complete_sheet(text: str, zeros: dict | None = None) -> str:
    """Fill a blank answer sheet with passes; zeros maps review IDs to failed dimensions."""
    values = (REVIEWER, "2026-11-21", "NONE", "NONE", "Yes", "Yes")
    for name, value in zip(DECLARATIONS[1:], values, strict=True):
        text = text.replace(f"{name}: \n", f"{name}: {value}\n", 1)
    text = text.replace("=_", "=1")
    text = text.replace("Comments: \n", "Comments: Synthetic comment.\nSecond synthetic line.\n")
    head, *parts = text.split("\n## Item ")
    for index, part in enumerate(parts):
        for dimension in (zeros or {}).get(part[:3], ()):
            parts[index] = parts[index].replace(f"{dimension}=1", f"{dimension}=0", 1)
    return "\n## Item ".join([head, *parts])


def review_by_packet(
    root: Path, tmp_path: Path, pack: Path, ids, *, packet_id="packet-x", zeros=None, freeze=True
):
    """Prepare one packet, answer it, import it and freeze both references.

    zeros receives the sealed mapping entries and returns failed dimensions by review ID.
    """
    output = tmp_path / f"reviewer-{packet_id}"
    prepare_masked_packet(root, packet_id, list(ids), pack, output)
    entries = read_json(root / "packets" / packet_id / "sealed-mapping.json")["entries"]
    answers = output / "MY-ANSWERS.md"
    answers.write_text(complete_sheet(answers.read_text(), zeros(entries) if zeros else None))
    import_packet_answers(root, packet_id, answers, REVIEWER)
    for assessment_id in ids if freeze else ():
        freeze_reference_v2(root, assessment_id, REVIEWER, declare_blind=True)
    return entries


def selected_records(root: Path, assessment_id: str) -> list[dict]:
    directory = root / "assessments" / assessment_id
    manifest = read_json(directory / "manifest.json")
    by_id = {
        json.loads(line)["item_id"]: json.loads(line)
        for line in (directory / "data.jsonl").read_text().splitlines()
    }
    return [by_id[item_id] for item_id in manifest["selected_ids"]]
