"""Build gates G1-G4 and G6-G8 of docs/AEC-RAG-PACK.md section 9 (G5 is tools/scan_rag_leakage.py).

``check_rag_pack.py <gate> --build <pack dir> ...`` re-derives each claim of a finished build from
its pinned inputs, writes ``<build>/gates/<gate>.json`` by exclusive create and exits 0 on a pass,
1 on a failed or incomplete gate and 2 (``error: ...`` on stderr) on an input error. ``all`` runs
G1-G4 and G6-G8 and adds ``gates/gates.json``. No network, no model, no hosted service: the
tokenizer is the offline Qwen port, the dry run uses a fake client in a temporary root, and the
baseline is read through the unchanged cohort loader. Nothing is overwritten.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import build_rag_corpus as bc
import build_rag_pack as bp
import qwen_offline_tokenizer as qwen

from aia_mp1 import retrieval as r

TOOL = Path(__file__).resolve()
REPO = bc.REPO
SCHEMA = "rag-gate-v1"
GATES_SCHEMA = "rag-gates-v1"
GATE_NAMES = {
    "G1": "provenance",
    "G2": "determinism",
    "G3": "tokenizer-parity",
    "G4": "token-preflight",
    "G6": "dry-run",
    "G7": "retrieval-metrics",
    "G8": "baseline",
}
LEAKAGE_FILE = "leakage-scan.json"
COURSE_DOMAIN = "aec-course"
UNUSED_KEY_ENV = "AIA_MP1_RAG_DRY_RUN_UNUSED"
MODEL_IDENTITY = (
    "unsloth/Qwen3-30B-A3B-GGUF@d5b1d57bd0b504ac62ae6c725904e96ef228dc74/Qwen3-30B-A3B-Q4_K_M.gguf"
)
DRY_COLLECTION = "dry-rag-001"
DRY_COHORT = "dry-rag-cohort"
DRY_ASSESSMENT = "dry-rag-assessment"
RESUME_REFUSAL = "resume requires identical collection inputs"
WORKER_TIMEOUT = 1800

# §1.1: the first twelve rows, full sha256 of the files that must stay byte-unchanged.
PINNED_MODULES = {
    "generate.py": "e892fa4633edb4ab2c0bd4e7e24eb7dd0446907a1507ced69ffb5607063fedf4",
    "gate.py": "e9f68078fcee2fefdc1727ec7263263e680c855c53ca8766a88ac7bd6b188f90",
    "sources.py": "2e3cea4753b1fcee5f01019769aa9c70f8a1f61c996448f0180243821b1cc764",
    "schemas.py": "0eebbe94bfe8240ba2d6a1ce6e102716737322c82833fa41787ba0c7bfe51f72",
    "collection.py": "f14179db06a89a007c7e877b12042fe5613ba1e66731e02b89b24e455bdddc62",
    "cohort.py": "9122293067af3dff91dfee48d8c35e188239d968a20043b64a3a59e8ff2ce892",
    "config.py": "edd708470ce8301adb28dde45705cf0ca3748581eeb1196620810443b4cc2b0e",
    "model_client.py": "e85070f413e2d1bfa371c1467eb50c7894a9ad421c87b25672362e01792236ed",
    "tracing.py": "adc39f8062b1031409f34a94ce9787bb899a32afc60bb22f5405c2b409326a6e",
    "cli.py": "a2dadaa47ca386bbd64af0fc41047c8a1a2d6e5170327adc236be5a140e68943",
    "collection_cli.py": "2b92af4bcf3519a99103aaad1a8f08205f6f6c6d2d8617e57917d58d917c3d41",
    "assessment.py": "1862e86830c9ec7f1fec9812e6430f8632d648ab884a42eb8434701e0b0def4f",
}
PROMPT_V1 = "prompts/generator-assessed-v1.md"


class GateError(ValueError):
    """An input error: the gate cannot be evaluated. The CLI prints it and exits 2."""


class CheckFailed(Exception):
    """A sub-check ran and the claim does not hold."""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


class Incomplete(Exception):
    """A sub-check cannot run yet (for example prompt v3 is not assembled)."""


class Checks:
    """Sub-checks in order; an unexpected exception is a failed check, never a crash."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def run(self, check_id: str, name: str, function: Callable[[], dict | None]) -> None:
        try:
            detail, status = function() or {}, "pass"
        except CheckFailed as exc:
            detail, status = {"reason": str(exc), **exc.detail}, "fail"
        except Incomplete as exc:
            detail, status = {"reason": str(exc)}, "incomplete"
        except Exception as exc:  # noqa: BLE001 - any failure to verify is a failed check
            detail, status = {"error": f"{type(exc).__name__}: {exc}"}, "fail"
        self.rows.append({"id": check_id, "name": name, "status": status, "detail": detail})

    @property
    def status(self) -> str:
        return combine(row["status"] for row in self.rows)


def combine(statuses) -> str:
    values = list(statuses)
    if "fail" in values:
        return "fail"
    return "incomplete" if "incomplete" in values or not values else "pass"


@dataclass
class Setup:
    build: Path
    evidence: Path = bc.DEFAULT_EVIDENCE
    repository: Path = REPO
    corpus: Path | None = None
    tier2: Path | None = None
    prompt: Path | None = None
    gguf: Path | None = None

    def __post_init__(self) -> None:
        self.build = bc._abs(self.build)
        self.evidence = bc._abs(self.evidence)
        self.repository = bc._abs(self.repository)
        self.corpus = bc._abs(self.corpus or self.build.parent / "corpus-v1")
        if self.tier2 is not None:
            self.tier2 = bc._abs(self.tier2)
        if self.prompt is not None:
            self.prompt = bc._abs(self.prompt)

    @property
    def gates(self) -> Path:
        return self.build / "gates"


# ------------------------------------------------------------------ the loaded build


def _load(path: Path, what: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateError(f"{what} {path} is unreadable: {exc}") from exc


class Build:
    """The pack, its receipts, the corpus and the pinned inputs, loaded through the §1.4 reader."""

    def __init__(self, setup: Setup):
        self.setup = setup
        self.dir = setup.build
        self.pack_path = self.dir / bp.PACK_FILE
        if not self.pack_path.is_file():
            raise GateError(f"no pack {bp.PACK_FILE} in {self.dir}")
        self.pack_bytes = self.pack_path.read_bytes()
        self.pack_text = self.pack_bytes.decode("utf-8")
        self.pack = _load(self.pack_path, "pack")
        self.receipt = _load(self.dir / "build-receipt.json", "build receipt")
        self.report_bytes = (self.dir / "retrieval-report.json").read_bytes()
        self.report = _load(self.dir / "retrieval-report.json", "retrieval report")
        self.reader = bc.InputReader(
            evidence=setup.evidence, repository=setup.repository, corpus=setup.corpus
        )
        try:
            corpus = setup.corpus
            self.manifest_bytes = self.reader.read(
                corpus / "corpus-manifest.json", "corpus_manifest"
            )
            self.chunks_bytes = self.reader.read(corpus / "chunks.jsonl", "corpus_chunks")
            self.corpus_receipt_bytes = self.reader.read(
                corpus / "corpus-receipt.json", "corpus_receipt"
            )
            self.manifest = bc._json(self.manifest_bytes, "corpus manifest")
            self.corpus_receipt = bc._json(self.corpus_receipt_bytes, "corpus receipt")
            self.config_bytes = self.reader.read(
                setup.repository / self.manifest["sources_config"]["path"],
                "sources_config",
                sha256=self.manifest["sources_config"]["sha256"],
            )
            self.config = bc._json(self.config_bytes, "rag-sources")
            pin = self.manifest["engineering_v1"]
            self.base_bytes = self.reader.read(
                setup.evidence / pin["path"], "engineering_v1", sha256=pin["sha256"]
            )
            self.base = bc._json(self.base_bytes, "engineering-v1")
            fetch_path = Path(self.manifest["fetch_receipt"]["path"])
        except (bc.BuildError, KeyError, TypeError) as exc:
            raise GateError(f"cannot load the corpus inputs: {exc}") from exc
        self.reader.roots["tier2"] = (
            setup.tier2 if setup.tier2 is not None else setup.evidence / fetch_path.parent
        )
        self.files = {f["file_key"]: f for f in self.manifest["files"]}
        self.repos = {x["repo_key"]: x for x in self.manifest["repositories"]}
        self.rows = [
            json.loads(line) for line in self.chunks_bytes.decode("utf-8").split("\n") if line
        ]
        self.row_problems: list[str] = []
        self.chunks_by_category: dict[str, list[r.Chunk]] = {c: [] for c in r.CATEGORIES}
        self.chunks_by_key: dict[str, r.Chunk] = {}
        for row in self.rows:
            if row["content_sha256"] != r.digest(row["text"]) or row["chunk_key"] != (
                f"{row['file_key']}#L{row['start']}-L{row['end']}"
            ):
                self.row_problems.append(row["chunk_key"])
            chunk = r.Chunk.from_row(row)
            self.chunks_by_category[chunk.category].append(chunk)
            self.chunks_by_key[chunk.chunk_key] = chunk
        self._texts: dict[str, str] = {}

    def file_text(self, record: dict) -> str:
        key = record["file_key"]
        if key not in self._texts:
            self._texts[key] = bp._file_text(self.reader, self.config, record)
        return self._texts[key]

    def passage_entry(self, chunk: r.Chunk) -> dict:
        record = self.files[chunk.file_key]
        repo = self.repos[record["repo_key"]]
        return r.passage_entry(
            category=chunk.category,
            text=chunk.text,
            owner=repo["owner"],
            repo=repo["repo"],
            commit=repo["commit"],
            path=record["path"],
            derived=record.get("derived") is not None,
            start=chunk.start,
            end=chunk.end,
            version_scope=record["version_scope"],
            label=chunk.segment_label,
            retrieved_at=record["retrieved_at"],
            license_expression=record["license_expression"],
            license_evidence=bp._license_evidence(record),
            attribution=record["attribution"],
        )

    def environment(self, count_tokens: Callable[[str], int]):
        """§6.5 from the pinned files: entries and receipt rows by category, and blocked lines."""
        entries, rows, blocked = {}, {}, {}
        config_repos = {x["repo_key"]: x for x in self.config["repositories"]}
        for spec in self.config["environment_passages"]:
            category = spec["category"]
            repo = self.repos[spec["repo_key"]]
            records, blocks = [], []
            for block in spec["blocks"]:
                record = self.files.get(block["file_key"])
                if record is None or record["repo_key"] != spec["repo_key"]:
                    raise CheckFailed(f"{spec['id']}: {block['file_key']} is not an admitted file")
                lines = r.parse_ranges(block["lines"])
                blocks.append(
                    r.environment_block(
                        owner=repo["owner"],
                        repo=repo["repo"],
                        commit=repo["commit"],
                        path=record["path"],
                        derived=record.get("derived") is not None,
                        text=self.file_text(record),
                        lines=lines,
                    )
                )
                records.append(record)
                blocked.setdefault(category, {}).setdefault(block["file_key"], set()).update(lines)
            text, tokens = r.environment_passage(spec["target"], blocks, count_tokens)
            attribution_templates = config_repos[spec["repo_key"]]["attribution"]
            template = attribution_templates.get("environment", attribution_templates["passage"])
            headers = []
            for record in records:
                for notice in record.get("notices", []):
                    if notice["kind"] == "file_header" and notice["text"] not in headers:
                        headers.append(notice["text"])
            attribution = r.fill_attribution(
                template,
                owner=repo["owner"],
                repo=repo["repo"],
                header=" File header: ".join(headers) or None,
                notice=bp._notice(records, "cheat_sheet_notice"),
                regents_notice=bp._notice(records, "regents_notice"),
            )
            entries[category] = r.environment_entry(
                category=category,
                target=spec["target"],
                text=text,
                owner=repo["owner"],
                repo=repo["repo"],
                commit=repo["commit"],
                version_scope=repo["version_scope"],
                retrieved_at=r.latest_timestamp(x["retrieved_at"] for x in records),
                license_expression=repo["license_expression"],
                license_evidence=bp._license_evidence(records[0]),
                attribution=attribution,
            )
            rows[category] = {
                "id": spec["id"],
                "category": category,
                "tokens": tokens,
                "sha256": r.digest(text),
                "blocks": [
                    {"file_key": b["file_key"], "lines": r.parse_ranges(b["lines"])}
                    for b in spec["blocks"]
                ],
                "tokens_nov20": spec.get("tokens_nov20"),
            }
        if set(entries) != set(r.CATEGORIES):
            raise CheckFailed("every category needs exactly one environment passage")
        return entries, rows, blocked

    def blocked_lines(self) -> dict:
        """The environment lines that retrieval must not select, from the pinned table alone."""
        blocked: dict = {}
        for spec in self.config["environment_passages"]:
            for block in spec["blocks"]:
                blocked.setdefault(spec["category"], {}).setdefault(
                    block["file_key"], set()
                ).update(r.parse_ranges(block["lines"]))
        return blocked

    def retrievers(self, blocked: Mapping) -> dict[str, r.CategoryRetriever]:
        return {
            c: r.CategoryRetriever(self.chunks_by_category[c], blocked.get(c, {}))
            for c in r.CATEGORIES
        }


def tool_record() -> dict:
    return {
        "path": TOOL.relative_to(REPO).as_posix(),
        "sha256": hashlib.sha256(TOOL.read_bytes()).hexdigest(),
    }


def pack_identity(setup: Setup) -> dict:
    """Which pack a gate result is about: the file's hash and the pack digest."""
    path = setup.build / bp.PACK_FILE
    try:
        data = path.read_bytes()
        return {"pack_file_sha256": r.sha256_hex(data), "pack_digest": r.digest(json.loads(data))}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateError(f"pack {path} is unreadable: {exc}") from exc


def result_of(gate: str, identity: dict | None, status: str, **body) -> dict:
    out = {
        "schema_version": SCHEMA,
        "gate": gate,
        "name": GATE_NAMES[gate],
        "status": status,
        "tool": tool_record(),
    }
    if identity is not None:
        out["build"] = identity
    return out | body


def preview(items: list, limit: int = 20) -> dict:
    return {"count": len(items), "first": items[:limit]}


# ------------------------------------------------------------------ G1 provenance


def _stored_items(fetched: dict):
    for key, item in fetched.items():
        for entry in item.get("files", []):
            if entry.get("stored") is not None:
                yield key, entry


def _t1_admitted(b: Build, fetched: dict) -> tuple[dict, dict]:
    """The tier-1 files for §3.7 step 6, from the manifest and the exclusions of the corpus."""
    items = {(k, e["path"]): e for k, item in fetched.items() for e in item.get("files", [])}
    admitted: dict = {}
    for record in b.manifest["files"]:
        if record["tier"] == "T1":
            kind = (record.get("derived") or {}).get("kind")
            admitted[(record["repo_key"], record["path"])] = {"tier": "T1", "derived": kind}
    config_repos = {x["repo_key"]: x for x in b.config["repositories"]}
    for excluded in b.manifest["excluded"]:
        explicit, glob = bc._spec_for(config_repos[excluded["repo_key"]], excluded["path"])
        spec = {**(glob or {}), **(explicit or {})}
        if spec.get("tier") == "T1":
            admitted[(excluded["repo_key"], excluded["path"])] = {
                "tier": "T1",
                "derived": spec.get("derived"),
            }
    return admitted, items


def check_consistency(b: Build) -> dict:
    """G1.0: the build, corpus and receipts agree on the bytes they name."""
    problems = []
    outputs = b.corpus_receipt.get("outputs", {})
    for name, data in (
        ("corpus-manifest.json", b.manifest_bytes),
        ("chunks.jsonl", b.chunks_bytes),
    ):
        if outputs.get(name) != r.sha256_hex(data):
            problems.append(f"corpus receipt names a different {name}")
    corpus = b.receipt.get("corpus", {})
    for name, data in (
        ("corpus-manifest.json", b.manifest_bytes),
        ("chunks.jsonl", b.chunks_bytes),
        ("corpus-receipt.json", b.corpus_receipt_bytes),
    ):
        if corpus.get(name) != r.sha256_hex(data):
            problems.append(f"build receipt names a different {name}")
    pack = b.receipt.get("pack", {})
    if pack.get("file_sha256") != r.sha256_hex(b.pack_bytes) or pack.get("digest") != r.digest(
        b.pack
    ):
        problems.append("build receipt names a different pack")
    if b.receipt.get("outputs") != {
        bp.PACK_FILE: r.sha256_hex(b.pack_bytes),
        "retrieval-report.json": r.sha256_hex(b.report_bytes),
    }:
        problems.append("build receipt outputs differ from the files")
    if b.receipt.get("engineering_v1") != {
        "sha256": r.sha256_hex(b.base_bytes),
        "digest": r.digest(b.base),
    }:
        problems.append("build receipt names a different engineering-v1")
    if b.receipt.get("tasks") != [
        {"task_id": t["id"], "source_refs": t["source_refs"]} for t in b.pack.get("tasks", [])
    ]:
        problems.append("build receipt task references differ from the pack")
    if b.receipt.get("tokenizer") != b.corpus_receipt.get("tokenizer"):
        problems.append("the chunk token counts and the pack budget used different tokenizers")
    if b.row_problems:
        problems.append(f"{len(b.row_problems)} chunk rows are inconsistent")
    if problems:
        raise CheckFailed("; ".join(problems), {"problems": problems})
    return {"chunks": len(b.rows), "files": len(b.manifest["files"])}


def check_fetch_blobs(b: Build) -> dict:
    """G1.1: the fetch receipt's bytes and every stored blob (AR-8)."""
    fetch_bytes = b.reader.read(
        b.reader.roots["tier2"] / "fetch-receipt.json",
        "fetch_receipt",
        sha256=b.manifest["fetch_receipt"]["sha256"],
    )
    fetched = bc.check_fetch(
        b.config, bc._json(fetch_bytes, "fetch receipt"), r.sha256_hex(b.config_bytes)
    )
    count = 0
    for key, item in _stored_items(fetched):
        bc.stored_bytes(b.reader, key, item)
        count += 1
    return {"repositories": len(fetched), "stored_files": count}


def check_tier1(b: Build) -> dict:
    """G1.2: §3.7 steps 1-5, then step 6 against the fetched blobs, equal to the corpus receipt."""
    tier1 = bc.verify_tier1(b.reader, b.config)
    fetch = bc._json(
        b.reader.read(b.reader.roots["tier2"] / "fetch-receipt.json", "fetch_receipt"),
        "fetch receipt",
    )
    fetched = bc.check_fetch(b.config, fetch, r.sha256_hex(b.config_bytes))
    admitted, items = _t1_admitted(b, fetched)
    raw = {key: bc.stored_bytes(b.reader, key[0], items[key]) for key in admitted}
    cross = bc.cross_check_tier1(b.config, tier1, admitted, raw)
    recorded = b.corpus_receipt["tier1_verification"]
    steps = {k: v for k, v in recorded.items() if k != "6_cross_check"}
    if json.loads(json.dumps(tier1["steps"])) != steps or cross != recorded["6_cross_check"]:
        raise CheckFailed("the tier-1 verification differs from the corpus receipt")
    return {"tier1_files": len(admitted), "cross_checked": len(cross)}


def check_text_hashes(b: Build) -> dict:
    """G1.3: every normalized and derived text hash equals the manifest's."""
    failures = []
    for record in b.manifest["files"]:
        try:
            bp._file_text(b.reader, b.config, record)
        except (bc.BuildError, ValueError, OSError) as exc:
            failures.append({"file_key": record["file_key"], "error": str(exc)})
    fetch = bc._json(
        b.reader.read(b.reader.roots["tier2"] / "fetch-receipt.json", "fetch_receipt"),
        "fetch receipt",
    )
    items = {
        (x.get("repo_key"), f.get("path")): f
        for x in fetch.get("repositories", [])
        for f in x.get("files", [])
    }
    for record in b.manifest["files"]:  # raw provenance equals the fetch receipt's item
        item = items.get((record["repo_key"], record["path"]))
        derived = record.get("derived") or {}
        if (
            item is None
            or record["raw_sha256"] != item.get("raw_sha256")
            or record["blob"] != item.get("blob")
            or record["raw_bytes"] != item.get("size")
            or (derived and derived.get("from_raw_sha256") != item.get("raw_sha256"))
        ):
            failures.append(
                {"file_key": record["file_key"], "error": "raw provenance differs from the fetch"}
            )
    licenses = 0
    for repository in b.manifest["repositories"]:
        for entry in repository["license_files"]:
            licenses += 1
            try:
                found = r.sha256_hex(
                    b.reader.read(b.setup.evidence / entry["evidence_path"], "license_evidence")
                )
                if found != entry.get("evidence_sha256"):
                    raise ValueError("the evidence bytes differ from evidence_sha256")
            except (bc.BuildError, ValueError, OSError, KeyError) as exc:
                failures.append(
                    {"license_file": f"{repository['repo_key']}/{entry['path']}", "error": str(exc)}
                )
    if failures:
        raise CheckFailed(f"{len(failures)} texts differ", {"files": preview(failures)})
    return {"files": len(b.manifest["files"]), "license_files": licenses}


def check_reslice(b: Build) -> dict:
    """G1.4: every retrieved passage re-slices from its pinned file and rebuilds its entry."""
    by_id = {s["id"]: s for s in b.pack["sources"]}
    rows = {row["chunk_key"]: row for row in b.rows}
    passages = b.receipt["passages"]
    problems = []
    retrieved = {i for i in by_id if re.fullmatch(r"(gis|aec|str|cad|sim)-p-[0-9a-f]{12}", i)}
    if {p["id"] for p in passages} != retrieved:
        problems.append({"id": "*", "error": "receipt passages differ from the pack's passages"})
    for passage in passages:
        try:
            record = b.files[passage["file_key"]]
            row = rows[passage["chunk_key"]]
            entry = by_id[passage["id"]]
            text = r.reslice(
                b.file_text(record), passage["start"], passage["end"], passage["removed_within"]
            )
            wrong = []
            if entry["text"] != text:
                wrong.append("pack text differs from the re-slice")
            if row["text"] != text:
                wrong.append("chunk table text differs from the re-slice")
            if entry["content_sha256"] != r.digest(text):
                wrong.append("content_sha256 differs")
            if (row["file_key"], row["start"], row["end"]) != (
                passage["file_key"],
                passage["start"],
                passage["end"],
            ) or [list(x) for x in row["removed_within"]] != [
                list(x) for x in passage["removed_within"]
            ]:
                wrong.append("chunk row differs from the receipt")
            if passage["tokens"] != row["qwen_tokens"]:
                wrong.append("token count differs")
            if entry != b.passage_entry(r.Chunk.from_row({**row, "text": text})):
                wrong.append("entry fields differ from the templates")
            if wrong:
                problems.append({"id": passage["id"], "error": "; ".join(wrong)})
        except (bc.BuildError, KeyError, ValueError, OSError) as exc:
            problems.append({"id": passage.get("id"), "error": f"{type(exc).__name__}: {exc}"})
    if problems:
        raise CheckFailed(f"{len(problems)} passages fail", {"passages": preview(problems)})
    return {"passages": len(passages)}


def check_environment(b: Build, count_tokens: Callable[[str], int]) -> dict:
    """G1.5: each environment passage rebuilds exactly from §6.5 within 600 tokens."""
    entries, rows, _ = b.environment(count_tokens)
    by_id = {s["id"]: s for s in b.pack["sources"]}
    problems = [
        f"{e['id']} differs from the rebuilt entry"
        for e in entries.values()
        if by_id.get(e["id"]) != e
    ]
    if b.receipt["environment"] != list(rows.values()):
        problems.append("receipt environment rows differ from the rebuilt rows")
    if problems:
        raise CheckFailed("; ".join(problems), {"problems": problems})
    return {"tokens": {row["id"]: row["tokens"] for row in rows.values()}, "cap": r.ENV_MAX_TOKENS}


def rebuild_pack(b: Build, environment: Mapping, blocked: Mapping) -> dict:
    retrievers = b.retrievers(blocked)
    order = {c: i for i, c in enumerate(r.CATEGORIES)}
    passages, task_passages = [], {}
    for task in b.base["tasks"]:
        ids = []
        for chunk in retrievers[task["category"]].retrieve(task["brief"]).selected:
            entry = b.passage_entry(chunk)
            ids.append(entry["id"])
            passages.append(
                ((order[chunk.category], chunk.file_index, chunk.start, chunk.end), entry)
            )
        task_passages[task["id"]] = ids
    return r.assemble_pack(
        b.base, environment, passages, task_passages, r.sha256_hex(b.manifest_bytes)
    )


def check_static_and_tasks(b: Build, expected: dict) -> dict:
    """G1.6: static spans and tasks (§7.3-§7.4); the pack equals its rebuild, byte for byte."""
    pack, problems = b.pack, []
    base_text = b.base_bytes.decode("utf-8")
    spans = r.static_source_spans(base_text)[: len(b.base["sources"])]
    if len(spans) != len(b.base["sources"]) or any(s not in b.pack_text for s in spans):
        problems.append("a static entry's byte span is not verbatim in the pack")
    if r.static_source_spans(b.pack_text)[: len(spans)] != spans:
        problems.append("static entries are not the first five entries, unchanged")
    for entry in pack["sources"]:
        if tuple(entry) != r.SOURCE_FIELDS:
            problems.append(f"{entry.get('id')}: not the twelve fields in order")
        elif (
            entry["allowed_uses"] != list(r.ALLOWED_USES)
            or entry["export_permission"] != r.EXPORT_PERMISSION
            or entry["content_sha256"] != r.digest(entry["text"])
        ):
            problems.append(f"{entry['id']}: uses, export permission or content hash")
    if len(pack["tasks"]) != len(b.base["tasks"]):
        problems.append("the pack has a different number of tasks")
    changed = []
    for old, new, want in zip(b.base["tasks"], pack["tasks"], expected["tasks"], strict=False):
        if {k: v for k, v in old.items() if k != "source_refs"} != {
            k: v for k, v in new.items() if k != "source_refs"
        }:
            problems.append(f"task {old['id']} changed beyond its references")
        if new != want:
            changed.append(new["id"])
    if changed:
        problems.append(f"{len(changed)} tasks differ from the retrieved references")
    if [s["id"] for s in pack["sources"]] != [s["id"] for s in expected["sources"]]:
        problems.append("the pack's entries differ from the rebuilt entries")
    if r.pack_json(expected) != b.pack_text:
        problems.append("the pack is not byte-identical to its rebuild")
    if r.separator_location(b.pack_text):
        problems.append("the pack holds U+0085, U+2028 or U+2029, which ledger readers split on")
    if problems:
        raise CheckFailed(
            "; ".join(problems), {"problems": problems, "tasks_with_other_refs": preview(changed)}
        )
    return {"sources": len(pack["sources"]), "tasks": len(pack["tasks"])}


def check_source_check(b: Build) -> dict:
    """G1.7: ``load_pack`` and ``python -m aia_mp1 source-check`` on the pack."""
    from aia_mp1.sources import load_pack

    pack = load_pack(b.pack_path)
    completed = subprocess.run(
        [sys.executable, "-m", "aia_mp1", "source-check", "--pack", str(b.pack_path)],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, "AIA_MP1_DOMAIN": COURSE_DOMAIN},
        timeout=600,
        check=False,
    )
    if completed.returncode != 0:
        raise CheckFailed(f"source-check exited {completed.returncode}")
    shown = json.loads(completed.stdout)
    retrieved = len(b.receipt["passages"])
    wanted = {"status": "ready", "tasks": 50, "sources": 10 + retrieved, "sha256": r.digest(pack)}
    if {k: shown.get(k) for k in wanted} != wanted:
        raise CheckFailed("source-check output differs", {"expected": wanted})
    return wanted


def check_context_for(b: Build, expected: dict) -> dict:
    """G1.8: ``context_for`` returns the expected entries for all 50 (category, ordinal) pairs."""
    from aia_mp1.sources import context_for

    by_id = {s["id"]: s for s in expected["sources"]}
    pack_digest = r.digest(b.pack)
    for category in r.CATEGORIES:
        tasks = [t for t in expected["tasks"] if t["category"] == category]
        for ordinal in range(10):
            task = tasks[ordinal % len(tasks)]
            want = {
                "pack_sha256": pack_digest,
                "task": task,
                "sources": [by_id[ref] for ref in task["source_refs"]],
            }
            if context_for(b.pack, category, ordinal) != want:
                raise CheckFailed(f"context_for differs for {category} ordinal {ordinal}")
    return {"pairs": 50}


def corrected_config(
    pack: Path, prompt: Path, artifact_root: Path, domain: str = COURSE_DOMAIN
) -> dict:
    """§9 G6 ``RunConfig`` fields (design §3 client settings)."""
    return {
        "base_url": "http://127.0.0.1:18081/v1",
        "domain": domain,
        "model": qwen.SERVED_MODEL,
        "purpose": "corrected",
        "reference_pack_path": str(pack),
        "model_identity": MODEL_IDENTITY,
        "model_sha256": qwen.GGUF_SHA256,
        "api_key_env": UNUSED_KEY_ENV,
        "mode": "json",
        "temperature": 0.6,
        "timeout_seconds": 120,
        "max_tokens": 4096,
        "max_attempts": 2,
        "artifact_root": str(artifact_root),
        "prompt_path": str(prompt),
        "prompt_variant": r.PROMPT_VARIANT,
    }


def run_in_domain(task: str, payload: dict) -> dict:
    """Run one worker task in a fresh process with ``AIA_MP1_DOMAIN=aec-course``."""
    env = {**os.environ, "AIA_MP1_DOMAIN": COURSE_DOMAIN}
    env.pop(UNUSED_KEY_ENV, None)
    try:
        completed = subprocess.run(
            [sys.executable, str(TOOL), "_worker", task],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=REPO,
            env=env,
            timeout=WORKER_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise GateError(f"the {task} worker timed out after {WORKER_TIMEOUT} s") from None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        tail = (completed.stderr.strip().splitlines() or ["no output"])[-1]
        raise GateError(f"the {task} worker failed: {tail}") from None


def assembly_problem(setup: Setup) -> tuple[str, str] | None:
    """Why ``setup.prompt`` is not the v3 that passed assembly: ``(status, reason)`` or None.

    The receipt is ``prompt-v3/assembly-receipt.json`` beside the pack directory (§8.4). An absent
    receipt is incomplete; a different prompt hash or a failed check is a failure.
    """
    path = setup.build.parent / "prompt-v3" / "assembly-receipt.json"
    if not path.is_file():
        return "incomplete", "the assembly receipt is missing"
    try:
        receipt = json.loads(path.read_bytes())
        assembled, checks = receipt["v3"]["sha256"], receipt["checks"]
    except (ValueError, KeyError, TypeError):
        return "fail", "the assembly receipt is unreadable"
    if assembled != r.sha256_hex(setup.prompt.read_bytes()):
        return "fail", "--prompt is not the v3 the assembly receipt names"
    if not checks or not all(isinstance(c, dict) and c.get("passed") is True for c in checks):
        return "fail", "the assembly receipt records a failed or missing check"
    return None


def check_load_inputs(b: Build, prompt: Path | None) -> dict:
    """G1.9: ``load_inputs`` on the corrected configuration returns prompt v3 and this pack."""
    if prompt is None or not prompt.is_file():
        raise Incomplete("prompt v3 is not assembled")
    problem = assembly_problem(b.setup)
    if problem and problem[0] == "incomplete":
        raise Incomplete(problem[1])
    if problem:
        raise CheckFailed(problem[1])
    with tempfile.TemporaryDirectory(prefix="rag-load-inputs-") as root:
        outcome = run_in_domain(
            "load-inputs",
            {"pack": str(b.pack_path), "prompt": str(prompt), "artifact_root": root},
        )
    if outcome["status"] != "pass":
        raise CheckFailed(outcome.get("error", "load_inputs differs"), outcome)
    return outcome


def g1_provenance(setup: Setup, count_tokens: Callable[[str], int]) -> dict:
    b = Build(setup)
    checks = Checks()
    checks.run("G1.0", "build, corpus and receipts agree", lambda: check_consistency(b))
    checks.run("G1.1", "fetch receipt and blobs (AR-8)", lambda: check_fetch_blobs(b))
    checks.run("G1.2", "tier-1 verification (section 3.7)", lambda: check_tier1(b))
    checks.run("G1.3", "normalized and derived text hashes", lambda: check_text_hashes(b))
    checks.run("G1.4", "retrieved passages re-slice", lambda: check_reslice(b))
    checks.run("G1.5", "environment passages rebuild", lambda: check_environment(b, count_tokens))
    rebuilt: dict = {}

    def rebuild() -> dict:
        entries, _, blocked = b.environment(count_tokens)
        rebuilt["pack"] = rebuild_pack(b, entries, blocked)
        return rebuilt["pack"]

    def need_pack() -> dict:
        if "pack" not in rebuilt:
            try:
                rebuild()
            except Exception as exc:  # noqa: BLE001
                raise CheckFailed(
                    f"the pack cannot be rebuilt: {type(exc).__name__}: {exc}"
                ) from exc
        return rebuilt["pack"]

    checks.run(
        "G1.6", "static entries, tasks, rebuild", lambda: check_static_and_tasks(b, need_pack())
    )
    checks.run("G1.7", "load_pack and source-check", lambda: check_source_check(b))
    checks.run("G1.8", "context_for for all 50 pairs", lambda: check_context_for(b, need_pack()))
    checks.run(
        "G1.9",
        "load_inputs on the corrected configuration",
        lambda: check_load_inputs(b, setup.prompt),
    )
    return result_of(
        "G1", pack_identity(setup), checks.status, checks=checks.rows, inputs=b.reader.inputs()
    )


# ------------------------------------------------------------------ G2 determinism


class BuilderRunner:
    """Run ``build_rag_corpus.py`` or ``build_rag_pack.py`` in a fresh process with a hash seed."""

    def __init__(self, setup: Setup, tier2: Path):
        self.setup, self.tier2 = setup, tier2

    def __call__(self, seed: int, step: str, output: Path, corpus: Path | None) -> None:
        evidence, gguf = str(self.setup.evidence), str(self.setup.gguf)
        if step == "corpus":
            argv = [
                str(TOOL.with_name("build_rag_corpus.py")),
                "--config",
                str(self.setup.repository / bc.CONFIG_PATH),
                "--tier2",
                str(self.tier2),
                "--gguf",
                gguf,
                "--output",
                str(output),
                "--evidence",
                evidence,
            ]
        else:
            argv = [
                str(TOOL.with_name("build_rag_pack.py")),
                "--corpus",
                str(corpus),
                "--gguf",
                gguf,
                "--output",
                str(output),
                "--evidence",
                evidence,
            ]
        env = {**os.environ, "PYTHONHASHSEED": str(seed)}
        subprocess.run(
            [sys.executable, *argv],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=WORKER_TIMEOUT,
        )


def output_tree(directory: Path, skip: tuple[str, ...] = ()) -> dict[str, str]:
    """Relative path to sha256 for every file except ``run.json``, locks and ``skip`` entries."""
    out = {}
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory)
        if not path.is_file() or path.name in ("run.json", ".writer.lock"):
            continue
        if relative.parts[0] in skip:
            continue
        out[relative.as_posix()] = r.sha256_hex(path.read_bytes())
    return out


def g2_determinism(setup: Setup, run_builder: Callable[..., None]) -> dict:
    b = Build(setup)
    base = setup.gates / "determinism"
    if base.exists():
        raise GateError(f"output exists: {base}")
    base.mkdir(parents=True, exist_ok=False)
    pack_name = r.PACK_ID
    runs: dict[int, dict] = {}
    failures = []
    for seed in (0, 1):
        corpus_out = base / f"seed{seed}" / "corpus-v1"
        pack_out = base / f"seed{seed}" / pack_name
        runs[seed] = {"corpus": corpus_out, "pack": pack_out}
        for step, output, corpus in (("corpus", corpus_out, None), ("pack", pack_out, corpus_out)):
            try:
                run_builder(seed, step, output, corpus)
            except subprocess.CalledProcessError as exc:
                tail = (exc.stderr or "").strip().splitlines()[-1:] or ["no message"]
                failures.append({"seed": seed, "step": step, "error": tail[0]})
                break
            except Exception as exc:  # noqa: BLE001
                failures.append(
                    {"seed": seed, "step": step, "error": f"{type(exc).__name__}: {exc}"}
                )
                break
    comparison = {}
    if not failures:
        primary = {
            "corpus": output_tree(setup.corpus),
            "pack": output_tree(setup.build, ("gates",)),
        }
        for step in ("corpus", "pack"):
            trees = {
                "primary": primary[step],
                "seed0": output_tree(runs[0][step]),
                "seed1": output_tree(runs[1][step]),
            }
            names = sorted(set().union(*trees.values()))
            files = {n: {k: t.get(n) for k, t in trees.items()} for n in names}
            different = [n for n, v in files.items() if len(set(v.values())) != 1]
            comparison[step] = {
                "files": files,
                "identical_file_sets": len({tuple(sorted(t)) for t in trees.values()}) == 1,
                "different": different,
            }
    identical = bool(comparison) and all(
        c["identical_file_sets"] and not c["different"] for c in comparison.values()
    )
    return result_of(
        "G2",
        pack_identity(setup),
        "pass" if identical and not failures else "fail",
        seeds=[0, 1],
        excluded_from_comparison=["run.json"],
        builder_failures=failures,
        comparison=comparison,
        inputs=b.reader.inputs(),
    )


# ------------------------------------------------------------------ G3 tokenizer parity


def g3_parity(tokenizer, evidence: Path) -> dict:
    try:
        parity = qwen.parity(tokenizer, evidence)
    except (OSError, ValueError) as exc:
        raise GateError(f"tokenizer parity cannot run: {exc}") from exc
    return {"schema_version": SCHEMA, "name": GATE_NAMES["G3"], "tool": tool_record()} | parity


# ------------------------------------------------------------------ G4 token preflight


class _Capture:
    """The preflight client: record each request and answer with a non-result."""

    def __init__(self) -> None:
        self.requests: list[list[dict]] = []

    def generate(self, messages):
        from aia_mp1.model_client import AttemptResult

        self.requests.append(copy.deepcopy(messages))
        return AttemptResult(None, None, "preflight capture only", "PreflightCapture")


def g4_preflight(setup: Setup, count_wire: Callable[[list[dict]], int]) -> dict:
    """Render all 500 possible requests with the unchanged generation code and count them."""
    from aia_mp1 import generate, schemas
    from aia_mp1.config import RunConfig
    from aia_mp1.sources import context_for, load_pack

    identity = pack_identity(setup)
    if setup.prompt is None or not setup.prompt.is_file():
        return result_of("G4", identity, "incomplete", reason="prompt v3 is not assembled")
    problem = assembly_problem(setup)
    if problem:
        return result_of("G4", identity, problem[0], reason=problem[1])
    domain = schemas.DOMAIN
    if domain == "home-diy":
        raise GateError("the preflight needs the engineering or aec-course domain")
    pack_path = setup.build / bp.PACK_FILE
    prompt = setup.prompt.read_text(encoding="utf-8")
    pack = load_pack(pack_path)
    batches, slots, attempts = (
        r.PREFLIGHT_ENUMERATION[k] for k in ("batches", "slots", "attempts")
    )
    with tempfile.TemporaryDirectory(prefix="rag-preflight-") as root:
        try:
            config = RunConfig(**corrected_config(pack_path, setup.prompt, Path(root), domain))
        except ValueError as exc:
            raise GateError(f"the preflight configuration is refused: {exc}") from exc
        capture = _Capture()
        generate.generate_run(
            config, prompt, pack, count=slots, run_id="preflight-capture", client=capture
        )
    mismatches = []
    wires: dict[tuple[int, int], dict] = {}
    for index, messages in enumerate(capture.requests):
        slot, attempt = divmod(index, attempts)
        attempt += 1
        category = r.CATEGORIES[slot % len(r.CATEGORIES)]
        context = context_for(pack, category, slot // len(r.CATEGORIES))
        request = (
            f"Generate one new, distinct {category} task for slot {slot + 1}. "
            f"Variant: {r.PROMPT_VARIANT}. Attempt: {attempt}. "
            "Return the seven-field JSON object. Do not claim that the result has been verified."
        )
        expected = [
            {"role": "system", "content": prompt.replace("{category}", category)},
            {
                "role": "user",
                "content": json.dumps(
                    {"request": request, "untrusted_reference_context": context},
                    ensure_ascii=False,
                ),
            },
        ]
        if messages != expected:
            mismatches.append({"slot": slot, "attempt": attempt})
        wire = qwen.wire_messages(messages)
        wires[(slot, attempt)] = {
            "task_id": context["task"]["id"],
            "category": category,
            "wire_sha256": r.digest(wire),
            "prompt_tokens": int(count_wire(wire)),
        }
    expected_captures = slots * attempts
    rows = [
        {"batch": batch, "slot": slot, "attempt": attempt}
        | {k: wires[(slot, attempt)][k] for k in ("task_id", "wire_sha256", "prompt_tokens")}
        for batch in range(1, batches + 1)
        for slot in range(slots)
        for attempt in range(1, attempts + 1)
        if (slot, attempt) in wires
    ]
    distinct = len({w["wire_sha256"] for w in wires.values()})
    over = [row for row in rows if row["prompt_tokens"] > r.PROMPT_TOKEN_CAP]
    per_category = {}
    for category in r.CATEGORIES:
        values = [w["prompt_tokens"] for w in wires.values() if w["category"] == category]
        if values:
            per_category[category] = {
                "minimum": min(values),
                "median": statistics.median(values),
                "maximum": max(values),
            }
    maximum = max((row["prompt_tokens"] for row in rows), default=None)
    nfc = [s["id"] for s in pack["sources"] if unicodedata.normalize("NFC", s["text"]) != s["text"]]
    ok = (
        len(capture.requests) == expected_captures
        and not mismatches
        and len(rows) == batches * slots * attempts
        and distinct == expected_captures
        and not over
    )
    return result_of(
        "G4",
        identity,
        "pass" if ok else "fail",
        domain=domain,
        prompt_sha256=r.sha256_hex(setup.prompt.read_bytes()),
        cap=r.PROMPT_TOKEN_CAP,
        captured_requests=len(capture.requests),
        expected_captured_requests=expected_captures,
        capture_mismatches=preview(mismatches),
        enumerated_requests=len(rows),
        distinct_wires=distinct,
        requests_over_cap=len(over),
        maximum_prompt_tokens=maximum,
        per_category=per_category,
        nfc_changed_pack_texts=len(nfc),
        nfc_changed_pack_text_ids=nfc[:20],
        nfc_changed_prompt=unicodedata.normalize("NFC", prompt) != prompt,
        rows=rows,
    )


# ------------------------------------------------------------------ G7 retrieval metrics


def differences(a, b, path: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[str] = []
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                out.append(f"{path}/{key}")
            else:
                out += differences(a[key], b[key], f"{path}/{key}")
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, f"{path}[{i}]")]
    return [] if a == b else [path or "/"]


def judge_metrics(measured: Mapping, floors: Mapping) -> list[str]:
    """The floors apply to every category separately; uneven treatment stops the build."""
    problems = []
    for category in r.CATEGORIES:
        values = measured["per_category"][category]
        for name, value in (
            ("holdout_hit_at_3", values["holdout"]["hit_at_3"]),
            ("gain", values["gain"]),
            ("stability", values["stability"]),
        ):
            if value is None or value < floors[name]:
                problems.append(f"{category}: {name} {value} is below the floor {floors[name]}")
    uneven = measured["uneven_treatment"]
    if uneven["empty_indexes"]:
        problems.append(f"empty category indexes: {uneven['empty_indexes']}")
    if uneven["categories_without_passages"]:
        problems.append(
            f"categories without a retrieved passage: {uneven['categories_without_passages']}"
        )
    return problems


FLOOR_KEYS = ("floors", "floor_results", "floors_pass")


def g7_metrics(setup: Setup, floors: Mapping | None = None) -> dict:
    """Recompute every metric from the corpus, chunk table and pack; compare with the report."""
    b = Build(setup)
    floors = dict(floors if floors is not None else r.METRIC_FLOORS)
    passages = {p["id"]: p for p in b.receipt["passages"]}
    selections: dict[str, list[r.Chunk]] = {}
    selection_problems = []
    for task in b.pack["tasks"]:
        chosen = []
        for ref in task["source_refs"][2:]:
            chunk = b.chunks_by_key.get(passages.get(ref, {}).get("chunk_key"))
            if chunk is None:
                selection_problems.append(
                    f"{task['id']}: {ref} is not a passage of the chunk table"
                )
            else:
                chosen.append(chunk)
        selections[task["id"]] = chosen
    measured = json.loads(
        r.record_json(
            r.retrieval_metrics(
                b.base["tasks"], b.chunks_by_category, b.blocked_lines(), selections
            )
        )
    )
    tiers = [
        b.files[passages[s["id"]]["file_key"]]["tier"]
        for s in b.pack["sources"]
        if s["id"] in passages
    ]
    shares = r.tier_shares(tiers)
    reported = copy.deepcopy(b.report.get("metrics", {}))
    reported_shares = reported.pop("tier_shares", None)
    mismatches = differences(
        {k: v for k, v in measured.items() if k not in FLOOR_KEYS},
        {k: v for k, v in reported.items() if k not in FLOOR_KEYS},
    )
    if reported_shares != shares:
        mismatches.append("/tier_shares")
    problems = selection_problems + judge_metrics(measured, floors)
    if mismatches:
        problems.append(f"{len(mismatches)} reported values differ from the recomputed values")
    floor_results = {
        c: {
            "holdout_hit_at_3": _at_least(
                measured["per_category"][c]["holdout"]["hit_at_3"], floors["holdout_hit_at_3"]
            ),
            "gain": _at_least(measured["per_category"][c]["gain"], floors["gain"]),
            "stability": _at_least(measured["per_category"][c]["stability"], floors["stability"]),
        }
        for c in r.CATEGORIES
    }
    return result_of(
        "G7",
        pack_identity(setup),
        "pass" if not problems else "fail",
        floors=floors,
        floor_results=floor_results,
        uneven_treatment=measured["uneven_treatment"],
        report_values_match=not mismatches,
        report_mismatches=preview(mismatches),
        problems=problems,
        per_category=measured["per_category"],
        combined_index=measured["combined_index"],
        tier_shares=shares,
        tasks=measured["tasks"],
        inputs=b.reader.inputs(),
    )


def _at_least(value, floor) -> bool:
    return value is not None and value >= floor


# ------------------------------------------------------------------ G6 dry run and G8 baseline


def g6_dry_run(setup: Setup, artifact_root: Path | None = None) -> dict:
    """Run the final pack through collect, gate, cohort and assessment with a fake client."""
    identity = pack_identity(setup)
    if setup.prompt is None or not setup.prompt.is_file():
        return result_of("G6", identity, "incomplete", reason="prompt v3 is not assembled")
    problem = assembly_problem(setup)
    if problem:
        return result_of("G6", identity, problem[0], reason=problem[1])
    outcome = run_in_domain(
        "dry-run",
        {
            "pack": str(setup.build / bp.PACK_FILE),
            "prompt": str(setup.prompt),
            "repository": str(setup.repository),
            "evidence": str(setup.evidence),
            "artifact_root": str(artifact_root) if artifact_root is not None else None,
        },
    )
    return result_of("G6", identity, outcome.pop("status"), **outcome)


@dataclass
class Baseline:
    """What §9 G8 expects of the frozen AEC baseline; tests substitute a synthetic cohort."""

    cohort_root: Path
    cohort_id: str = "aec-course-baseline"
    cohort_sha256: str = "d81078282a8d4c8abed0edb0a446066ab9117ad2c346d966dd57b90e2a634422"
    rule_identity: str = PINNED_MODULES["gate.py"]
    prompt_v1_digest: str = "f19b8b9032745fc14af03cfbe314a2a5f2d2e7d3e0c5855e4962ed39a23a42eb"
    modules: dict = field(default_factory=lambda: dict(PINNED_MODULES))


def g8_baseline(setup: Setup, baseline: Baseline | None = None) -> dict:
    from aia_mp1.tracing import digest

    baseline = baseline or Baseline(setup.evidence / "aec-course")
    checks = Checks()

    def modules() -> dict:
        root = setup.repository / "src" / "aia_mp1"
        found = {}
        for name, want in baseline.modules.items():
            path = root / name
            found[name] = r.sha256_hex(path.read_bytes()) if path.is_file() else None
        wrong = sorted(n for n, v in found.items() if v != baseline.modules[n])
        if wrong:
            raise CheckFailed(f"{len(wrong)} pinned modules differ", {"modules": wrong})
        return {"modules": found}

    def prompt() -> dict:
        path = setup.repository / PROMPT_V1
        found = digest(path.read_text(encoding="utf-8"))
        if found != baseline.prompt_v1_digest:
            raise CheckFailed("the digest of prompt v1 differs", {"found": found})
        return {"digest": found}

    outcome = run_in_domain(
        "baseline",
        {
            "cohort_root": str(baseline.cohort_root),
            "cohort_id": baseline.cohort_id,
            "cohort_sha256": baseline.cohort_sha256,
            "rule_identity": baseline.rule_identity,
        },
    )
    checks.rows.extend(outcome["checks"])
    checks.run("G8.4", "the first twelve rows of section 1.1 match byte for byte", modules)
    checks.run("G8.3b", "the digest of prompt v1", prompt)
    return result_of(
        "G8",
        pack_identity(setup),
        checks.status,
        checks=checks.rows,
        cohort_id=baseline.cohort_id,
        fields_reported="pass or fail and hashes only",
    )


# ------------------------------------------------------------------ workers (AIA_MP1_DOMAIN=aec-course)


def _fake_fields(n: int) -> dict:
    """§9 G6 synthetic item; ``n`` is the slot number parsed from the request text."""
    return {
        "question": f"How can synthetic dry-run fixture {n} confirm unit consistency "
        "before saving results?",
        "answer": f"Open a copy of synthetic dry-run fixture {n}, confirm its declared unit "
        "system against a known reference value, and save the checked copy separately so "
        "the original fixture stays unchanged.",
        "equipment_problem": f"Synthetic dry-run fixture {n} needs a unit consistency check "
        "before results are saved.",
        "tools_required": ["Synthetic offline checker"],
        "steps": [
            "Open a copy of the synthetic fixture.",
            "Compare the declared units with the known reference value.",
            "Save the checked copy separately.",
        ],
        "safety_info": "Verify the unit system against the known reference value before "
        "saving, because a silent unit mismatch can corrupt every derived result.",
        "tips": [
            "Keep the reference value in a separate record so later unit changes can be audited."
        ],
    }


class _FakeClient:
    def __init__(self, model: str, interrupt: int | None = None) -> None:
        self.model, self.interrupt, self.calls = model, interrupt, 0

    def generate(self, messages):
        from aia_mp1.model_client import AttemptResult
        from aia_mp1.schemas import QAItem

        self.calls += 1
        if self.calls == self.interrupt:
            raise KeyboardInterrupt
        request = json.loads(messages[-1]["content"])["request"]
        n = int(re.search(r"for slot (\d+)\.", request).group(1))
        item = QAItem(**_fake_fields(n))
        return AttemptResult(item, item.model_dump(), None, None, self.model)


def _flip(text: str) -> str:
    return text[:-1] + ("x" if text[-1] != "x" else "y")


def _refused(call: Callable[[], object], message: str) -> str:
    try:
        call()
    except ValueError as exc:
        if message not in str(exc):
            raise CheckFailed(f"refused, but not for the expected reason: {exc}") from exc
        return str(exc)
    raise CheckFailed("the call was not refused")


def _task_load_inputs(p: dict) -> dict:
    from aia_mp1.config import RunConfig, load_inputs
    from aia_mp1.sources import load_pack

    try:
        pack, prompt = Path(p["pack"]), Path(p["prompt"])
        config = RunConfig(**corrected_config(pack, prompt, Path(p["artifact_root"])))
        text, loaded = load_inputs(config)
        if text != prompt.read_text(encoding="utf-8") or loaded != load_pack(pack):
            return {"status": "fail", "error": "load_inputs returned other inputs"}
        return {
            "status": "pass",
            "prompt_sha256": r.sha256_hex(prompt.read_bytes()),
            "pack_digest": r.digest(loaded),
            "credential_read": os.environ.get(UNUSED_KEY_ENV) is not None,
            "api_key_env": UNUSED_KEY_ENV,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "fail", "error": f"{type(exc).__name__}: {exc}"}


def _task_dry_run(p: dict) -> dict:
    from aia_mp1.cohort import freeze_cohort, load_cohort
    from aia_mp1.collection import collect
    from aia_mp1.config import RunConfig, load_inputs
    from aia_mp1.schemas import CATEGORIES
    from aia_mp1.sources import context_for, load_pack
    from aia_mp1.tracing import digest, read_records

    pack_path, prompt_path = Path(p["pack"]), Path(p["prompt"])
    if p.get("artifact_root"):
        root, discard = Path(p["artifact_root"]), False
        root.mkdir(parents=True, exist_ok=False)
    else:
        root, discard = Path(tempfile.mkdtemp(prefix="rag-dry-run-")), True
    resolved = root.resolve()
    for guarded in (REPO, Path(p["repository"]), Path(p["evidence"])):
        guarded = guarded.resolve()
        if resolved == guarded or guarded in resolved.parents:
            raise ValueError(f"the dry-run root {root} is inside {guarded}")
    state: dict = {}
    checks = Checks()
    try:
        pack = load_pack(pack_path)
    except Exception as exc:  # noqa: BLE001 - an invalid pack is the gate's finding
        if discard:
            shutil.rmtree(root, ignore_errors=True)
        row = {"id": "G6.0", "name": "the pack validates", "status": "fail"}
        return {
            "status": "fail",
            "fake_client": True,
            "checks": [row | {"detail": {"error": f"{type(exc).__name__}: {exc}"}}],
        }
    prompt = prompt_path.read_text(encoding="utf-8")
    primary = root / "primary"
    primary.mkdir()
    config = RunConfig(**corrected_config(pack_path, prompt_path, primary))
    run_id = f"{DRY_COLLECTION}-b01"

    def collection() -> dict:
        text, loaded = load_inputs(config)
        if text != prompt or loaded != pack:
            raise CheckFailed("load_inputs returned other inputs")
        client = _FakeClient(config.model)
        summary = collect(config, DRY_COLLECTION, client)
        batch = summary["batches"][0] if summary["batches"] else {}
        facts = {
            "status": summary["status"],
            "batches": len(summary["batches"]),
            "calls": client.calls,
            "started_attempts": summary["started_attempts"],
            "initial_attempt_valid_count": summary["initial_attempt_valid_count"],
            "counts": summary["counts"],
            "gate_status": batch.get("gate_status"),
        }
        if (
            facts["status"] != "ready"
            or facts["batches"] != 1
            or facts["calls"] != 50
            or facts["initial_attempt_valid_count"] != 50
            or facts["counts"] != dict.fromkeys(CATEGORIES, 10)
            or facts["gate_status"] != "passed"
        ):
            raise CheckFailed("the dry-run collection did not reach ready in one batch", facts)
        state["summary"] = summary
        return facts

    def requests() -> dict:
        events = read_records(primary / run_id / "events.jsonl")
        records = read_records(primary / run_id / "data.jsonl")
        wrong = []
        for event in events:
            context = context_for(pack, event["category"], event["slot"] // len(CATEGORIES))
            user = json.dumps(
                {"request": event["request"], "untrusted_reference_context": context},
                ensure_ascii=False,
            )
            if (
                event["input"][-1]["content"] != user
                or event["reference_context"] != context
                or event["input"][0]["content"] != prompt.replace("{category}", event["category"])
            ):
                wrong.append(event["attempt_id"])
        for record in records:
            slot = int(record["item_id"].rsplit("-item-", 1)[1]) - 1
            context = context_for(pack, record["category"], slot // len(CATEGORIES))
            if (
                record["source_refs"] != context["task"]["source_refs"]
                or record["reference_context"] != context
            ):
                wrong.append(record["item_id"])
        if len(events) != 50 or len(records) != 50 or wrong:
            raise CheckFailed(
                "requests or records differ from the pack",
                {"events": len(events), "records": len(records), "differing": len(wrong)},
            )
        return {"events": len(events), "records": len(records)}

    def cohort() -> dict:
        manifest = freeze_cohort(primary, DRY_COLLECTION, DRY_COHORT)
        loaded = load_cohort(primary, DRY_COHORT)
        if loaded["sha256"] != manifest["sha256"] or loaded["summary"] != state["summary"]:
            raise CheckFailed("the loaded cohort differs from the frozen cohort")
        state["cohort"] = loaded
        return {"cohort_sha256": loaded["sha256"], "members": len(loaded["summary"]["members"])}

    def assessment() -> dict:
        import importlib.util

        if importlib.util.find_spec("aia_mp1.assessment_v2") is None:
            return {"available": False}
        from aia_mp1.assessment_v2 import create_assessment_v2, load_assessment_v2

        created = create_assessment_v2(
            primary, DRY_COHORT, DRY_ASSESSMENT, declare_no_prior_reviews=True
        )
        loaded = load_assessment_v2(primary, DRY_ASSESSMENT)
        return {
            "available": True,
            "manifest_sha256": created.get("manifest_sha256"),
            "loaded_manifest_sha256": loaded[1].get("manifest_sha256"),
        }

    def resume() -> dict:
        work = root / "inputs"
        work.mkdir()
        prompt_copy, pack_copy = work / "prompt.md", work / "pack.json"
        shutil.copyfile(prompt_path, prompt_copy)
        shutil.copyfile(pack_path, pack_copy)
        cfg = RunConfig(**corrected_config(pack_copy, prompt_copy, root / "resume"))
        try:
            collect(cfg, "dry-rag-002", _FakeClient(cfg.model, interrupt=3))
        except KeyboardInterrupt:
            pass
        else:
            raise CheckFailed("the interrupted collection did not stop")

        def again():
            return collect(cfg, "dry-rag-002", _FakeClient(cfg.model), resume=True)

        original_prompt = prompt_copy.read_bytes()
        prompt_copy.write_bytes(original_prompt + b" ")
        by_prompt = _refused(again, RESUME_REFUSAL)
        prompt_copy.write_bytes(original_prompt)
        original_pack = json.loads(pack_copy.read_text(encoding="utf-8"))
        edited = copy.deepcopy(original_pack)
        edited["sources"][-1]["text"] = _flip(edited["sources"][-1]["text"])
        edited["sources"][-1]["content_sha256"] = digest(edited["sources"][-1]["text"])
        pack_copy.write_text(r.pack_json(edited), encoding="utf-8")
        by_passage = _refused(again, RESUME_REFUSAL)
        pack_copy.write_text(r.pack_json(original_pack), encoding="utf-8")
        # Control: with both inputs restored the identity matches, so only the next guard stops it.
        control = _refused(again, "unknown request outcome")
        return {
            "prompt_byte_refused": by_prompt,
            "passage_character_refused": by_passage,
            "unchanged_inputs_reach_the_outcome_guard": control,
        }

    def tampered_pack() -> dict:
        bad = copy.deepcopy(json.loads(pack_path.read_text(encoding="utf-8")))
        bad["sources"][-1]["text"] = _flip(bad["sources"][-1]["text"])
        bad_path = root / "inputs" / "pack-bad.json"
        bad_path.write_text(r.pack_json(bad), encoding="utf-8")
        cfg = RunConfig(**corrected_config(bad_path, prompt_path, root / "bad"))
        client = _FakeClient(cfg.model)
        message = _refused(lambda: collect(cfg, "dry-rag-003", client), "content hash differs")
        if client.calls or (root / "bad" / "collections").exists():
            raise CheckFailed("a call or a collection preceded the refusal")
        return {"refused": message, "calls": client.calls}

    def tampered_event() -> dict:
        duplicate = root / "primary-copy"
        shutil.copytree(primary, duplicate)
        load_cohort(duplicate, DRY_COHORT)  # control: the unedited copy loads
        path = duplicate / run_id / "events.jsonl"
        lines = path.read_text(encoding="utf-8").split("\n")[:-1]
        first = json.loads(lines[0])
        first["reference_context"]["sources"][-1]["text"] = _flip(
            first["reference_context"]["sources"][-1]["text"]
        )
        lines[0] = json.dumps(first, ensure_ascii=False, allow_nan=False)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {"refused": _refused(lambda: load_cohort(duplicate, DRY_COHORT), "")}

    try:
        checks.run("G6.1", "collect reaches ready after one batch", collection)
        checks.run("G6.2", "requests, contexts and source references", requests)
        checks.run("G6.3", "freeze_cohort and load_cohort", cohort)
        checks.run("G6.4", "create_assessment_v2 and load_assessment_v2", assessment)
        checks.run("G6.5", "resume with a changed prompt byte or passage is refused", resume)
        checks.run("G6.6", "a pack edit without its hash is refused before any call", tampered_pack)
        checks.run("G6.7", "an edited recorded event is refused by load_cohort", tampered_event)
    finally:
        if discard:
            shutil.rmtree(root, ignore_errors=True)
    return {
        "status": checks.status,
        "fake_client": True,
        "checks": checks.rows,
        "model": qwen.SERVED_MODEL,
        "hashes": {
            "pack_file_sha256": r.sha256_hex(pack_path.read_bytes()),
            "prompt_sha256": r.sha256_hex(prompt_path.read_bytes()),
            "cohort_sha256": state.get("cohort", {}).get("sha256"),
        },
        "root": "temporary root, discarded" if discard else str(root),
    }


def _task_baseline(p: dict) -> dict:
    from aia_mp1.cohort import load_cohort
    from aia_mp1.collection import rule_identity
    from aia_mp1.sources import context_for, validate_pack

    checks = Checks()
    held: dict = {}

    def loads() -> dict:
        held["cohort"] = load_cohort(Path(p["cohort_root"]), p["cohort_id"])
        return {"cohort_id": p["cohort_id"]}

    def sha() -> dict:
        if held["cohort"]["sha256"] != p["cohort_sha256"]:
            raise CheckFailed("the cohort sha256 differs", {"found": held["cohort"]["sha256"]})
        return {"cohort_sha256": p["cohort_sha256"]}

    def contexts() -> dict:
        cohort = held["cohort"]
        members = cohort["summary"]["members"]
        pack = validate_pack(cohort["identity"]["sources"])
        wrong = 0
        for record in members:
            slot = int(record["item_id"].rsplit("-item-", 1)[1]) - 1
            context = context_for(pack, record["category"], slot // 5)
            wrong += record.get("reference_context") != context
        if len(members) != 50 or wrong:
            raise CheckFailed(
                "recomputed contexts differ", {"members": len(members), "differing": wrong}
            )
        return {"members": len(members)}

    def rules() -> dict:
        found = rule_identity()
        if found != p["rule_identity"]:
            raise CheckFailed("rule_identity differs", {"found": found})
        return {"rule_identity": found}

    def after_load(function):
        def run():
            if "cohort" not in held:
                raise CheckFailed("the cohort did not load")
            return function()

        return run

    checks.run("G8.1", "load_cohort passes", loads)
    checks.run("G8.2", "the cohort sha256", after_load(sha))
    checks.run("G8.3", "context_for recomputed for all 50 members", after_load(contexts))
    checks.run("G8.3a", "rule_identity", rules)
    return {"checks": checks.rows}


def worker(task: str) -> int:
    handlers = {
        "load-inputs": _task_load_inputs,
        "dry-run": _task_dry_run,
        "baseline": _task_baseline,
    }
    if task not in handlers:
        print(f"error: unknown worker task {task}", file=sys.stderr)
        return 2
    print(json.dumps(handlers[task](json.load(sys.stdin)), ensure_ascii=False))
    return 0


# ------------------------------------------------------------------ running, writing, CLI


@dataclass
class Parts:
    """The injectable pieces; the CLI fills them from ``--gguf`` and the real builders."""

    count_tokens: Callable[[str], int] | None = None
    tokenizer: object = None
    count_wire: Callable[[list[dict]], int] | None = None
    run_builder: Callable[..., None] | None = None
    floors: Mapping | None = None
    baseline: Baseline | None = None
    dry_root: Path | None = None


GATE_RUNNERS: dict[str, Callable[[Setup, Parts], dict]] = {
    "G1": lambda s, p: g1_provenance(s, p.count_tokens),
    "G2": lambda s, p: g2_determinism(s, p.run_builder),
    "G3": lambda s, p: g3_parity(p.tokenizer, s.evidence),
    "G4": lambda s, p: g4_preflight(s, p.count_wire),
    "G6": lambda s, p: g6_dry_run(s, p.dry_root),
    "G7": lambda s, p: g7_metrics(s, p.floors),
    "G8": lambda s, p: g8_baseline(s, p.baseline),
}


def gate_path(setup: Setup, gate: str) -> Path:
    return setup.gates / f"{GATE_NAMES[gate]}.json"


def refuse_existing(setup: Setup, gates: list[str], extra: tuple[str, ...] = ()) -> None:
    paths = [gate_path(setup, g) for g in gates] + [setup.gates / name for name in extra]
    if "G2" in gates:
        paths.append(setup.gates / "determinism")
    for path in paths:
        if path.exists() or path.is_symlink():
            raise GateError(f"output exists: {path}")


def check_build_dir(setup: Setup) -> None:
    if not setup.build.is_dir():
        raise GateError(f"build directory {setup.build} does not exist")
    if setup.build.is_symlink():
        raise GateError(f"symlinked build directory {setup.build} is refused")


def run_gates(setup: Setup, parts: Parts, gates: list[str], *, summary: bool = False) -> dict:
    """Run the named gates under one lock, writing each result as soon as it exists."""
    check_build_dir(setup)
    refuse_existing(setup, gates, ("gates.json",) if summary else ())
    setup.gates.mkdir(exist_ok=True)
    results: dict[str, dict] = {}
    with bc.writer_lock(setup.gates):
        for gate in gates:
            try:
                result = GATE_RUNNERS[gate](setup, parts)
            except GateError as error:
                if not summary:
                    raise
                # Under ``all`` an input error is recorded, so gates.json can still be written.
                result = result_of(gate, None, "error", reason=str(error))
            results[gate] = {
                "name": GATE_NAMES[gate],
                "file": f"gates/{GATE_NAMES[gate]}.json",
                "status": result["status"],
                "sha256": r.write_new(gate_path(setup, gate), r.record_json(result)),
            }
        if summary:
            gates_json = {
                "schema_version": GATES_SCHEMA,
                "pack_id": r.PACK_ID,
                "tool": tool_record(),
                "build": pack_identity(setup),
                "gates": dict(results),
                "leakage_scan": leakage_scan(setup),
                "all_passed": all(v["status"] == "pass" for v in results.values()),
            }
            gates_json["all_passed_with_g5"] = (
                gates_json["all_passed"] and gates_json["leakage_scan"]["status"] == "pass"
            )
            r.write_new(setup.gates / "gates.json", r.record_json(gates_json))
            results["summary"] = gates_json
    return results


def leakage_scan(setup: Setup) -> dict:
    """G5 belongs to ``scan_rag_leakage.py``; report its file if it already exists."""
    path = setup.gates / LEAKAGE_FILE
    if not path.is_file():
        return {
            "name": "leakage-scan",
            "file": f"gates/{LEAKAGE_FILE}",
            "status": "not_run",
            "sha256": None,
        }
    data = path.read_bytes()
    try:
        scan = json.loads(data)
        status = scan.get("status", "unknown")
    except json.JSONDecodeError:
        scan, status = {}, "unreadable"
    if status == "pass" and not _scan_matches(setup, scan):
        status = "stale"
    return {
        "name": "leakage-scan",
        "file": f"gates/{LEAKAGE_FILE}",
        "status": status,
        "sha256": r.sha256_hex(data),
    }


def _scan_matches(setup: Setup, scan: dict) -> bool:
    """Whether G5 scanned this pack, this prompt and this guidance sidecar."""
    recorded = scan.get("inputs") if isinstance(scan.get("inputs"), dict) else {}
    current = {
        "pack": setup.build / bp.PACK_FILE,
        "prompt_v3": setup.prompt,
        "guidance_provenance": setup.build.parent / "prompt-v3" / "guidance-provenance.json",
    }
    for name, path in current.items():
        if path is None:
            continue  # a gate run without --prompt cannot compare the prompt
        if not path.is_file():
            return False
        entry = recorded.get(name)
        if not isinstance(entry, dict) or entry.get("sha256") != r.sha256_hex(path.read_bytes()):
            return False
    return True


COMMANDS = {
    "provenance": "G1",
    "determinism": "G2",
    "tokenizer-parity": "G3",
    "token-preflight": "G4",
    "dry-run": "G6",
    "retrieval-metrics": "G7",
    "baseline": "G8",
}
ALIASES = {gate.lower(): name for name, gate in COMMANDS.items()}
NEEDS_GGUF = {"G1", "G2", "G3", "G4"}
NEEDS_PROMPT = {"G4", "G6"}


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__)
    commands = top.add_subparsers(dest="command", required=True)
    for name, gate in [*COMMANDS.items(), ("all", None)]:
        sub = commands.add_parser(
            name,
            aliases=[gate.lower()] if gate else [],
            help=f"gate {gate} ({name})" if gate else "gates G1-G4 and G6-G8, then gates.json",
        )
        sub.add_argument("--build", type=Path, required=True, help="the pack directory")
        sub.add_argument(
            "--prompt", type=Path, required=name == "all", help="prompts/generator-assessed-v3.md"
        )
        sub.add_argument("--gguf", type=Path, help="the pinned Qwen3 GGUF (G1-G4)")
        sub.add_argument("--evidence", type=Path, default=bc.DEFAULT_EVIDENCE)
        sub.add_argument("--repository", type=Path, default=REPO)
        sub.add_argument("--corpus", type=Path, help="default: corpus-v1 beside the pack directory")
        sub.add_argument(
            "--tier2", type=Path, help="default: the corpus manifest's fetch directory"
        )
    return top


def default_parts(setup: Setup, gates: list[str]) -> Parts:
    parts = Parts()
    if NEEDS_GGUF & set(gates):
        if setup.gguf is None:
            raise GateError("--gguf is required for gates G1-G4")
        tokenizer = qwen.load_tokenizer(setup.gguf)
        parts.tokenizer = tokenizer
        parts.count_tokens = tokenizer.count_tokens
        parts.count_wire = lambda wire: tokenizer.count_tokens(
            tokenizer.render(wire), parse_special=True
        )
    if "G2" in gates:
        tier2 = setup.tier2 or Build(setup).reader.roots["tier2"]
        parts.run_builder = BuilderRunner(setup, tier2)
    return parts


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if args_list[:1] == ["_worker"]:
        return worker(args_list[1] if len(args_list) > 1 else "")
    args = parser().parse_args(args_list)
    command = ALIASES.get(args.command, args.command)
    gates = list(GATE_NAMES) if command == "all" else [COMMANDS[command]]
    try:
        setup = Setup(
            build=args.build,
            evidence=args.evidence,
            repository=args.repository,
            corpus=args.corpus,
            tier2=args.tier2,
            prompt=args.prompt,
            gguf=args.gguf,
        )
        check_build_dir(setup)
        if NEEDS_PROMPT & set(gates) and setup.prompt is None and command != "all":
            raise GateError("--prompt is required for this gate")
        refuse_existing(setup, gates, ("gates.json",) if command == "all" else ())
        results = run_gates(setup, default_parts(setup, gates), gates, summary=command == "all")
    except (GateError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    for gate in gates:
        print(f"{gate} {GATE_NAMES[gate]}: {results[gate]['status']}")
    if command == "all":
        summary = results["summary"]
        print(f"G5 leakage-scan: {summary['leakage_scan']['status']} (scan_rag_leakage.py)")
        print(f"all_passed: {summary['all_passed']}")
        return 0 if summary["all_passed"] else 1
    return 0 if results[gates[0]]["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
