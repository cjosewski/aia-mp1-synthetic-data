"""Entirely synthetic fixtures for the retrieval-pack tools (tokenizer, fetch, leakage, assembly).

Nothing here reads real evidence, model files or the network. ``tests/rag_fixtures.py`` belongs to
the core retrieval lane; this module serves only the four tool test files.
"""

import hashlib
import json
import os
import struct
import subprocess
from pathlib import Path

GGUF_SCALARS = {
    0: "B",
    1: "b",
    2: "H",
    3: "h",
    4: "I",
    5: "i",
    6: "f",
    7: "?",
    10: "Q",
    11: "q",
    12: "d",
}
GGUF_STRING, GGUF_ARRAY, GGUF_INT32, GGUF_BOOL = 8, 9, 5, 7

# Written in the Qwen template's own style: newlines come from string literals, not template text.
CHATML_TEMPLATE = (
    "{%- for message in messages %}{{- '<|im_start|>' + message.role + '\\n' + message.content + '<|im_end|>\\n' }}"
    "{%- endfor %}{%- if add_generation_prompt %}{{- '<|im_start|>assistant\\n' }}{%- endif %}"
)


def _gguf_string(text: str) -> bytes:
    raw = text.encode("utf-8")
    return struct.pack("<Q", len(raw)) + raw


def gguf_value(kind: int, value) -> bytes:
    """Encode one GGUF value; an array value is ``(element_kind, items)``."""
    if kind in GGUF_SCALARS:
        return struct.pack("<" + GGUF_SCALARS[kind], value)
    if kind == GGUF_STRING:
        return _gguf_string(value)
    if kind == GGUF_ARRAY:
        element_kind, items = value
        head = struct.pack("<IQ", element_kind, len(items))
        return head + b"".join(gguf_value(element_kind, item) for item in items)
    raise ValueError(f"unsupported synthetic GGUF type {kind}")


def gguf_bytes(entries, *, version: int = 3, tail: bytes = b"\x00tensor-bytes\xff" * 8) -> bytes:
    """A GGUF file: header, ``(key, kind, value)`` entries, then bytes standing in for tensors."""
    body = b"".join(
        _gguf_string(key) + struct.pack("<I", kind) + gguf_value(kind, value)
        for key, kind, value in entries
    )
    return b"GGUF" + struct.pack("<IQQ", version, 0, len(entries)) + body + tail


def byte_symbols() -> list[str]:
    """The GPT-2 byte-to-unicode symbols, indexed by byte value."""
    printable = [
        *range(ord("!"), ord("~") + 1),
        *range(ord("¡"), ord("¬") + 1),
        *range(ord("®"), ord("ÿ") + 1),
    ]
    symbols, extra = {}, 0
    for byte in range(256):
        if byte in printable:
            symbols[byte] = chr(byte)
        else:
            symbols[byte] = chr(256 + extra)
            extra += 1
    return [symbols[byte] for byte in range(256)]


# Token IDs 0-255 are the byte symbols in byte order, so the ID of a lone byte is its value.
MERGES = [
    "h e",
    "l l",
    "he ll",
    "hell o",  # hello
    "Ġ w",
    "o r",
    "Ġw or",
    "Ġwor l",
    "Ġworl d",  # " world"
    "b c",
    "a b",  # lowest rank first: "abc" -> a + bc
    "2 0",  # never applies: Qwen splits digits before BPE
]
MERGED = ["he", "ll", "hell", "hello", "Ġw", "or", "Ġwor", "Ġworl", "Ġworld", "bc", "ab", "20"]
SPECIALS = [("<|im_start|>", 3), ("<|im_end|>", 3), ("<think>", 4), ("<think>!", 4), ("<plain>", 1)]


def tiny_vocabulary():
    """Tokens, token types and merges of a small synthetic byte-level BPE vocabulary."""
    tokens = byte_symbols() + MERGED + [text for text, _ in SPECIALS]
    types = [1] * (256 + len(MERGED)) + [kind for _, kind in SPECIALS]
    return tokens, types, list(MERGES)


def token_id(text: str) -> int:
    return tiny_vocabulary()[0].index(text)


def write_tokenizer_gguf(
    path: Path, *, template: str = CHATML_TEMPLATE, merges=None, pre: str = "qwen2"
):
    """Write a synthetic tokenizer-only GGUF; return ``(file_sha256, template_sha256)``."""
    tokens, types, default_merges = tiny_vocabulary()
    merges = default_merges if merges is None else merges
    entries = [
        ("general.architecture", GGUF_STRING, "synthetic"),
        ("tokenizer.ggml.model", GGUF_STRING, "gpt2"),
        ("tokenizer.ggml.pre", GGUF_STRING, pre),
        ("tokenizer.ggml.tokens", GGUF_ARRAY, (GGUF_STRING, tokens)),
        ("tokenizer.ggml.token_type", GGUF_ARRAY, (GGUF_INT32, types)),
        ("tokenizer.ggml.merges", GGUF_ARRAY, (GGUF_STRING, merges)),
        ("tokenizer.ggml.add_bos_token", GGUF_BOOL, False),
        ("tokenizer.chat_template", GGUF_STRING, template),
    ]
    raw = gguf_bytes(entries)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest(), hashlib.sha256(template.encode("utf-8")).hexdigest()


# --- local git repositories for the tier-2 fetch -------------------------------------------------

GIT_TEST_ENVIRONMENT = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Synthetic Author",
    "GIT_AUTHOR_EMAIL": "author@example.invalid",
    "GIT_COMMITTER_NAME": "Synthetic Author",
    "GIT_COMMITTER_EMAIL": "author@example.invalid",
    "GIT_AUTHOR_DATE": "2026-11-20T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-11-20T00:00:00Z",
}


def git(*arguments: str, cwd: Path) -> str:
    environment = {"PATH": os.environ["PATH"], "HOME": str(cwd), **GIT_TEST_ENVIRONMENT}
    result = subprocess.run(
        ["git", *arguments], cwd=cwd, env=environment, capture_output=True, check=True
    )
    return result.stdout.decode().strip()


def bare_repository(
    root: Path,
    name: str,
    files: dict[str, bytes],
    *,
    tag=None,
    annotated=False,
    attributes=None,
    links=None,
):
    """A synthetic bare repository served over file://; return ``(url, commit, tag_object)``.

    ``attributes`` becomes ``.gitattributes`` after the files are staged, so blobs keep their own
    line endings while a checkout would convert them. ``links`` maps symlink paths to targets.
    """
    work = root / "work" / name
    work.mkdir(parents=True)
    git("init", "-q", "-b", "main", cwd=work)
    for relative, raw in files.items():
        (work / relative).parent.mkdir(parents=True, exist_ok=True)
        (work / relative).write_bytes(raw)
    for relative, target in (links or {}).items():
        (work / relative).symlink_to(target)
    git("add", "-A", cwd=work)
    if attributes is not None:
        (work / ".gitattributes").write_bytes(attributes)
        git("add", ".gitattributes", cwd=work)
    git("commit", "-q", "-m", "synthetic", cwd=work)
    commit = git("rev-parse", "HEAD", cwd=work)
    tag_object = None
    if tag:
        git("tag", *(["-a", "-m", "synthetic tag"] if annotated else []), tag, cwd=work)
        tag_object = git("rev-parse", f"refs/tags/{tag}", cwd=work) if annotated else None
    bare = root / "served" / f"{name}.git"
    bare.parent.mkdir(parents=True, exist_ok=True)
    git("clone", "-q", "--bare", str(work), str(bare), cwd=root)
    git("config", "uploadpack.allowFilter", "true", cwd=bare)
    return f"file://{bare}", commit, tag_object


def advance(root: Path, name: str) -> str:
    """Move a served repository's HEAD to a new commit; return it."""
    work = root / "work" / name
    (work / "later.txt").write_bytes(b"later\n")
    git("add", "-A", cwd=work)
    git("commit", "-q", "-m", "later", cwd=work)
    git("push", "-q", str(root / "served" / f"{name}.git"), "HEAD:main", cwd=work)
    return git("rev-parse", "HEAD", cwd=work)


def blob_id(raw: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()


DENY_LISTS = {
    "excluded_hosts": ["pro.arcgis.com", "revitapidocs.com"],
    "excluded_repos": ["jeremytammik/RevitSdkSamples", "Esri/developer-support"],
    "excluded_repo_name_substrings": ["stubs"],
    "excluded_path_patterns": ["(?i)\\.(chm|dll|exe|msi|zip|7z|pdb|lib)$"],
    "excluded_path_segments": ["RevitSdkSamples"],
    "credential_name_pattern": "(?i)(credential|secret|password|token)",
    "arcmap_era_pattern": "\\b(arcpy\\.mapping|arcgisscripting)\\b",
}


def sources_config(repositories: list[dict], engineering_v1: dict) -> dict:
    """A synthetic ``rag-sources-v1`` table with only the fields the fetch reads."""
    return {
        "schema_version": "rag-sources-v1",
        "deny_lists": DENY_LISTS,
        "tier1": {"engineering_v1": engineering_v1},
        "repositories": repositories,
    }


def repository_entry(
    key, owner, repo, url, commit, ref, *, category="gis_scripting", files=(), globs=()
):
    return {
        "repo_key": key,
        "owner": owner,
        "repo": repo,
        "url": url,
        "commit": commit,
        "ref": ref,
        "category": category,
        "files": list(files),
        "globs": list(globs),
    }


# --- a synthetic build layout for the G5 leakage scan ---------------------------------------------

V1_TEXT = (Path(__file__).resolve().parents[1] / "prompts" / "generator-assessed-v1.md").read_text(
    encoding="utf-8"
)
UPSTREAM_TEXT = (
    "Upstream synthetic guide: open the fixture model, then read each member's documented units.\n"
)
NOTE_FRAGMENT = "the fixture answer omits the declared unit check entirely"  # nine G5 tokens
REGENTS_NOTICE = (
    "Synthetic regents notice: permission to copy this fixture text must appear in all copies."
)


def _json(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    return path


def leakage_layout(
    root: Path,
    *,
    guidance_sentence: str,
    upstream: str = UPSTREAM_TEXT,
    corpus_inputs=None,
    license_in_manifest: bool = True,
    engineering_brief: str = "Synthetic brief.",
    extra_passages: tuple[str, ...] = (),
) -> dict:
    """Pack, corpus, tier 2, sidecar, v3 prompt and an evidence tree, all synthetic."""
    from assemble_generator_v3 import CLAUSE

    evidence = root / "evidence"
    evid = evidence / "P1-03"
    rag = evid / "aec-course" / "rag"
    build, corpus, tier2 = rag / "engineering-v1-rag-bm25-v1", rag / "corpus-v1", rag / "tier2-v1"
    stored = tier2 / "files" / "up" / "docs" / "guide.md"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(upstream.encode("utf-8"))
    normalized = upstream + "\n"
    engineering = _json(
        evid / "references" / "engineering-v1.json",
        {"tasks": [{"id": "gis_scripting-01", "brief": engineering_brief}]},
    )
    fetch_receipt = _json(
        tier2 / "fetch-receipt.json",
        {"inputs": [{"root": "repository", "path": "config/aec-course/rag-sources-v1.json"}]},
    )
    corpus_receipt = _json(
        corpus / "corpus-receipt.json",
        {"inputs": corpus_inputs or [{"root": "tier2", "path": "files/up/docs/guide.md"}]},
    )
    regents = evid / "references" / "preparation-20261110" / "upstream" / "regents-license.html"
    regents.parent.mkdir(parents=True)
    regents.write_text(f"<html><body><pre>{REGENTS_NOTICE}</pre></body></html>\n", encoding="utf-8")
    license_entry = {
        "path": "references/preparation-20261110/upstream/regents-license.html",
        "blob": None,
        "sha256": hashlib.sha256(regents.read_bytes()).hexdigest(),
        "evidence_path": "references/preparation-20261110/upstream/regents-license.html",
    }
    config = _json(
        root / "rag-sources.json",
        {
            "decisions": [{"id": "G1", "scope": "Synthetic decision scope."}],
            "tier1": {
                "cheat_sheet_text": {"path": "references/none.txt"},
                "engineering_v1": {
                    "path": "references/engineering-v1.json",
                    "sha256": hashlib.sha256(engineering.read_bytes()).hexdigest(),
                },
            },
            "repositories": [
                {
                    "repo_key": "up",
                    "version_scope": "Synthetic 1.0",
                    "files": [
                        {"path": "docs/guide.md", "note": "Synthetic configuration note text."}
                    ],
                    "attribution": {"passage": "Synthetic {HEADER}"},
                }
            ],
        },
    )
    manifest = _json(
        corpus / "corpus-manifest.json",
        {
            "sources_config": {
                "path": "rag-sources.json",
                "sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
            },
            "engineering_v1": {
                "path": "references/engineering-v1.json",
                "sha256": hashlib.sha256(engineering.read_bytes()).hexdigest(),
            },
            "repositories": [
                {"repo_key": "up", "license_files": [license_entry] if license_in_manifest else []}
            ],
            "fetch_receipt": {
                "path": "aec-course/rag/tier2-v1/fetch-receipt.json",
                "sha256": hashlib.sha256(fetch_receipt.read_bytes()).hexdigest(),
            },
            "files": [
                {
                    "file_key": "up/docs/guide.md",
                    "repo_key": "up",
                    "path": "docs/guide.md",
                    "derived": None,
                    "t1_snapshot": None,
                    "normalized_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
                    "attribution": "Synthetic upstream authors (MIT).",
                    "notices": [
                        {"kind": "file_header", "text": "Copyright synthetic fixture owners."},
                        {"kind": "regents_notice", "text": REGENTS_NOTICE},
                    ],
                }
            ],
        },
    )
    passage = "open the fixture model, then read each member's documented units."
    _json(
        build / "engineering-v1-rag-bm25-v1.json",
        {
            "approval_basis": "Synthetic approval basis for a test pack.",
            "sources": [
                {
                    "id": "gis-p-000000000000",
                    "text": passage,
                    "version": "Synthetic 1.0; docs/guide.md lines 1-1",
                    "attribution": "Synthetic upstream authors (MIT).",
                    "installation": "See gis-env-v1.",
                },
                *(
                    {
                        "id": f"gis-p-{n:012d}",
                        "text": text,
                        "version": "Synthetic 1.0",
                        "attribution": "Synthetic.",
                        "installation": "See gis-env-v1.",
                    }
                    for n, text in enumerate(extra_passages, 1)
                ),
            ],
        },
    )
    _json(
        build / "build-receipt.json",
        {
            "inputs": [{"root": "corpus", "path": "corpus-manifest.json"}],
            "corpus": {
                name: hashlib.sha256(path.read_bytes()).hexdigest()
                for name, path in (
                    ("corpus-manifest.json", manifest),
                    ("corpus-receipt.json", corpus_receipt),
                )
            },
        },
    )
    guidance = f"## Answer guidance v3\n\nPlain synthetic guidance. {guidance_sentence}\n"
    sidecar = _json(
        rag / "prompt-v3" / "guidance-provenance.json",
        {"sentences": [{"text": "Plain synthetic guidance."}, {"text": guidance_sentence}]},
    )
    prompt = root / "prompts" / "generator-assessed-v3.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text(V1_TEXT + "\n" + CLAUSE + "\n" + guidance, encoding="utf-8")
    _json(
        rag / "prompt-v3" / "assembly-receipt.json",
        {
            "v3": {"sha256": hashlib.sha256(prompt.read_bytes()).hexdigest()},
            "checks": [{"id": "c1", "passed": True}],
        },
    )
    _json(
        evid / "aec-course" / "analysis" / "source-verification.json",
        {"upstream_files_sha256": {"upstream/regents-license.html": "0" * 64}},
    )
    judge = evid / "aec-course" / "api-correctness-x" / "context.md"
    judge.parent.mkdir(parents=True)
    judge.write_text(f"Synthetic judge context quoting: {REGENTS_NOTICE}\n", encoding="utf-8")
    note = evid / "aec-course" / "assessments" / "x" / "reviews" / "note.md"
    note.parent.mkdir(parents=True)
    note.write_text(f"Synthetic reviewer note: {NOTE_FRAGMENT}.\n", encoding="utf-8")
    _json(
        evidence / ".rag-generator-design-20261120" / "recommendation.json",
        {"text": "Unrelated synthetic design words."},
    )
    return {
        "evidence": evidence,
        "build": build,
        "corpus": corpus,
        "tier2": tier2,
        "prompt": prompt,
        "config": config,
        "provenance": sidecar,
        "note": note,
    }
