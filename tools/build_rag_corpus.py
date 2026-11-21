"""Steps 3 and 5a of docs/AEC-RAG-PACK.md: admit, verify and chunk the retrieval corpus.

Inputs are opened only through ``InputReader`` (the §1.4 allowlist). The builder applies
the admission rules AR-1 to AR-9 (§3.5), verifies tier 1 (§3.7), normalizes and derives
texts (§3.6), applies the live-code rule (§5.2), cuts segments and windows (§5.3-§5.4) and
writes ``corpus-manifest.json``, ``chunks.jsonl``, ``corpus-receipt.json`` and ``run.json``
into a new directory. Nothing is overwritten; there is no network access and no model call.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import re
import subprocess
import sys
import warnings
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from aia_mp1 import retrieval as r

REPO = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = REPO.parent / "artifacts" / "evidence" / "P1-03"
CONFIG_PATH = "config/aec-course/rag-sources-v1.json"
SOURCES_SCHEMA = "rag-sources-v1"
FETCH_SCHEMA = "rag-fetch-v1"
CORPUS_SCHEMA = "rag-corpus-v1"
CORPUS_RECEIPT_SCHEMA = "rag-corpus-receipt-v1"
ROLES = ("passage", "environment", "license", "index", "evidence")
MODES = ("lines", "freecad_pyxml", "freecad_cpp", "python_public_api", "rst_sections")
DERIVED = ("pdf_text", "sandcastle_text")
HEX40 = re.compile(r"[0-9a-f]{40}")
SANDCASTLE_EXTRACTOR = "aia_mp1.retrieval.sandcastle_text"


class BuildError(ValueError):
    """A refusal: the build stops and keeps its directory for inspection."""


def _abs(path) -> Path:
    return Path(os.path.abspath(path))


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _json(data: bytes, name: str):
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"{name} is not valid UTF-8 JSON: {exc}") from exc


class InputReader:
    """§1.4 ``read_input``: refuse symlinks, check the allowlist and deny-list, hash, record.

    Each input is recorded as ``{root, path, role, sha256, bytes}`` with ``path`` relative to
    its root, so builds in different output directories stay byte-identical.
    """

    def __init__(
        self,
        *,
        evidence: Path,
        repository: Path,
        tier2: Path | None = None,
        corpus: Path | None = None,
    ):
        self.roots = {"evidence": _abs(evidence), "repository": _abs(repository)}
        if tier2 is not None:
            self.roots["tier2"] = _abs(tier2)
        if corpus is not None:
            self.roots["corpus"] = _abs(corpus)
        self.upstream: set[str] = set()
        self.records: dict[tuple[str, str, str], dict] = {}

    def allow_upstream(self, names: Iterable[str]) -> None:
        """Admit the ``upstream/*`` snapshots named in source-verification."""
        self.upstream.update(names)

    def locate(self, path) -> tuple[str, str]:
        target = _abs(path)
        matches = [
            (len(root.parts), name)
            for name, root in self.roots.items()
            if _inside(target, root) and target != root
        ]
        if not matches:
            raise BuildError(f"read outside the allowlist: {target}")
        name = max(matches)[1]
        return name, target.relative_to(self.roots[name]).as_posix()

    def path(self, root: str, relative: str) -> Path:
        return self.roots[root] / relative

    def read(self, path, role: str, *, sha256: str | None = None) -> bytes:
        name, relative = self.locate(path)
        root = self.roots[name]
        if root.is_symlink():
            raise BuildError(f"symlink refused: {root}")
        current = root
        for part in Path(relative).parts:
            current = current / part
            if current.is_symlink():
                raise BuildError(f"symlink refused: {current}")
        target = root / relative
        evidence = self.roots["evidence"]
        evidence_relative = (
            target.relative_to(evidence).as_posix() if _inside(target, evidence) else None
        )
        reason = r.forbidden_path_reason(target.parts, evidence_relative) or r.input_path_problem(
            name, relative
        )
        if reason:
            raise BuildError(f"input refused ({reason}): {relative}")
        # A symlink above the root is not seen by the component walk; judge the real location.
        resolved, real_root, real_evidence = (
            target.resolve(),
            root.resolve(),
            evidence.resolve(),
        )
        if not _inside(resolved, real_root):
            raise BuildError(f"input refused (resolves outside its root): {relative}")
        resolved_relative = (
            resolved.relative_to(real_evidence).as_posix()
            if _inside(resolved, real_evidence)
            else None
        )
        reason = r.forbidden_path_reason(resolved.parts, resolved_relative)
        if reason:
            raise BuildError(f"input refused ({reason}): {relative}")
        if name == "evidence" and relative.startswith(r.UPSTREAM_PREFIX):
            if relative[len(r.UPSTREAM_PREFIX) :] not in self.upstream:
                raise BuildError(f"input refused (not named in source-verification): {relative}")
        if not target.is_file():
            raise BuildError(f"input missing: {relative}")
        data = target.read_bytes()
        found = r.sha256_hex(data)
        if sha256 is not None and found != sha256:
            raise BuildError(f"{relative}: sha256 {found} differs from the pinned {sha256}")
        self.records[(name, relative, role)] = {
            "root": name,
            "path": relative,
            "role": role,
            "sha256": found,
            "bytes": len(data),
        }
        return data

    def record(self, root: str, path: str, role: str, sha256: str, size: int) -> None:
        reason = r.input_path_problem(root, path)
        if reason:
            raise BuildError(f"input refused ({reason}): {path}")
        self.records[(root, path, role)] = {
            "root": root,
            "path": path,
            "role": role,
            "sha256": sha256,
            "bytes": size,
        }

    def inputs(self) -> list[dict]:
        return [self.records[k] for k in sorted(self.records)]


@contextmanager
def writer_lock(directory: Path):
    lock = directory / ".writer.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(datetime.now(timezone.utc).isoformat())
    try:
        yield
    finally:
        lock.unlink()


def _git(repository: Path, *args: str) -> str | None:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *args],
            capture_output=True,
            text=True,
            check=True,
            env=env,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout


def run_record(
    tool: Path, argv: list[str], started: str, status: str, error: str | None = None
) -> dict:
    """``run.json``: never compared, so it may carry times and the environment."""
    commit = _git(REPO, "rev-parse", "HEAD")
    modified = _git(REPO, "diff", "--name-only", "HEAD")
    return {
        "tool": {
            "path": tool.relative_to(REPO).as_posix(),
            "sha256": r.sha256_hex(tool.read_bytes()),
        },
        "argv": list(argv),
        "started_at": started,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "aia_mp1_domain": os.environ.get("AIA_MP1_DOMAIN"),
        "repository_commit": commit.strip() if commit else None,
        "modified_tracked_paths": sorted(modified.split()) if modified is not None else None,
        "status": status,
        "error": error,
    }


def run_in_new_directory(
    output: Path, repository: Path, tool: Path, argv: list[str], work: Callable[[], dict]
) -> dict:
    """AR-9 and §1.3: a new directory, a writer lock, and ``run.json`` however the run ends."""
    output = _abs(output)
    if output.exists() or output.is_symlink():
        raise BuildError(f"AR-9: output directory exists: {output}")
    if _inside(output, _abs(repository)) or _inside(output, REPO):
        raise BuildError("outputs must live outside the repository")
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    status, error = "failed", None
    with writer_lock(output):
        try:
            result = work()
            status = "complete"
            return result
        except BaseException as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:  # run.json is written while the lock is still held (§1.3)
            r.write_new(
                output / "run.json", r.record_json(run_record(tool, argv, started, status, error))
            )


_CODE_AT_START: dict[str, str | None] = {}


def _code_hash(name: str) -> str | None:
    if name not in _CODE_AT_START:
        path = REPO / name
        _CODE_AT_START[name] = r.sha256_hex(path.read_bytes()) if path.is_file() else None
    return _CODE_AT_START[name]


def code_hashes(names: Iterable[str]) -> dict:
    """Hashes of the code files, taken once per process so every record names the same bytes."""
    return {name: _code_hash(name) for name in names}


for _name in (
    "src/aia_mp1/retrieval.py",
    "src/aia_mp1/sources.py",
    "tools/build_rag_corpus.py",
    "tools/build_rag_pack.py",
    "tools/qwen_offline_tokenizer.py",
):
    _code_hash(_name)


# ------------------------------------------------------------------ configuration (AR-1, AR-7)


def check_config(config: dict) -> dict:
    """Validate the admission table and refuse deny-listed repositories and hosts (AR-1)."""
    if config.get("schema_version") != SOURCES_SCHEMA:
        raise BuildError("unsupported rag-sources schema")
    if sorted(config.get("allowed_uses") or []) != sorted(r.ALLOWED_USES) or len(
        config["allowed_uses"]
    ) != len(r.ALLOWED_USES):
        raise BuildError("AR-7: allowed uses must be exactly the four assessed uses")
    if config.get("export_permission") != r.EXPORT_PERMISSION:
        raise BuildError("AR-7: export permission must be local_only")
    decisions = {d.get("id"): d for d in config.get("decisions", [])}
    if None in decisions or len(decisions) != len(config.get("decisions", [])):
        raise BuildError("decision IDs must be present and unique")
    deny = config.get("deny_lists") or {}
    for key in (
        "excluded_hosts",
        "excluded_repos",
        "excluded_repo_name_substrings",
        "excluded_path_patterns",
        "excluded_path_segments",
        "credential_name_pattern",
        "arcmap_era_pattern",
    ):
        if key not in deny:
            raise BuildError(f"deny list {key} is missing")
    excluded_repos = {x.casefold() for x in deny["excluded_repos"]}
    keys = set()
    for repo in config.get("repositories", []):
        key = repo.get("repo_key")
        if not key or key in keys:
            raise BuildError("repository keys must be present and unique")
        keys.add(key)
        owner, name = repo.get("owner", ""), repo.get("repo", "")
        if f"{owner}/{name}".casefold() in excluded_repos or any(
            s.casefold() in name.casefold() for s in deny["excluded_repo_name_substrings"]
        ):
            raise BuildError(f"AR-1: deny-listed repository {owner}/{name}")
        host = (urlparse(repo.get("url", "")).hostname or "").lower()
        if host in {h.lower() for h in deny["excluded_hosts"]}:
            raise BuildError(f"AR-1: deny-listed host {host}")
        if host != "github.com" or repo["url"] != f"https://github.com/{owner}/{name}.git":
            raise BuildError(f"AR-1: {key} must be the github.com repository {owner}/{name}")
        if not HEX40.fullmatch(repo.get("commit") or ""):
            raise BuildError(
                f"AR-1: {key} commit must be a full 40-hex SHA, not a branch name or short SHA"
            )
        ref = repo.get("ref") or {}
        if ref.get("kind") not in ("head", "tag"):
            raise BuildError(f"{key}: ref must be head or tag")
        if ref["kind"] == "tag" and (
            not ref.get("name")
            or (ref.get("annotated") and not HEX40.fullmatch(ref.get("tag_object") or ""))
        ):
            raise BuildError(f"{key}: tag ref needs a name and, if annotated, its tag object")
        if repo.get("category") not in r.CATEGORIES:
            raise BuildError(f"{key}: unknown category")
        for field in ("license_expression", "version_scope"):
            if not (repo.get(field) or "").strip():
                raise BuildError(f"AR-7: {key} has no {field}")
        if not ((repo.get("attribution") or {}).get("passage") or "").strip():
            raise BuildError(f"AR-7: {key} has no attribution")
        if not set(repo.get("decision_ids") or []) <= set(decisions) or not repo.get(
            "decision_ids"
        ):
            raise BuildError(f"AR-7: {key} has an unknown or missing decision ID")
        paths = set()
        for spec in repo.get("files", []) + repo.get("globs", []):
            roles = spec.get("roles") or []
            if not roles or not set(roles) <= set(ROLES):
                raise BuildError(f"{key}: unknown roles {roles}")
            if spec.get("tier") not in ("T1", "T2"):
                raise BuildError(f"{key}: tier must be T1 or T2")
            if "passage" in roles and spec.get("mode") not in MODES:
                raise BuildError(f"{key}: passage needs a §5.3 mode")
            if spec.get("derived") not in (None, *DERIVED):
                raise BuildError(f"{key}: unknown derived text {spec.get('derived')}")
            if spec.get("decision_id") not in repo["decision_ids"]:
                raise BuildError(f"AR-7: {key} file has an unknown or missing decision ID")
            if "path" in spec:
                if spec["path"] in paths:
                    raise BuildError(f"{key}: duplicate path {spec['path']}")
                paths.add(spec["path"])
    return decisions


def denied_path(path: str, deny: dict) -> bool:
    return any(re.search(p, path) for p in deny["excluded_path_patterns"]) or any(
        segment in path.split("/") for segment in deny["excluded_path_segments"]
    )


def _spec_for(repo: dict, path: str) -> tuple[dict | None, dict | None]:
    explicit = next((f for f in repo.get("files", []) if f["path"] == path), None)
    glob = next(
        (
            g
            for g in repo.get("globs", [])
            if any(r.glob_match(p, path, g.get("any_depth", False)) for p in g["patterns"])
        ),
        None,
    )
    return explicit, glob


# ------------------------------------------------------------------ §3.7 tier-1 verification


def verify_tier1(reader: InputReader, config: dict) -> dict:
    """§3.7 steps 1-5; step 6 needs the fetched blobs and runs in ``cross_check_tier1``."""
    t1 = config["tier1"]
    ev = reader.roots["evidence"]
    sv_bytes = reader.read(
        ev / t1["source_verification"]["path"],
        "source_verification",
        sha256=t1["source_verification"]["sha256"],
    )
    sv = _json(sv_bytes, "source-verification")
    pack_bytes = reader.read(
        ev / t1["engineering_v1"]["path"], "engineering_v1", sha256=t1["engineering_v1"]["sha256"]
    )
    approval_bytes = reader.read(
        ev / t1["approval"]["path"], "approval", sha256=t1["approval"]["sha256"]
    )
    if sv.get("approved_pack_file_sha256") != r.sha256_hex(pack_bytes):
        raise BuildError("§3.7: source-verification approves a different engineering-v1 file")
    if sv.get("approval_receipt_sha256") != r.sha256_hex(approval_bytes):
        raise BuildError("§3.7: source-verification names a different approval receipt")
    pack = _json(pack_bytes, "engineering-v1")
    if r.digest(pack) != t1["engineering_v1"]["digest"]:
        raise BuildError("§3.7: engineering-v1 digest differs")
    upstream = sv.get("upstream_files_sha256") or {}
    names = [k[len("upstream/") :] for k in upstream if k.startswith("upstream/")]
    reader.allow_upstream(names)
    snapshots: dict[str, bytes] = {}
    snapshot_dir = ev / t1["snapshot_dir"]
    for key in sorted(upstream):
        data = reader.read(snapshot_dir / key, "tier1", sha256=upstream[key])
        snapshots[key] = data
    statics = {s["id"]: s for s in pack["sources"]}
    if sv.get("source_hashes") != {k: s["content_sha256"] for k, s in statics.items()}:
        raise BuildError("§3.7: source hashes differ from the static entries")
    if any(r.digest(s["text"]) != s["content_sha256"] for s in statics.values()):
        raise BuildError("§3.7: a static entry's content hash differs from its text")
    text_bytes = reader.read(
        ev / t1["cheat_sheet_text"]["path"],
        "tier1_cheat_sheet_text",
        sha256=t1["cheat_sheet_text"]["sha256"],
    )
    extraction = _json(
        reader.read(
            ev / t1["extraction_receipt"]["path"],
            "extraction_receipt",
            sha256=t1["extraction_receipt"]["sha256"],
        ),
        "extraction receipt",
    )
    extractor = reader.read(
        reader.roots["repository"] / t1["extractor"]["path"],
        "extractor",
        sha256=t1["extractor"]["sha256"],
    )
    pdf_key = Path(t1["pdf"]["path"]).relative_to(t1["snapshot_dir"]).as_posix()
    if upstream.get(pdf_key) != t1["pdf"]["sha256"]:
        raise BuildError("§3.7: the cheat-sheet PDF hash differs from source-verification")
    if extraction.get("original_sha256") != upstream.get(pdf_key):
        raise BuildError("§3.7: the extraction receipt names a different PDF")
    if extraction.get("output_sha256") != r.sha256_hex(text_bytes):
        raise BuildError("§3.7: the extraction receipt names a different text")
    if extraction.get("extractor_sha256") != r.sha256_hex(extractor):
        raise BuildError("§3.7: the extraction receipt names a different extractor")
    provenance = _json(
        reader.read(ev / t1["provenance"]["path"], "provenance", sha256=t1["provenance"]["sha256"]),
        "provenance",
    )
    if provenance.get("prepared_at") != t1["prepared_at"]:
        raise BuildError("§3.7: provenance prepared_at differs from the configuration")
    for item in provenance.get("upstream", []):
        if upstream.get(item.get("path")) != item.get("sha256"):
            raise BuildError(f"§3.7: provenance hash differs for {item.get('path')}")
    return {
        "pack": pack,
        "pack_bytes": pack_bytes,
        "snapshots": snapshots,
        "provenance": provenance,
        "cheat_sheet_text": text_bytes.decode("utf-8"),
        "pdf_key": pdf_key,
        "steps": {
            "1_source_verification_sha256": r.sha256_hex(sv_bytes),
            "2_pack_and_approval": True,
            "3_upstream_files": len(upstream),
            "4_static_source_hashes": sorted(statics),
            "5_cheat_sheet_extraction": {
                "text_sha256": r.sha256_hex(text_bytes),
                "receipt_original_sha256": extraction.get("original_sha256"),
                "extractor_sha256": extraction.get("extractor_sha256"),
            },
        },
    }


def _provenance_target(url: str) -> tuple[str, str, str, str] | None:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if parsed.hostname == "github.com" and len(parts) >= 5 and parts[2] == "blob":
        return parts[0], parts[1], parts[3], "/".join(parts[4:])
    if parsed.hostname == "raw.githubusercontent.com" and len(parts) >= 4:
        return parts[0], parts[1], parts[2], "/".join(parts[3:])
    return None


def cross_check_tier1(config: dict, tier1: dict, admitted: dict, raw: dict) -> list[dict]:
    """§3.7 step 6: n1(fetched blob) equals each snapshot; the PDF blob hash equals its pin."""
    by_owner = {(c["owner"], c["repo"]): c for c in config["repositories"]}
    aliases: dict[str, set[str]] = {}
    for alias in config["tier1"].get("commit_aliases", []):
        aliases.setdefault(alias["repo_key"], set()).add(alias["commit"])
    regents = {
        c["repo_key"]: c["regents_notice"]["snapshot"]
        for c in config["repositories"]
        if c.get("regents_notice")
    }
    checked, covered = [], set()
    for item in tier1["provenance"].get("upstream", []):
        target = _provenance_target(item["url"])
        if target is None:
            if item["path"] not in regents.values():
                raise BuildError(f"§3.7: tier-1 snapshot {item['path']} has no pinned source")
            continue
        owner, name, commit, path = target
        repo = by_owner.get((owner, name))
        if repo is None or commit not in {repo["commit"], *aliases.get(repo["repo_key"], ())}:
            raise BuildError(f"§3.7: {item['url']} is not an admitted pin")
        key = (repo["repo_key"], path)
        if key not in admitted or admitted[key]["tier"] != "T1":
            raise BuildError(f"§3.7: {repo['repo_key']}/{path} is not admitted as tier 1")
        blob = raw[key]
        if admitted[key].get("derived") == "pdf_text":
            ok = r.sha256_hex(blob) == item["sha256"] == config["tier1"]["pdf"]["sha256"]
        else:
            try:
                ok = r.n1(blob).encode("utf-8") == tier1["snapshots"][item["path"]]
            except UnicodeDecodeError:
                ok = False
        if not ok:
            raise BuildError(f"§3.7: fetched {repo['repo_key']}/{path} differs from tier 1")
        covered.add(key)
        checked.append({"snapshot": item["path"], "file_key": f"{key[0]}/{key[1]}"})
    for key, spec in admitted.items():
        if spec["tier"] == "T1" and key not in covered:
            raise BuildError(f"§3.7: tier-1 file {key[0]}/{key[1]} has no tier-1 snapshot")
    return sorted(checked, key=lambda x: x["file_key"])


# ------------------------------------------------------------------ fetch receipt (AR-1, AR-2, AR-8)


def check_fetch(config: dict, fetch: dict, config_sha256: str | None = None) -> dict:
    if fetch.get("schema_version") != FETCH_SCHEMA:
        raise BuildError("unsupported fetch receipt schema")
    if fetch.get("hosts_contacted") != ["github.com"]:
        raise BuildError("the fetch contacted a host other than github.com")
    if config_sha256 is not None:
        recorded = [
            x.get("sha256")
            for x in fetch.get("inputs") or []
            if isinstance(x, dict) and x.get("role") == "sources_config"
        ]
        if recorded != [config_sha256]:
            raise BuildError("the fetch was made with a different sources config")
    fetched = {}
    for item in fetch.get("repositories", []):
        if item.get("repo_key") in fetched:
            raise BuildError(f"fetch receipt repeats {item.get('repo_key')}")
        fetched[item.get("repo_key")] = item
    expected = {c["repo_key"]: c for c in config["repositories"]}
    extra = sorted(set(fetched) - set(expected), key=str)
    if extra:
        raise BuildError(f"AR-1: unadmitted repository in the fetch receipt: {extra}")
    missing = sorted(set(expected) - set(fetched))
    if missing:
        raise BuildError(f"AR-1: repository not fetched: {missing}")
    for key, item in fetched.items():
        repo = expected[key]
        if item.get("commit") != repo["commit"]:
            raise BuildError(f"AR-1: {key} was fetched at an unadmitted commit")
        if item.get("url") != repo["url"]:
            raise BuildError(f"AR-1: {key} was fetched from an unadmitted URL")
        tag = repo["ref"].get("name") if repo["ref"]["kind"] == "tag" else None
        if item.get("tag") != tag:
            raise BuildError(f"AR-1: {key} was fetched under an unadmitted ref")
        if not item.get("fetched_at"):
            raise BuildError(f"{key}: fetch receipt has no fetched_at")
    return fetched


def classify(repo: dict, fetched: dict, deny: dict, adn_pages: set[str] | None) -> tuple:
    """AR-2: every listed path is an admitted path or glob match, or a deny-listed exclusion."""
    key = repo["repo_key"]
    listed = {}
    for item in fetched.get("files", []):
        if item.get("path") in listed:
            raise BuildError(f"{key}: fetch receipt lists {item.get('path')} twice")
        listed[item["path"]] = item
    for spec in repo.get("files", []):
        if spec["path"] not in listed:
            raise BuildError(f"AR-2: {key}/{spec['path']} is missing from the fetch")
    admitted, excluded = {}, []
    for path in sorted(listed):
        item = listed[path]
        if denied_path(path, deny):
            excluded.append(
                {"repo_key": key, "path": path, "blob": item.get("blob"), "reason": "deny_listed"}
            )
            continue
        explicit, glob = _spec_for(repo, path)
        if explicit is None and glob is None:
            raise BuildError(f"AR-2: {key}/{path} is not an admitted path")
        if (
            explicit is None
            and glob.get("selection") == "adn-1"
            and (adn_pages is None or path not in adn_pages)
        ):
            raise BuildError(f"AR-6: {key}/{path} is not an ADN-1 page")
        spec = dict(glob or {})
        spec.update(explicit or {})
        spec["rules"] = list((glob or {}).get("rules", [])) + list(
            (explicit or {}).get("rules", [])
        )
        expected_blob = (explicit or {}).get("blob")
        prefix = (explicit or {}).get("blob_prefix")
        if expected_blob and item.get("blob") != expected_blob:
            raise BuildError(f"AR-8: {key}/{path} blob differs from §3.3")
        if prefix and not str(item.get("blob", "")).startswith(prefix):
            raise BuildError(f"AR-8: {key}/{path} blob differs from §3.3")
        admitted[path] = {**spec, "path": path, "receipt": item}
    counts = []
    for glob in repo.get("globs", []):
        count = sum(
            1
            for p in listed
            if any(r.glob_match(x, p, glob.get("any_depth", False)) for x in glob["patterns"])
        )
        counts.append(
            {"patterns": glob["patterns"], "listed": count, "expected": glob.get("listed_count")}
        )
        if "listed_count" in glob and count != glob["listed_count"]:
            raise BuildError(
                f"AR-2: {key} {glob['patterns']} matched {count} paths, "
                f"§3.3 lists {glob['listed_count']}"
            )
    if adn_pages is not None:
        pages = {p for p, s in admitted.items() if s.get("selection") == "adn-1"}
        if pages != adn_pages:
            raise BuildError("AR-6: fetched ADN pages differ from the ADN-1 selection")
    return admitted, excluded, counts


def stored_bytes(reader: InputReader, key: str, item: dict) -> bytes:
    """AR-8: size, sha256 and the git blob ID recomputed from the stored bytes."""
    stored = item.get("stored")
    if stored != f"files/{key}/{item['path']}":
        raise BuildError(f"AR-8: {key}/{item['path']} is not stored where the receipt says")
    data = reader.read(reader.path("tier2", stored), "tier2")
    if (
        len(data) != item.get("size")
        or r.sha256_hex(data) != item.get("raw_sha256")
        or r.git_blob_id(data) != item.get("blob")
    ):
        raise BuildError(f"AR-8: stored bytes of {key}/{item['path']} differ from the receipt")
    return data


# ------------------------------------------------------------------ AR-3, AR-4, AR-5


def ar3_reason(data: bytes, pattern: str) -> str | None:
    try:
        text = r.n1(data)
    except UnicodeDecodeError:
        return "not_utf8"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ast.parse(text)
    except (SyntaxError, ValueError):
        return "not_python3"
    if any(re.search(pattern, line) for line in r.split_lines(text)):
        return "arcmap_era"
    return None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _msbuild_match(pattern: str, path: str) -> bool:
    regex = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            regex, i = regex + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            regex, i = regex + ".*", i + 2
        elif pattern[i] == "*":
            regex, i = regex + "[^/]*", i + 1
        else:
            regex, i = regex + re.escape(pattern[i]), i + 1
    return re.fullmatch(regex, path, re.IGNORECASE) is not None


def live_samples(csproj_text: str, directory: str, candidates: Iterable[str]) -> set[str]:
    """AR-5: Compile items when default items are off, else top-level files minus Remove."""
    try:
        root = ET.fromstring(csproj_text)
    except ET.ParseError as exc:
        raise BuildError(f"AR-5: csproj does not parse: {exc}") from exc
    disabled = any(
        _local(e.tag) == "EnableDefaultCompileItems" and (e.text or "").strip().lower() == "false"
        for group in root.iter()
        if _local(group.tag) == "PropertyGroup"
        for e in group
    )
    compiles = [e for e in root.iter() if _local(e.tag) == "Compile"]
    prefix = directory.rstrip("/") + "/"

    def paths(attribute: str) -> list[str]:
        return [
            prefix + part.strip().replace("\\", "/")
            for e in compiles
            for part in (e.get(attribute) or "").split(";")
            if part.strip()
        ]

    candidates = sorted(candidates)
    if disabled:
        includes = paths("Include")
        return {c for c in candidates if any(_msbuild_match(p, c) for p in includes)}
    removes = paths("Remove")
    return {c for c in candidates if not any(_msbuild_match(p, c) for p in removes)}


# ------------------------------------------------------------------ the build


def _role_string(roles: Iterable[str]) -> str:
    return "+".join(x for x in ROLES if x in set(roles))


def _evidence_relative(reader: InputReader, path: Path) -> str:
    evidence = reader.roots["evidence"]
    if not _inside(path, evidence):
        raise BuildError(f"{path} must live under the evidence root")
    return path.relative_to(evidence).as_posix()


def _segments(
    mode: str, text: str, path: str, label: str | None, names: list[str] | None, needle: str
) -> list[r.Segment]:
    lines = r.split_lines(text)
    if mode == "lines":
        return [r.Segment(1, len(lines), label)] if lines else []
    if mode == "freecad_pyxml":
        return r.segments_freecad_pyxml(text)
    if mode == "freecad_cpp":
        return r.segments_freecad_cpp(lines, path)
    if mode == "python_public_api":
        if names is None:
            raise BuildError("python_public_api needs the public-name index")
        return r.segments_python_public_api(text, names)
    if mode == "rst_sections":
        return r.segments_rst_sections(lines, needle)
    raise BuildError(f"unknown mode {mode}")


def build(
    config: dict,
    config_bytes: bytes,
    reader: InputReader,
    output: Path,
    count_tokens: Callable[[str], int],
    tokenizer: dict,
) -> dict:
    decisions = check_config(config)
    deny = config["deny_lists"]
    tier1 = verify_tier1(reader, config)
    pack = tier1["pack"]
    tier2 = reader.roots["tier2"]
    fetch_path = tier2 / "fetch-receipt.json"
    fetch_bytes = reader.read(fetch_path, "fetch_receipt")
    fetch = _json(fetch_bytes, "fetch receipt")
    fetched = check_fetch(config, fetch, r.sha256_hex(config_bytes))
    briefs = [t["brief"] for t in pack["tasks"] if t["category"] == "aec_automation"]

    admitted: dict[tuple[str, str], dict] = {}
    excluded: list[dict] = []
    raw: dict[tuple[str, str], bytes] = {}
    glob_counts: dict[str, list] = {}
    adn = None
    for repo in config["repositories"]:
        key = repo["repo_key"]
        selection_glob = any(g.get("selection") == "adn-1" for g in repo.get("globs", []))
        adn_pages = None
        if selection_glob:
            hhk = next(
                (f for f in repo["files"] if "index" in f["roles"] and f["path"].endswith(".hhk")),
                None,
            )
            item = next(
                (
                    f
                    for f in fetched[key].get("files", [])
                    if hhk is not None and f["path"] == hhk["path"]
                ),
                None,
            )
            if item is None:
                raise BuildError("AR-6: the ADN index was not fetched")
            hhk_bytes = stored_bytes(reader, key, item)
            adn = r.adn_select(r.n1(hhk_bytes), briefs)
            recorded = dict(fetch.get("adn_selection") or {})
            if recorded.pop("hhk_blob", None) != item["blob"] or recorded != adn:
                raise BuildError(
                    "AR-6: the fetch receipt's ADN-1 selection differs from the re-derived one"
                )
            adn = {**adn, "hhk_blob": item["blob"]}
            adn_pages = set(adn["pages"])
        files, out, counts = classify(repo, fetched[key], deny, adn_pages)
        excluded.extend(out)
        glob_counts[key] = counts
        for path, spec in files.items():
            item = spec["receipt"]
            if item.get("stored") is None:
                if re.search(deny["credential_name_pattern"], path.rsplit("/", 1)[-1]):
                    # The fetch never stores credential-like names, so AR-4 decides unread.
                    excluded.append(
                        {
                            "repo_key": key,
                            "path": path,
                            "blob": item.get("blob"),
                            "reason": "credential_like",
                        }
                    )
                    continue
                raise BuildError(f"AR-8: admitted {key}/{path} was not materialized")
            raw[(key, path)] = stored_bytes(reader, key, item)
            admitted[(key, path)] = spec
        for item in out:
            listed = next(f for f in fetched[key]["files"] if f["path"] == item["path"])
            if listed.get("stored") is not None:
                stored_bytes(reader, key, listed)

    cross_checked = cross_check_tier1(config, tier1, admitted, raw)

    repo_by_key = {c["repo_key"]: c for c in config["repositories"]}
    credential = deny["credential_name_pattern"]
    for (key, path), spec in list(admitted.items()):
        reason = None
        if "AR-3" in spec["rules"]:
            reason = ar3_reason(raw[(key, path)], deny["arcmap_era_pattern"])
        if reason is None and re.search(credential, path.rsplit("/", 1)[-1]):
            reason = "credential_like"
        if reason is not None:
            excluded.append(
                {"repo_key": key, "path": path, "blob": spec["receipt"]["blob"], "reason": reason}
            )
            del admitted[(key, path)]
    for repo in config["repositories"]:
        for glob in repo.get("globs", []):
            if "AR-5" not in glob.get("rules", []):
                continue
            index = next(
                (
                    f
                    for f in repo["files"]
                    if "index" in f["roles"] and f["path"].endswith(".csproj")
                ),
                None,
            )
            if index is None or (repo["repo_key"], index["path"]) not in admitted:
                raise BuildError("AR-5: the csproj index is not admitted")
            directory = index["path"].rsplit("/", 1)[0]
            members = [
                p
                for (k, p) in admitted
                if k == repo["repo_key"] and any(r.glob_match(x, p) for x in glob["patterns"])
            ]
            live = live_samples(r.n1(raw[(repo["repo_key"], index["path"])]), directory, members)
            for path in sorted(set(members) - live):
                spec = admitted.pop((repo["repo_key"], path))
                excluded.append(
                    {
                        "repo_key": repo["repo_key"],
                        "path": path,
                        "blob": spec["receipt"]["blob"],
                        "reason": "not_compiled",
                    }
                )

    order = {c["repo_key"]: i for i, c in enumerate(config["repositories"])}
    excluded.sort(key=lambda x: (order[x["repo_key"]], x["path"]))

    # licenses and notices
    t1 = config["tier1"]
    tier2_relative = _evidence_relative(reader, tier2)
    regents_text = None
    license_files: dict[str, list[dict]] = {}
    for repo in config["repositories"]:
        key = repo["repo_key"]
        entries = []
        for (k, path), spec in sorted(admitted.items()):
            if k == key and "license" in spec["roles"]:
                data = raw[(k, path)]
                if spec["tier"] == "T1":
                    name = _snapshot_for(tier1, repo, path)
                    evidence_path = f"{t1['snapshot_dir']}/{name}"
                    evidence_data = tier1["snapshots"][name]  # N1 of the blob, not the blob
                else:
                    evidence_path = f"{tier2_relative}/{spec['receipt']['stored']}"
                    evidence_data = data
                entries.append(
                    {
                        "path": path,
                        "blob": spec["receipt"]["blob"],
                        "sha256": r.sha256_hex(data),
                        "evidence_path": evidence_path,
                        "evidence_sha256": r.sha256_hex(evidence_data),
                    }
                )
        notice_spec = repo.get("regents_notice")
        if notice_spec:
            snapshot = f"{t1['snapshot_dir']}/{notice_spec['snapshot']}"
            data = tier1["snapshots"].get(notice_spec["snapshot"])
            if data is None or r.sha256_hex(data) != notice_spec["sha256"]:
                raise BuildError("§3.8: the Regents snapshot differs from its pin")
            regents_text = r.regents_notice(
                r.n1(data),
                starts_with=notice_spec["starts_with"],
                contains=notice_spec["contains"],
                last_line_suffix=notice_spec["last_line_suffix"],
                line_count=notice_spec["line_count"],
            )
            entries.append(
                {
                    "path": snapshot,
                    "blob": None,
                    "sha256": notice_spec["sha256"],
                    "evidence_path": snapshot,
                    "evidence_sha256": notice_spec["sha256"],
                }
            )
        if not entries:
            raise BuildError(f"AR-7: {key} has no license file")
        license_files[key] = entries

    # texts, live code, segments, chunks
    cheat_text = tier1["cheat_sheet_text"]
    cheat_lines = r.split_lines(cheat_text)
    names_cache: dict[str, list[str]] = {}
    file_records, rows = [], []
    removals, no_boundary, segments_by_file, oversize_by_file = {}, {}, {}, {}
    notice = None
    prepared: dict[tuple[str, str], tuple] = {}
    for (key, path), spec in admitted.items():
        derived = spec.get("derived")
        normalized = None
        if derived != "pdf_text":
            try:
                normalized = r.n1(raw[(key, path)])
            except UnicodeDecodeError as exc:
                raise BuildError(f"{key}/{path} is not UTF-8") from exc
        label = None
        if derived == "pdf_text":
            text = cheat_text
            span = tuple(spec.get("notice_block_lines") or ())
            found = r.notice_block(cheat_lines)
            if found is None or (span and found != span):
                raise BuildError(f"TXT-1: cheat-sheet notice block is {found}, expected {span}")
            notice = r.notice_text(cheat_lines, found)
        elif derived == "sandcastle_text":
            text, label = r.sandcastle_extract(normalized)
        else:
            text = normalized
        found = r.separator_location(text)
        if found:
            raise BuildError(
                f"{key}/{path} line {found[0]} holds {found[1]}, which the pinned ledger "
                "reader splits on; it cannot be admitted"
            )
        live = None
        if "passage" in spec["roles"]:
            try:
                live = r.live_code(
                    text,
                    r.rule_family(path, derived),
                    notice_lines=tuple(spec["notice_block_lines"])
                    if spec.get("notice_block_lines")
                    else None,
                )
            except r.NotPython3:
                excluded.append(
                    {
                        "repo_key": key,
                        "path": path,
                        "blob": spec["receipt"]["blob"],
                        "reason": "not_python3",
                    }
                )
                continue
        prepared[(key, path)] = (normalized, text, label, live)
    sorted_keys = sorted(prepared, key=lambda k: (order[k[0]], k[1]))
    for file_index, (key, path) in enumerate(sorted_keys):
        spec = admitted[(key, path)]
        repo = repo_by_key[key]
        data = raw[(key, path)]
        derived = spec.get("derived")
        normalized, text, label, live = prepared[(key, path)]
        file_key = f"{key}/{path}" + ("!text" if derived else "")
        header = None
        if live is not None:
            names = None
            if spec["mode"] == "python_public_api":
                names = _public_names(repo, admitted, raw, names_cache)
            segments = _segments(
                spec["mode"],
                text,
                path,
                label,
                names,
                config.get("rst_section_filter", "scipy.integrate"),
            )
            chunk_rows, oversize = r.chunk_segments(text, segments, live, count_tokens)
            for row in chunk_rows:
                rows.append(
                    {
                        **row,
                        "category": repo["category"],
                        "file_key": file_key,
                        "file_index": file_index,
                    }
                )
            removals[file_key] = [list(x) for x in live.removed]
            no_boundary[file_key] = [list(x) for x in live.no_boundary]
            segments_by_file[file_key] = [[s.start, s.end, s.label] for s in segments]
            oversize_by_file[file_key] = oversize
            header = r.file_header(r.split_lines(text), live.removed)
        template_key = (
            "environment"
            if "environment" in spec["roles"]
            and "passage" not in spec["roles"]
            and "environment" in repo["attribution"]
            else "passage"
        )
        template = repo["attribution"][template_key]
        attribution = r.fill_attribution(
            template,
            owner=repo["owner"],
            repo=repo["repo"],
            header=header,
            notice=notice,
            regents_notice=regents_text,
        )
        notices = []
        if header and "{HEADER}" in template:
            notices.append({"kind": "file_header", "text": header})
        if "{NOTICE}" in template:
            notices.append({"kind": "cheat_sheet_notice", "text": notice})
        if "{REGENTS_NOTICE}" in template:
            notices.append({"kind": "regents_notice", "text": regents_text})
        if spec["decision_id"] not in decisions:
            raise BuildError(f"AR-7: {file_key} has no decision ID")
        tier = spec["tier"]
        snapshot = None
        if tier == "T1":
            name = _snapshot_for(tier1, repo, path)
            snapshot = {
                "path": f"{t1['snapshot_dir']}/{name}",
                "sha256": r.sha256_hex(tier1["snapshots"][name]),
            }
        derived_record = None
        if derived == "pdf_text":
            derived_record = {
                "kind": "pdf_text",
                "from_raw_sha256": r.sha256_hex(data),
                "extractor": f"{t1['extractor']['path']} ({t1['extractor'].get('version', '')})",
                "extractor_sha256": t1["extractor"]["sha256"],
                "receipt": dict(t1["extraction_receipt"]),
                "text_sha256": r.sha256_hex(text.encode("utf-8")),
                "text_lines": len(r.split_lines(text)),
            }
        elif derived == "sandcastle_text":
            derived_record = {
                "kind": "sandcastle_text",
                "from_raw_sha256": r.sha256_hex(data),
                "extractor": SANDCASTLE_EXTRACTOR,
                "extractor_sha256": code_hashes(["src/aia_mp1/retrieval.py"])[
                    "src/aia_mp1/retrieval.py"
                ],
                "receipt": None,
                "text_sha256": r.sha256_hex(text.encode("utf-8")),
                "text_lines": len(r.split_lines(text)),
            }
        basis_key = "op2" if spec.get("decision_basis") == "op2" else "default"
        record = {
            "file_key": file_key,
            "file_index": file_index,
            "repo_key": key,
            "path": path,
            "tier": tier,
            "role": _role_string(spec["roles"]),
            "category": repo["category"],
            "mode": spec.get("mode") if "passage" in spec["roles"] else None,
            "language": r.file_language(path, derived),
            "blob": spec["receipt"]["blob"],
            "raw_bytes": len(data),
            "raw_sha256": r.sha256_hex(data),
            "normalized_sha256": (
                r.sha256_hex(normalized.encode("utf-8")) if normalized is not None else None
            ),
            "normalized_lines": len(r.split_lines(normalized)) if normalized is not None else None,
            "derived": derived_record,
            "t1_snapshot": snapshot,
            "license_expression": repo["license_expression"],
            "license_files": license_files[key],
            "attribution": attribution,
            "notices": notices,
            "decision_id": spec["decision_id"],
            "decision_basis": config["decision_basis"][basis_key],
            "version_scope": repo["version_scope"],
            "allowed_uses": list(r.ALLOWED_USES),
            "export_permission": r.EXPORT_PERMISSION,
            "retrieved_at": (t1["prepared_at"] if tier == "T1" else fetched[key]["fetched_at"]),
        }
        if repo.get("license_judgment"):
            record["license_judgment"] = dict(repo["license_judgment"])
        file_records.append(record)
    excluded.sort(key=lambda x: (order[x["repo_key"]], x["path"]))
    chunks, table = r.finalize_chunks(rows)

    repositories = []
    for repo in config["repositories"]:
        ref = repo["ref"]
        repositories.append(
            {
                "repo_key": repo["repo_key"],
                "owner": repo["owner"],
                "repo": repo["repo"],
                "url": repo["url"],
                "commit": repo["commit"],
                "tag": ref.get("name") if ref["kind"] == "tag" else None,
                "tag_object": ref.get("tag_object") if ref["kind"] == "tag" else None,
                "category": repo["category"],
                "tiers": list(repo["tiers"]),
                "decision_ids": list(repo["decision_ids"]),
                "license_expression": repo["license_expression"],
                "license_files": license_files[repo["repo_key"]],
                "version_scope": repo["version_scope"],
                "allowed_uses": list(r.ALLOWED_USES),
                "export_permission": r.EXPORT_PERMISSION,
            }
        )
    record_ref = config["decision_record"]
    judgments = {
        d: repo["license_judgment"]
        for repo in config["repositories"]
        if repo.get("license_judgment")
        for d in repo["decision_ids"]
    }
    manifest = {
        "schema_version": CORPUS_SCHEMA,
        "corpus_id": config["corpus_id"],
        "sources_config": {"path": CONFIG_PATH, "sha256": r.sha256_hex(config_bytes)},
        "fetch_receipt": {
            "path": _evidence_relative(reader, fetch_path),
            "sha256": r.sha256_hex(fetch_bytes),
        },
        "source_verification": dict(t1["source_verification"]),
        "engineering_v1": {
            "path": t1["engineering_v1"]["path"],
            "sha256": r.sha256_hex(tier1["pack_bytes"]),
            "digest": r.digest(pack),
        },
        "decisions": [
            {**d, "record": dict(record_ref)}
            | ({"license_judgment": dict(judgments[d["id"]])} if d["id"] in judgments else {})
            for d in config["decisions"]
        ],
        "deny_lists": config["deny_lists"],
        "repositories": repositories,
        "files": file_records,
        "excluded": excluded,
    }
    chunk_text = "".join(r.jsonl_line(row) + "\n" for row in chunks)
    manifest_text = r.record_json(manifest)
    outputs = {
        "chunks.jsonl": r.write_new(output / "chunks.jsonl", chunk_text),
        "corpus-manifest.json": r.write_new(output / "corpus-manifest.json", manifest_text),
    }
    per_category = {}
    category_of = {f["file_key"]: f["category"] for f in file_records}
    for category in r.CATEGORIES:
        members = [c for c in chunks if c["category"] == category]
        passage_files = [
            f for f in file_records if f["category"] == category and "passage" in f["role"]
        ]
        per_category[category] = {
            "files": len(passage_files),
            "chunks": len(members),
            "tokens": sum(c["qwen_tokens"] for c in members),
            "collapsed_duplicates": sum(
                1
                for x in table["collapsed"]
                if category_of[x["chunk_key"].split("#L", 1)[0]] == category
            ),
            "oversize_lines": sum(
                len(oversize_by_file.get(f["file_key"], [])) for f in passage_files
            ),
        }
    receipt = {
        "schema_version": CORPUS_RECEIPT_SCHEMA,
        "inputs": reader.inputs(),
        "tier1_verification": {**tier1["steps"], "6_cross_check": cross_checked},
        "admitted": [f["file_key"] for f in file_records],
        "excluded": excluded,
        "glob_counts": glob_counts,
        "adn_selection": adn,
        "removals": removals,
        "no_boundary": no_boundary,
        "segments": segments_by_file,
        "oversize_lines": oversize_by_file,
        "chunk_table": table,
        "per_category": per_category,
        "code": code_hashes(
            [
                "src/aia_mp1/retrieval.py",
                "tools/build_rag_corpus.py",
                "tools/qwen_offline_tokenizer.py",
            ]
        ),
        "tokenizer": tokenizer,
        "constants": r.constants(),
        "outputs": dict(outputs),
    }
    outputs["corpus-receipt.json"] = r.write_new(
        output / "corpus-receipt.json", r.record_json(receipt)
    )
    return {"manifest": manifest, "chunks": chunks, "receipt": receipt, "outputs": outputs}


def _snapshot_for(tier1: dict, repo: dict, path: str) -> str:
    for item in tier1["provenance"].get("upstream", []):
        target = _provenance_target(item["url"])
        if target and (target[0], target[1], target[3]) == (repo["owner"], repo["repo"], path):
            return item["path"]
    raise BuildError(f"§3.7: no tier-1 snapshot for {repo['repo_key']}/{path}")


def _public_names(repo: dict, admitted: dict, raw: dict, cache: dict) -> list[str]:
    spec = repo.get("public_names")
    if not spec:
        raise BuildError(f"{repo['repo_key']}: python_public_api needs public_names")
    key = (repo["repo_key"], spec["index"])
    if key not in cache:
        if key not in admitted:
            raise BuildError("the public-name index is not admitted")
        names = r.public_names(r.n1(raw[key]))
        if set(names) != set(spec["names"]):
            raise BuildError(f"public names {sorted(names)} differ from §5.3")
        cache[key] = names
    return cache[key]


def load_counter(gguf: Path):
    """The offline Qwen tokenizer from tools/qwen_offline_tokenizer.py, loaded once."""
    sys.path.insert(0, str(REPO / "tools"))
    import qwen_offline_tokenizer

    tokenizer = qwen_offline_tokenizer.load_tokenizer(gguf)
    return tokenizer.count_tokens, dict(tokenizer.identity)


def build_corpus(
    *,
    config: Path,
    tier2: Path,
    output: Path,
    evidence: Path = DEFAULT_EVIDENCE,
    repository: Path = REPO,
    count_tokens: Callable[[str], int],
    tokenizer: dict,
    gguf: Path | None = None,
    argv: list[str] | None = None,
) -> dict:
    """Run the whole step; tests inject ``count_tokens`` and a synthetic tokenizer identity."""
    reader = InputReader(evidence=evidence, repository=repository, tier2=tier2)

    def work():
        config_bytes = reader.read(config, "sources_config")
        if reader.locate(config) != ("repository", CONFIG_PATH):
            raise BuildError(f"the admission table must be {CONFIG_PATH}")
        if gguf is not None:
            reader.record(
                "tokenizer",
                str(_abs(gguf)),
                "tokenizer",
                tokenizer["gguf_sha256"],
                _abs(gguf).stat().st_size,
            )
        return build(
            _json(config_bytes, "rag-sources"),
            config_bytes,
            reader,
            _abs(output),
            count_tokens,
            tokenizer,
        )

    return run_in_new_directory(output, repository, Path(__file__).resolve(), argv or [], work)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tier2", type=Path, required=True)
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args(argv)
    try:
        count_tokens, identity = load_counter(args.gguf)
        result = build_corpus(
            config=args.config,
            tier2=args.tier2,
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
                "chunks": len(result["chunks"]),
                "files": len(result["manifest"]["files"]),
                "outputs": result["outputs"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
