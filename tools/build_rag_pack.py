"""Step 5b-c of docs/AEC-RAG-PACK.md: retrieval, environment passages, pack, receipt, report.

Reads the corpus directory (checked against its receipt), the admission table, the
engineering-v1 base pack and the pinned environment files; ranks every category's chunks
with Okapi BM25 plus the identifier bonus for each task brief; and writes the reference pack
``engineering-v1-rag-bm25-v1.json``, ``build-receipt.json``, ``retrieval-report.json`` and
``run.json`` into a new directory. The unchanged ``aia_mp1.sources`` validator must accept
the pack before it is written. No network, no model, nothing retrieved at generation time.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from build_rag_corpus import (
    CORPUS_RECEIPT_SCHEMA,
    CORPUS_SCHEMA,
    DEFAULT_EVIDENCE,
    REPO,
    BuildError,
    InputReader,
    _abs,
    _json,
    code_hashes,
    load_counter,
    run_in_new_directory,
)

from aia_mp1 import retrieval as r
from aia_mp1.sources import context_for, validate_pack

PACK_FILE = f"{r.PACK_ID}.json"
BUILD_RECEIPT_SCHEMA = "rag-build-receipt-v1"
REPORT_SCHEMA = "rag-retrieval-report-v1"
TOP_CANDIDATES = 10


def _file_text(reader: InputReader, config: dict, record: dict) -> str:
    """The normalized or derived text of one manifest file, re-verified against its hashes."""
    evidence = reader.roots["evidence"]
    derived = record.get("derived")
    if derived and derived["kind"] == "pdf_text":
        data = reader.read(
            evidence / config["tier1"]["cheat_sheet_text"]["path"],
            "tier1_cheat_sheet_text",
            sha256=derived["text_sha256"],
        )
        return data.decode("utf-8")
    if record["tier"] == "T1":
        data = reader.read(
            evidence / record["t1_snapshot"]["path"],
            "tier1",
            sha256=record["t1_snapshot"]["sha256"],
        )
        text = data.decode("utf-8")
    else:
        stored = f"files/{record['repo_key']}/{record['path']}"
        text = r.n1(reader.read(reader.path("tier2", stored), "tier2", sha256=record["raw_sha256"]))
    if r.sha256_hex(text.encode("utf-8")) != record["normalized_sha256"]:
        raise BuildError(f"{record['file_key']}: normalized text differs from the manifest")
    if derived and derived["kind"] == "sandcastle_text":
        text = r.sandcastle_text(text)
        if r.sha256_hex(text.encode("utf-8")) != derived["text_sha256"]:
            raise BuildError(f"{record['file_key']}: derived text differs from the manifest")
    return text


def _license_evidence(record: dict) -> str:
    return "; ".join(f["evidence_path"] for f in record["license_files"])


def _notice(records: list[dict], kind: str) -> str | None:
    for record in records:
        for notice in record.get("notices", []):
            if notice["kind"] == kind:
                return notice["text"]
    return None


def build(
    reader: InputReader, output: Path, count_tokens: Callable[[str], int], tokenizer: dict
) -> dict:
    corpus = reader.roots["corpus"]
    manifest_bytes = reader.read(corpus / "corpus-manifest.json", "corpus_manifest")
    chunks_bytes = reader.read(corpus / "chunks.jsonl", "corpus_chunks")
    receipt_bytes = reader.read(corpus / "corpus-receipt.json", "corpus_receipt")
    corpus_receipt = _json(receipt_bytes, "corpus receipt")
    manifest = _json(manifest_bytes, "corpus manifest")
    if corpus_receipt.get("schema_version") != CORPUS_RECEIPT_SCHEMA:
        raise BuildError("unsupported corpus receipt schema")
    if manifest.get("schema_version") != CORPUS_SCHEMA:
        raise BuildError("unsupported corpus manifest schema")
    if corpus_receipt.get("tokenizer") != tokenizer:
        raise BuildError("the corpus was counted with a different tokenizer than this pack build")
    outputs = corpus_receipt.get("outputs", {})
    if outputs.get("corpus-manifest.json") != r.sha256_hex(manifest_bytes) or outputs.get(
        "chunks.jsonl"
    ) != r.sha256_hex(chunks_bytes):
        raise BuildError("the corpus files differ from the corpus receipt")
    repository, evidence = reader.roots["repository"], reader.roots["evidence"]
    config_bytes = reader.read(
        repository / manifest["sources_config"]["path"],
        "sources_config",
        sha256=manifest["sources_config"]["sha256"],
    )
    config = _json(config_bytes, "rag-sources")
    base_bytes = reader.read(
        evidence / manifest["engineering_v1"]["path"],
        "engineering_v1",
        sha256=manifest["engineering_v1"]["sha256"],
    )
    base = _json(base_bytes, "engineering-v1")
    if r.digest(base) != manifest["engineering_v1"]["digest"]:
        raise BuildError("engineering-v1 digest differs from the corpus manifest")
    verification = _json(
        reader.read(
            evidence / manifest["source_verification"]["path"],
            "source_verification",
            sha256=manifest["source_verification"]["sha256"],
        ),
        "source-verification",
    )
    reader.allow_upstream(
        k[len("upstream/") :]
        for k in verification.get("upstream_files_sha256", {})
        if k.startswith("upstream/")
    )
    fetch_relative = manifest["fetch_receipt"]["path"]
    reader.roots["tier2"] = evidence / Path(fetch_relative).parent
    reader.read(
        evidence / fetch_relative, "fetch_receipt", sha256=manifest["fetch_receipt"]["sha256"]
    )

    files = {f["file_key"]: f for f in manifest["files"]}
    repos = {x["repo_key"]: x for x in manifest["repositories"]}
    config_repos = {x["repo_key"]: x for x in config["repositories"]}
    rows = [json.loads(line) for line in chunks_bytes.decode("utf-8").split("\n") if line]
    chunks_by_category: dict[str, list[r.Chunk]] = {c: [] for c in r.CATEGORIES}
    for row in rows:
        if row["content_sha256"] != r.digest(row["text"]) or row["chunk_key"] != (
            f"{row['file_key']}#L{row['start']}-L{row['end']}"
        ):
            raise BuildError(f"chunk table row {row.get('chunk_key')} is inconsistent")
        if files.get(row["file_key"], {}).get("category") != row["category"]:
            raise BuildError(f"chunk {row['chunk_key']} names an unknown file")
        chunks_by_category[row["category"]].append(r.Chunk.from_row(row))

    # §6.5 environment passages
    environment, blocked, env_receipt = {}, {}, []
    for spec in config["environment_passages"]:
        category = spec["category"]
        repo = repos[spec["repo_key"]]
        records, blocks = [], []
        for block in spec["blocks"]:
            record = files.get(block["file_key"])
            if record is None or record["repo_key"] != spec["repo_key"]:
                raise BuildError(f"{spec['id']}: {block['file_key']} is not an admitted file")
            if not {"environment", "passage"} & set(record["role"].split("+")):
                raise BuildError(
                    f"{spec['id']}: {block['file_key']} is neither an environment "
                    "nor a passage file"
                )
            lines = r.parse_ranges(block["lines"])
            blocks.append(
                r.environment_block(
                    owner=repo["owner"],
                    repo=repo["repo"],
                    commit=repo["commit"],
                    path=record["path"],
                    derived=record.get("derived") is not None,
                    text=_file_text(reader, config, record),
                    lines=lines,
                )
            )
            records.append(record)
            blocked.setdefault(category, {}).setdefault(block["file_key"], set()).update(lines)
        text, tokens = r.environment_passage(spec["target"], blocks, count_tokens)
        source = config_repos[spec["repo_key"]]
        template = source["attribution"].get("environment", source["attribution"]["passage"])
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
            notice=_notice(records, "cheat_sheet_notice"),
            regents_notice=_notice(records, "regents_notice"),
        )
        if spec["id"] != f"{r.CATEGORY_CODES[category]}-env-v1":
            raise BuildError(f"environment passage {spec['id']} does not match its category")
        environment[category] = r.environment_entry(
            category=category,
            target=spec["target"],
            text=text,
            owner=repo["owner"],
            repo=repo["repo"],
            commit=repo["commit"],
            version_scope=repo["version_scope"],
            retrieved_at=r.latest_timestamp(x["retrieved_at"] for x in records),
            license_expression=repo["license_expression"],
            license_evidence=_license_evidence(records[0]),
            attribution=attribution,
        )
        env_receipt.append(
            {
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
        )
    if set(environment) != set(r.CATEGORIES):
        raise BuildError("every category needs exactly one environment passage")

    # §6.4 retrieval
    retrievers = {
        c: r.CategoryRetriever(chunks_by_category[c], blocked.get(c, {})) for c in r.CATEGORIES
    }
    results, selections, task_passages, passages, passage_rows = {}, {}, {}, [], {}
    order = {c: i for i, c in enumerate(r.CATEGORIES)}
    for task in base["tasks"]:
        result = retrievers[task["category"]].retrieve(task["brief"])
        results[task["id"]] = result
        selections[task["id"]] = result.selected
        ids = []
        for chunk in result.selected:
            record = files[chunk.file_key]
            repo = repos[record["repo_key"]]
            entry = r.passage_entry(
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
                license_evidence=_license_evidence(record),
                attribution=record["attribution"],
            )
            ids.append(entry["id"])
            passages.append(
                ((order[chunk.category], chunk.file_index, chunk.start, chunk.end), entry)
            )
            passage_rows[entry["id"]] = {
                "id": entry["id"],
                "chunk_key": chunk.chunk_key,
                "file_key": chunk.file_key,
                "start": chunk.start,
                "end": chunk.end,
                "removed_within": [list(x) for x in chunk.removed_within],
                "tokens": chunk.qwen_tokens,
            }
        task_passages[task["id"]] = ids
    manifest_sha = r.sha256_hex(manifest_bytes)
    pack = r.assemble_pack(base, environment, passages, task_passages, manifest_sha)

    # §7.4 validation before writing
    validate_pack(pack)
    by_id = {s["id"]: s for s in pack["sources"]}
    pack_digest = r.digest(pack)
    for category in r.CATEGORIES:
        tasks = [t for t in pack["tasks"] if t["category"] == category]
        for ordinal in range(10):
            context = context_for(pack, category, ordinal)
            task = tasks[ordinal % len(tasks)]
            if (
                set(context) != {"pack_sha256", "task", "sources"}
                or context["pack_sha256"] != pack_digest
                or context["task"] != task
                or context["sources"] != [by_id[ref] for ref in task["source_refs"]]
            ):
                raise BuildError(f"context_for differs for {category} ordinal {ordinal}")
    for old, new in zip(base["sources"], pack["sources"], strict=False):
        if list(old.items()) != list(new.items()):
            raise BuildError(f"static entry {old['id']} changed")
    for old, new in zip(base["tasks"], pack["tasks"], strict=True):
        if {k: v for k, v in old.items() if k != "source_refs"} != {
            k: v for k, v in new.items() if k != "source_refs"
        } or new["source_refs"][: len(old["source_refs"])] != old["source_refs"]:
            raise BuildError(f"task {old['id']} changed beyond its references")
    for entry in pack["sources"]:
        if tuple(entry) != r.SOURCE_FIELDS:
            raise BuildError(f"{entry['id']} does not carry the twelve fields in order")

    pack_text = r.pack_json(pack)
    found = r.separator_location(pack_text)
    if found:
        raise BuildError(
            f"the pack holds {found[1]} at line {found[0]}, which the pinned ledger reader "
            "splits on"
        )
    pack_sha = r.write_new(output / PACK_FILE, pack_text)
    written = (output / PACK_FILE).read_text(encoding="utf-8")
    spans = r.static_source_spans(base_bytes.decode("utf-8"))[: len(base["sources"])]
    missing = [
        s["id"] for s, span in zip(base["sources"], spans, strict=True) if span not in written
    ]
    if missing or len(spans) != len(base["sources"]):
        raise BuildError(f"static entry byte spans are not verbatim in the pack: {missing}")

    # §9 G7 metrics and the retrieval report
    metrics = r.retrieval_metrics(base["tasks"], chunks_by_category, blocked, selections)
    metric_rows = {row["task_id"]: row for row in metrics["tasks"]}
    task_reports = []
    for task in base["tasks"]:
        result = results[task["id"]]
        category = task["category"]
        prose = retrievers[category].retrieve(r.prose_only(task["brief"]))
        task_reports.append(
            {
                "task_id": task["id"],
                "query_terms": result.query_terms,
                "identifiers": [
                    {"identifier": x, "chunks_with_exact_match": n}
                    for x, n in result.identifier_chunks.items()
                ],
                "top_raw": result.top_raw,
                "floor": result.floor,
                "top_candidates": [
                    {
                        "chunk_key": c.chunk.chunk_key,
                        "r_raw": c.r_raw,
                        "m": c.m,
                        "r_final": c.r_final,
                        "decision": c.decision,
                    }
                    for c in result.ranking[:TOP_CANDIDATES]
                ],
                "selected": task_passages[task["id"]],
                "selected_tokens": result.selected_tokens,
                "prose_only": {
                    "query_terms": prose.query_terms,
                    "selected": [r.passage_id(category, c.text) for c in prose.selected],
                },
                "leave_one_sentence_out": metric_rows[task["id"]].get("leave_one_sentence_out"),
            }
        )
    categories = {}
    for category in r.CATEGORIES:
        retriever = retrievers[category]
        group = [t for t in base["tasks"] if t["category"] == category]
        categories[category] = {
            "N": retriever.index.n,
            "avgdl": round(retriever.index.avgdl, r.SCORE_DECIMALS),
            "files": sum(
                1
                for f in manifest["files"]
                if f["category"] == category and "passage" in f["role"].split("+")
            ),
            "chunks": len(chunks_by_category[category]),
            "tasks_with_zero_passages": sum(1 for t in group if not task_passages[t["id"]]),
        }
    tiers = [
        files[passage_rows[s["id"]]["file_key"]]["tier"]
        for s in pack["sources"]
        if s["id"] in passage_rows
    ]
    metrics["tier_shares"] = r.tier_shares(tiers)
    report = {
        "schema_version": REPORT_SCHEMA,
        "pack_id": r.PACK_ID,
        "categories": categories,
        "tasks": task_reports,
        "metrics": metrics,
        "prose_only_definition": "the brief with every occurrence of its identifiers removed, "
        "ranked and selected by section 6.4; reported only",
    }
    report_sha = r.write_new(output / "retrieval-report.json", r.record_json(report))

    receipt = {
        "schema_version": BUILD_RECEIPT_SCHEMA,
        "inputs": reader.inputs(),
        "corpus": {
            "corpus-manifest.json": r.sha256_hex(manifest_bytes),
            "chunks.jsonl": r.sha256_hex(chunks_bytes),
            "corpus-receipt.json": r.sha256_hex(receipt_bytes),
        },
        "engineering_v1": {"sha256": r.sha256_hex(base_bytes), "digest": r.digest(base)},
        "constants": r.constants(),
        "code": code_hashes(
            [
                "src/aia_mp1/retrieval.py",
                "tools/build_rag_corpus.py",
                "tools/build_rag_pack.py",
                "tools/qwen_offline_tokenizer.py",
                "src/aia_mp1/sources.py",
            ]
        ),
        "tokenizer": tokenizer,
        "environment": env_receipt,
        "passages": [passage_rows[s["id"]] for s in pack["sources"] if s["id"] in passage_rows],
        "tasks": [{"task_id": t["id"], "source_refs": t["source_refs"]} for t in pack["tasks"]],
        "pack": {
            "file_sha256": pack_sha,
            "digest": pack_digest,
            "sources": len(pack["sources"]),
            "tasks": len(pack["tasks"]),
        },
        "validation": {
            "validate_pack": "pass",
            "context_for": "pass: 5 categories x ordinals 0-9",
            "static_entries": "pass: keys, order, values and byte spans",
            "tasks": "pass: unchanged except source_refs",
        },
        "outputs": {PACK_FILE: pack_sha, "retrieval-report.json": report_sha},
    }
    r.write_new(output / "build-receipt.json", r.record_json(receipt))
    return {"pack": pack, "receipt": receipt, "report": report}


def build_pack(
    *,
    corpus: Path,
    output: Path,
    evidence: Path = DEFAULT_EVIDENCE,
    repository: Path = REPO,
    count_tokens: Callable[[str], int],
    tokenizer: dict,
    gguf: Path | None = None,
    argv: list[str] | None = None,
) -> dict:
    """Run step 5b-c; tests inject ``count_tokens`` and a synthetic tokenizer identity."""
    reader = InputReader(evidence=evidence, repository=repository, corpus=corpus)

    def work():
        if gguf is not None:
            reader.record(
                "tokenizer",
                str(_abs(gguf)),
                "tokenizer",
                tokenizer["gguf_sha256"],
                _abs(gguf).stat().st_size,
            )
        return build(reader, _abs(output), count_tokens, tokenizer)

    return run_in_new_directory(output, repository, Path(__file__).resolve(), argv or [], work)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args(argv)
    try:
        count_tokens, identity = load_counter(args.gguf)
        result = build_pack(
            corpus=args.corpus,
            output=args.output,
            evidence=args.evidence,
            count_tokens=count_tokens,
            tokenizer=identity,
            gguf=args.gguf,
            argv=sys.argv[:1] + list(argv if argv is not None else sys.argv[1:]),
        )
    except (BuildError, ValueError, OSError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": "complete",
                "pack": result["receipt"]["pack"],
                "outputs": result["receipt"]["outputs"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
