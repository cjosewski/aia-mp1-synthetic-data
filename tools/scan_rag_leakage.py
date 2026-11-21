"""Gate G5: the n = 8 leakage scan of the retrieval pack and prompt v3 (AEC-RAG-PACK §9 G5).

Authored and selected text (the candidates) is split into 8-grams of ``[a-z0-9]+`` tokens. N-grams
found in the allowed upstream and course texts are exempt; the rest are looked up while every
forbidden evidence file is streamed. Forbidden files are read programmatically only, and the output
holds counts and one digest: no n-gram text and no forbidden file name is written or printed. The
path check confirms that every input the builders recorded is allowlisted (§1.4).
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
from collections import defaultdict
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from aia_mp1.retrieval import (
    CLAUSE_SHA256,
    EVIDENCE_INPUTS,
    LEAKAGE_N,
    PACK_ID,
    RUBRIC_V2_SHA256,
    UPSTREAM_PREFIX,
    g5_tokens,
    input_path_problem,
    n1,
    record_json,
    sandcastle_text,
    sha256_hex,
    write_new,
)

REPOSITORY = Path(__file__).resolve().parents[1]
EVIDENCE = REPOSITORY.parent / "artifacts" / "evidence"
CONFIG = REPOSITORY / "config" / "aec-course" / "rag-sources-v1.json"
PROMPT_V1 = REPOSITORY / "prompts" / "generator-assessed-v1.md"
RUBRIC_V2 = REPOSITORY / "config" / "aec-course" / "rubric-v2.json"
CANDIDATE_CLASSES = ("passage_text", "entry_free_text", "clause", "guidance", "config_free_text")
FORBIDDEN_CLASSES = ("labels", "reviews", "answers", "task_notes", "judge", "design", "other")
SCANNED_SUFFIXES = (".json", ".jsonl", ".md", ".txt", ".csv", ".tsv", ".html", ".htm")
ENTRY_FREE_TEXT = ("version", "attribution", "installation")


@contextmanager
def writer_lock(directory: Path):
    """Hold ``.writer.lock`` while writing (§1.3), with the standard library only."""
    lock = directory / ".writer.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(datetime.now(timezone.utc).isoformat())
    try:
        yield
    finally:
        lock.unlink()


def ngram_strings(text: str) -> Iterator[str]:
    tokens = g5_tokens(text)
    return (" ".join(tokens[i : i + LEAKAGE_N]) for i in range(len(tokens) - LEAKAGE_N + 1))


def json_strings(value) -> Iterator[str]:
    """Every string value of a JSON document, recursively; keys are not values."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for entry in value.values():
            yield from json_strings(entry)
    elif isinstance(value, list):
        for entry in value:
            yield from json_strings(entry)


def file_texts(raw: bytes, suffix: str) -> tuple[list[str], bool]:
    """A file's texts: JSON string values, else the whole text. False when JSON does not parse."""
    text = raw.decode("utf-8", errors="replace")
    try:
        if suffix == ".json":
            return list(json_strings(json.loads(text))), True
        if suffix == ".jsonl":
            texts, parsed = [], True
            for line in text.split("\n"):
                if not line.strip():
                    continue
                try:
                    texts += json_strings(json.loads(line))
                except ValueError:  # an interrupted append: only this line falls back to raw text
                    texts.append(line)
                    parsed = False
            return texts, parsed
    except ValueError:
        return [text], False
    return [text], True


def forbidden_class(relative: str) -> str:
    """The first §9 G5 class whose path test matches ``relative`` (POSIX, under the evidence root)."""
    segments = relative.split("/")
    directories, name = segments[:-1], segments[-1]
    if "human-labels" in relative or "human-reference" in relative or "labels" in directories:
        return "labels"
    if any(s in ("reviews", "human-review-reports") for s in directories) or any(
        s.startswith(("human-adjudication", "human-amendments", "MY-ANSWERS", "submitted-answers"))
        for s in segments
    ):
        return "reviews"
    if name in ("data.jsonl", "attempts.jsonl", "gate-items.jsonl"):
        return "answers"
    if name in ("task-cards.json", "task-catalog.json") or "task-notes" in relative:
        return "task_notes"
    if any(
        m in relative
        for m in ("judge", "api-development-", "api-correctness-", "qualification/", "analysis/")
    ) or any(
        s.startswith(".") and any(w in s for w in ("docs", "conformance", "judge"))
        for s in directories
    ):
        return "judge"
    if ".rag-generator-design-" in relative or ".rubric-v2-review-" in relative:
        return "design"
    return "other"


def _walk_error(error: OSError) -> None:
    raise error


def forbidden_files(
    evidence: Path, excepted: Iterable[Path], skipped: list[str] | None = None
) -> list[tuple[str, Path]]:
    """Scanned evidence files, sorted by POSIX path under ``evidence``; symlinks are never followed.

    Excepted: the §1.4 allowlist, ``EVID/references/**``, ``EVID/aec-course/rag/**`` and the given
    tier-2, corpus and build directories. A directory that cannot be listed raises. Symlinked
    files and directories are not scanned; their paths are appended to ``skipped``.
    """
    evidence = evidence.resolve()
    evid = evidence / "P1-03"
    roots = [
        evid / "references",
        evid / "aec-course" / "rag",
        *(Path(p).resolve() for p in excepted),
    ]
    allowlisted = {evid / relative for relative in EVIDENCE_INPUTS}
    found = []
    for directory, subdirectories, names in os.walk(evidence, onerror=_walk_error):
        here = Path(directory)
        subdirectories[:] = sorted(
            d for d in subdirectories if not any((here / d).is_relative_to(r) for r in roots)
        )
        if skipped is not None:
            skipped += [
                (here / d).relative_to(evidence).as_posix()
                for d in subdirectories
                if (here / d).is_symlink()
            ]
        for name in sorted(names):
            path = here / name
            if path.suffix.lower() not in SCANNED_SUFFIXES or path in allowlisted:
                continue
            if path.is_symlink():
                if skipped is not None:
                    skipped.append(path.relative_to(evidence).as_posix())
                continue
            found.append((path.relative_to(evidence).as_posix(), path))
    return sorted(found)


def scan(
    candidates: dict[str, list[str]],
    allowed: Iterable[str],
    forbidden: Iterable[tuple[str, Iterable[str]]],
) -> dict:
    """Count candidate n-grams found in forbidden texts after removing those found in allowed texts.

    ``candidates`` maps a candidate class to its texts, one candidate entry each; ``forbidden`` yields
    ``(forbidden class, texts)`` per file. N-grams never span two texts. Memory is bounded by the
    candidate set.
    """
    owners: dict[str, set[tuple[str, int]]] = defaultdict(set)
    for cclass in CANDIDATE_CLASSES:
        for index, text in enumerate(candidates.get(cclass, [])):
            for gram in ngram_strings(text):
                owners[gram].add((cclass, index))
    before = _class_counts(owners)
    first = {gram.partition(" ")[0] for gram in owners}
    for text in allowed:
        for gram in _matching(text, first):
            owners.pop(gram, None)
    after = _class_counts(owners)
    first = {gram.partition(" ")[0] for gram in owners}
    hits: dict[str, set[str]] = {fclass: set() for fclass in FORBIDDEN_CLASSES}
    for fclass, texts in forbidden:
        for text in texts:
            hits[fclass].update(gram for gram in _matching(text, first) if gram in owners)
    table = {}
    for cclass in CANDIDATE_CLASSES:
        table[cclass] = {}
        for fclass in FORBIDDEN_CLASSES:
            grams = {gram for gram in hits[fclass] if any(c == cclass for c, _ in owners[gram])}
            entries = {(c, e) for gram in grams for c, e in owners[gram] if c == cclass}
            table[cclass][fclass] = {
                "distinct_ngrams": len(grams),
                "entries_with_hit": len(entries),
            }
    summary = {
        cclass: {
            "entries": len(candidates.get(cclass, [])),
            "ngrams": before[cclass],
            "exempt": before[cclass] - after[cclass],
            "scanned": after[cclass],
        }
        for cclass in CANDIDATE_CLASSES
    }
    return {"candidates": summary, "hits": table}


def _matching(text: str, first: set[str]) -> Iterator[str]:
    tokens = g5_tokens(text)
    for i in range(len(tokens) - LEAKAGE_N + 1):
        if tokens[i] in first:
            yield " ".join(tokens[i : i + LEAKAGE_N])


def _class_counts(owners: dict[str, set[tuple[str, int]]]) -> dict[str, int]:
    counts = dict.fromkeys(CANDIDATE_CLASSES, 0)
    for owner in owners.values():
        for cclass in {c for c, _ in owner}:
            counts[cclass] += 1
    return counts


def path_check(receipts: dict[str, dict], upstream_names: set[str] | None = None) -> dict:
    """Counts for every ``{root, path}`` input recorded in the fetch, corpus and build receipts."""
    counts = {
        "receipts": len(receipts),
        "receipts_without_inputs": 0,
        "inputs": 0,
        "not_allowlisted": 0,
        "forbidden_pattern": 0,
    }
    for receipt in receipts.values():
        inputs = receipt.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            counts["receipts_without_inputs"] += 1
            continue
        for record in inputs:
            counts["inputs"] += 1
            valid = (
                isinstance(record, dict)
                and isinstance(record.get("root"), str)
                and isinstance(record.get("path"), str)
            )
            problem = (
                input_path_problem(record["root"], record["path"])
                if valid
                else "malformed input record"
            )
            if (
                not problem
                and upstream_names is not None
                and record["root"] == "evidence"
                and record["path"].startswith(UPSTREAM_PREFIX)
                and record["path"].removeprefix(UPSTREAM_PREFIX.rsplit("upstream/", 1)[0])
                not in upstream_names
            ):
                problem = "upstream file not named in source-verification"
            if problem:
                counts[
                    "forbidden_pattern" if problem.startswith("forbidden") else "not_allowlisted"
                ] += 1
    return counts


def prompt_sections(v3: str, v1: str) -> tuple[str, str]:
    """The clause and guidance of ``v1 + LF + clause + LF + guidance`` (§8.1)."""
    if not v3.startswith(v1 + "\n"):
        raise ValueError("the v3 prompt does not start with prompt v1 and a blank line")
    rest = v3[len(v1) + 1 :]
    clause = "\n".join(rest.split("\n")[:3]) + "\n"
    if (
        sha256_hex(clause.encode("utf-8")) != CLAUSE_SHA256
        or rest[len(clause) : len(clause) + 1] != "\n"
    ):
        raise ValueError("the v3 prompt does not hold the pinned retrieval clause")
    return clause, rest[len(clause) + 1 :]


def candidate_texts(
    pack: dict, clause: str, guidance: str, config: dict, manifest: dict, sidecar: dict
) -> dict[str, list[str]]:
    """The §9 G5 candidate classes; identifiers, URLs, paths, hashes and enumerations are not."""
    config_text = config_free_text(config)
    for record in manifest["files"]:
        config_text += [record.get("attribution"), *_strings(record.get("notices"))]
    config_text += [sentence["text"] for sentence in sidecar["sentences"]]
    return {
        "passage_text": [entry["text"] for entry in pack["sources"]],
        "entry_free_text": [entry[field] for entry in pack["sources"] for field in ENTRY_FREE_TEXT]
        + [pack["approval_basis"]],
        "clause": [clause],
        "guidance": [guidance],
        "config_free_text": [text for text in config_text if isinstance(text, str) and text],
    }


def config_free_text(config: dict) -> list:
    """Free text of rag-sources-v1.json, as its author enumerates it; pins and patterns are not."""
    deny = config.get("deny_lists") or {}
    texts = [config.get("specification"), deny.get("never_inputs"), deny.get("excluded_host_note")]
    texts += (config.get("decision_basis") or {}).values()
    for decision in config.get("decisions", []):
        texts += [decision.get("scope"), decision.get("owner_record")]
    for repository in config.get("repositories", []):
        texts += [repository.get("version_scope"), *(repository.get("attribution") or {}).values()]
        judgment = repository.get("license_judgment") or {}
        texts += [judgment.get("statement"), *_strings(judgment.get("caveat"))]
        texts.append((repository.get("regents_notice") or {}).get("placement"))
    texts += [passage.get("target") for passage in config.get("environment_passages", [])]
    return texts + list(_notes(config))


def _notes(value) -> Iterator[str]:
    """Every string under a ``note`` key, at any depth."""
    if isinstance(value, dict):
        for key, entry in value.items():
            if key == "note" and isinstance(entry, str):
                yield entry
            else:
                yield from _notes(entry)
    elif isinstance(value, list):
        for entry in value:
            yield from _notes(entry)


def _strings(value) -> list[str]:
    """Plain strings or ``{kind, text}`` records."""
    if isinstance(value, str):
        return [value]
    return [v["text"] if isinstance(v, dict) else v for v in value or []]


def corpus_texts(manifest: dict, config: dict, tier2: Path, evid: Path) -> Iterator[str]:
    """The normalized or derived text of every corpus file and license file, hash-checked.

    Tier-1 texts are the tier-1 snapshots, which equal N1 of their blobs; tier-2 texts are N1 of
    the stored blobs. License files that are not file records (the Regents page) come from the
    repositories' ``license_files`` copies.
    """
    cheat_sheet = config["tier1"]["cheat_sheet_text"]

    def evidence_file(relative: str) -> Path:
        problem = input_path_problem("evidence", relative)
        if problem:
            raise ValueError(f"corpus text path {relative} is not allowlisted: {problem}")
        return evid / relative

    for record in manifest["files"]:
        derived = record.get("derived")
        stored = tier2 / "files" / record["repo_key"] / record["path"]
        snapshot = record.get("t1_snapshot")
        if derived:
            if derived["kind"] == "pdf_text":
                text = evidence_file(cheat_sheet["path"]).read_bytes().decode("utf-8")
            elif derived["kind"] == "sandcastle_text":
                text = sandcastle_text(n1(stored.read_bytes()))
            else:
                raise ValueError(f"unknown derived text kind {derived['kind']!r}")
            expected = derived.get("text_sha256")
        elif record.get("normalized_sha256") is None:
            continue  # a binary file has no normalized text (the cheat-sheet PDF)
        elif record.get("tier") == "T1" and snapshot:
            text, expected = (
                evidence_file(snapshot["path"]).read_bytes().decode("utf-8"),
                record["normalized_sha256"],
            )
        else:
            text, expected = n1(stored.read_bytes()), record["normalized_sha256"]
        if sha256_hex(text.encode("utf-8")) != expected:
            raise ValueError(
                f"corpus text of {record.get('file_key', record['path'])} differs from the manifest"
            )
        yield text
    recorded = {(record["repo_key"], record["path"]) for record in manifest["files"]}
    for repository in manifest["repositories"]:  # §3.9 requires both keys; drift fails loudly
        for entry in repository["license_files"]:
            if (repository["repo_key"], entry["path"]) not in recorded:
                raw = evidence_file(entry["evidence_path"]).read_bytes()
                if sha256_hex(raw) != entry.get("evidence_sha256", entry["sha256"]):
                    raise ValueError(f"license file {entry['path']} differs from the manifest")
                yield n1(raw)


def run(
    build: Path,
    prompt: Path,
    evidence: Path,
    *,
    corpus=None,
    tier2=None,
    config=CONFIG,
    provenance=None,
    rubric=RUBRIC_V2,
) -> dict:
    """Run gate G5 and write ``<build>/gates/leakage-scan.json``; return the result.

    ``gates/.writer.lock`` is held from the existence check through the final write (§1.3).
    """
    build = Path(build)
    gates = build / "gates"
    gates.mkdir(exist_ok=True)
    with writer_lock(gates):
        return _run_locked(
            build,
            prompt,
            Path(evidence),
            corpus=corpus,
            tier2=tier2,
            config=config,
            provenance=provenance,
            rubric=rubric,
        )


def _run_locked(
    build: Path,
    prompt: Path,
    evidence: Path,
    *,
    corpus,
    tier2,
    config,
    provenance,
    rubric,
) -> dict:
    corpus = Path(corpus or build.parent / "corpus-v1")
    tier2 = Path(tier2 or build.parent / "tier2-v1")
    provenance = Path(provenance or build.parent / "prompt-v3" / "guidance-provenance.json")
    evid = evidence / "P1-03"
    gates = build / "gates"
    output = gates / "leakage-scan.json"
    if output.exists() or output.is_symlink():
        raise ValueError(f"output exists: {output}")
    manifest_pin = json.loads((corpus / "corpus-manifest.json").read_bytes())
    pinned = manifest_pin["engineering_v1"]
    inputs = {
        "pack": build / f"{PACK_ID}.json",
        "build_receipt": build / "build-receipt.json",
        "corpus_manifest": corpus / "corpus-manifest.json",
        "corpus_receipt": corpus / "corpus-receipt.json",
        "fetch_receipt": tier2 / "fetch-receipt.json",
        "sources_config": Path(config),
        "guidance_provenance": provenance,
        "prompt_v3": Path(prompt),
        "prompt_v1": PROMPT_V1,
        "rubric_v2": Path(rubric),
        "engineering_v1": evid / pinned["path"],
    }
    raw = {name: path.read_bytes() for name, path in inputs.items()}
    if sha256_hex(raw["engineering_v1"]) != pinned["sha256"]:
        raise ValueError("engineering-v1.json differs from its pin")
    receipt_path = build.parent / "prompt-v3" / "assembly-receipt.json"
    if not receipt_path.is_file():
        raise ValueError(f"the assembly receipt is missing: {receipt_path}")
    assembly = json.loads(receipt_path.read_bytes())
    if assembly["v3"]["sha256"] != sha256_hex(raw["prompt_v3"]):
        raise ValueError("--prompt is not the v3 the assembly receipt names")
    if not assembly["checks"] or not all(c.get("passed") is True for c in assembly["checks"]):
        raise ValueError("the assembly receipt records a failed or missing check")
    if sha256_hex(raw["rubric_v2"]) != RUBRIC_V2_SHA256:
        raise ValueError("rubric-v2.json differs from its frozen pin")
    if sha256_hex(raw["sources_config"]) != manifest_pin["sources_config"]["sha256"]:
        raise ValueError("the sources config is not the one the corpus was built from")
    data = {
        name: json.loads(raw[name]) for name in inputs if name not in ("prompt_v3", "prompt_v1")
    }
    built_from = data["build_receipt"]["corpus"]
    if (
        built_from["corpus-manifest.json"] != sha256_hex(raw["corpus_manifest"])
        or built_from["corpus-receipt.json"] != sha256_hex(raw["corpus_receipt"])
        or data["corpus_manifest"]["fetch_receipt"]["sha256"] != sha256_hex(raw["fetch_receipt"])
    ):
        raise ValueError("the pack was not built from the scanned corpus and tier-2 receipts")
    clause, guidance = prompt_sections(
        raw["prompt_v3"].decode("utf-8"), raw["prompt_v1"].decode("utf-8")
    )
    candidates = candidate_texts(
        data["pack"],
        clause,
        guidance,
        data["sources_config"],
        data["corpus_manifest"],
        data["guidance_provenance"],
    )
    allowed = itertools.chain(
        corpus_texts(data["corpus_manifest"], data["sources_config"], tier2, evid),
        json_strings(data["engineering_v1"]),
        [raw["prompt_v1"].decode("utf-8")],
        json_strings(data["rubric_v2"]),
    )
    skipped: list[str] = []
    files = forbidden_files(evidence, [tier2, corpus, build], skipped)
    verification = json.loads((evid / "aec-course/analysis/source-verification.json").read_bytes())
    scanned = {fclass: {"files": 0, "bytes": 0} for fclass in FORBIDDEN_CLASSES}
    hashes: list[tuple[str, str]] = []
    unparsed = 0

    def stream() -> Iterator[tuple[str, list[str]]]:
        nonlocal unparsed
        for relative, path in files:
            content = path.read_bytes()
            fclass = forbidden_class(relative)
            scanned[fclass]["files"] += 1
            scanned[fclass]["bytes"] += len(content)
            hashes.append((relative, sha256_hex(content)))
            texts, parsed = file_texts(content, path.suffix)
            unparsed += not parsed
            yield fclass, texts

    result = scan(candidates, allowed, stream())
    paths = path_check(
        {name: data[name] for name in ("fetch_receipt", "corpus_receipt", "build_receipt")},
        set(verification["upstream_files_sha256"]),
    )
    hit_total = sum(
        cell[key] for row in result["hits"].values() for cell in row.values() for key in cell
    )
    path_total = sum(
        paths[key] for key in ("receipts_without_inputs", "not_allowlisted", "forbidden_pattern")
    )
    result.update(
        gate="G5",
        name="leakage-scan",
        status="pass" if hit_total == 0 and path_total == 0 and not skipped else "fail",
        skipped_symlinks=sorted(skipped),
        leakage_n=LEAKAGE_N,
        forbidden=scanned,
        forbidden_files=len(hashes),
        forbidden_files_digest=sha256_hex(
            json.dumps(sorted(hashes), ensure_ascii=False).encode("utf-8")
        ),
        forbidden_digest_method="sha256 of the JSON list of sorted [relative path, sha256] pairs",
        unparsed_json_files=unparsed,
        path_check=paths,
        inputs={
            name: {"sha256": sha256_hex(content), "bytes": len(content)}
            for name, content in raw.items()
        },
    )
    write_new(output, record_json(result))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gate G5 leakage scan (AEC-RAG-PACK §9 G5); counts only."
    )
    parser.add_argument("--build", type=Path, required=True, help="the pack directory")
    parser.add_argument(
        "--prompt", type=Path, required=True, help="prompts/generator-assessed-v3.md"
    )
    parser.add_argument("--evidence", type=Path, default=EVIDENCE, help="../artifacts/evidence")
    parser.add_argument("--corpus", type=Path, help="default: corpus-v1 beside the pack directory")
    parser.add_argument("--tier2", type=Path, help="default: tier2-v1 beside the pack directory")
    parser.add_argument(
        "--provenance", type=Path, help="default: prompt-v3/guidance-provenance.json beside it"
    )
    args = parser.parse_args(argv)
    try:
        result = run(
            args.build,
            args.prompt,
            args.evidence,
            corpus=args.corpus,
            tier2=args.tier2,
            provenance=args.provenance,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    hits = sum(cell["distinct_ngrams"] for row in result["hits"].values() for cell in row.values())
    problems = result["path_check"]["not_allowlisted"] + result["path_check"]["forbidden_pattern"]
    print(
        f"G5 {result['status']}: {hits} hit n-grams in {result['forbidden_files']} forbidden "
        f"files; {problems} input path problems"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
