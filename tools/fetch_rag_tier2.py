"""Tier-2 fetch: pinned partial clones, sparse checkouts and raw blob bytes (AEC-RAG-PACK §4).

This is the only network step of the retrieval-pack build. Each admitted repository is read at its
pinned commit only, through a depth-1, blob-less partial clone with a non-cone sparse checkout.
Every selected path is written to ``files/<repo_key>/<path>`` from ``git cat-file``, so the bytes
are the blob's own and no ``.gitattributes`` conversion applies. Paths matching the deny-lists or
the AR-4 credential name rule are listed but never stored. No project data is sent anywhere.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from aia_mp1.assessment import exclusive
from aia_mp1.retrieval import (
    adn_select,
    constants,
    git_blob_id,
    glob_match,
    n1,
    record_json,
    sha256_hex,
    write_new,
)

REPOSITORY = Path(__file__).resolve().parents[1]
EVID = REPOSITORY.parent / "artifacts" / "evidence" / "P1-03"
CONFIG = REPOSITORY / "config" / "aec-course" / "rag-sources-v1.json"
SCHEMA_VERSION = "rag-fetch-v1"
GIT_ENVIRONMENT = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_LFS_SKIP_SMUDGE": "1",
    "GIT_ASKPASS": "",
}
# protocol v2 as specified; refusing redirects keeps every request on the admitted host.
GIT_OPTIONS = ["-c", "protocol.version=2", "-c", "http.followRedirects=false"]
MINIMUM_GIT = (2, 40)
FULL_SHA = re.compile(r"[0-9a-f]{40}")
REGULAR_MODES = ("100644", "100755")
Runner = Callable[..., bytes]


class GitError(RuntimeError):
    pass


def subprocess_runner(argv: list[str], *, cwd: Path, env: dict[str, str]) -> bytes:
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, check=False)
    if result.returncode:
        command = next((a for a in argv[1:] if a not in GIT_OPTIONS), "")
        message = result.stderr.decode("utf-8", errors="replace").strip()[-500:]
        raise GitError(f"git {command} failed ({result.returncode}): {message}")
    return result.stdout


def git_environment() -> dict[str, str]:
    """No user, system or credential configuration, no prompts and no LFS downloads."""
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C", **GIT_ENVIRONMENT}


def read_input(
    path: Path, role: str, evid: Path, expected_sha256: str | None = None
) -> tuple[bytes, dict]:
    """Read one input; record it as ``{root, path}`` relative to the repository or EVID (§1.4)."""
    if path.is_symlink():
        raise ValueError(f"refusing symlinked input {path}")
    raw = path.read_bytes()
    if expected_sha256 is not None and sha256_hex(raw) != expected_sha256:
        raise ValueError(f"{role} sha256 differs from the pin: {path}")
    located = path.absolute().resolve()
    for root, base in (("repository", REPOSITORY), ("evidence", evid.absolute().resolve())):
        if located.is_relative_to(base):
            where = {"root": root, "path": located.relative_to(base).as_posix()}
            break
    else:
        where = {"root": "absolute", "path": located.as_posix()}
    return raw, {**where, "role": role, "sha256": sha256_hex(raw), "bytes": len(raw)}


def tool_record() -> dict:
    return {
        "path": Path(__file__).resolve().relative_to(REPOSITORY).as_posix(),
        "sha256": sha256_hex(Path(__file__).read_bytes()),
    }


def check_repository(repository: dict, deny: dict, file_roots: tuple[Path, ...]) -> str:
    """AR-1 and the deny-lists for one repository, before any network use; return its host label."""
    owner, name, url = repository["owner"], repository["repo"], repository["url"]
    full = f"{owner}/{name}"
    excluded = {entry.lower() for entry in deny["excluded_repos"]}
    if full.lower() in excluded or any(
        s.lower() in full.lower() for s in deny["excluded_repo_name_substrings"]
    ):
        raise ValueError(f"repository {full} is deny-listed")
    if not FULL_SHA.fullmatch(repository["commit"]):
        raise ValueError(
            f"{repository['repo_key']}: a full 40-hex commit is required, not {repository['commit']!r}"
        )
    ref = repository["ref"]
    if ref.get("kind") not in ("head", "tag") or (ref["kind"] == "tag" and not ref.get("name")):
        raise ValueError(f"{repository['repo_key']}: ref kind must be head or a named tag")
    parts = urlsplit(url)
    if parts.hostname in deny["excluded_hosts"]:
        raise ValueError(f"host {parts.hostname} is deny-listed")
    if parts.scheme == "file" and file_roots:
        if any(Path(parts.path).resolve().is_relative_to(root.resolve()) for root in file_roots):
            return "local"
    elif url == f"https://github.com/{owner}/{name}.git":
        return "github.com"
    raise ValueError(f"refusing {url}: only https://github.com/<owner>/<repo>.git is fetched")


def glob_matches(glob: dict, path: str) -> bool:
    """AR-2 through the library's glob rule, so the corpus builder selects identically."""
    return any(
        glob_match(pattern, path, glob.get("any_depth", False)) for pattern in glob["patterns"]
    )


def sparse_patterns(repository: dict) -> list[str]:
    """§3.3 paths anchored with ``/``; any-depth globs stay unanchored. ADN pages come later."""
    patterns = [
        "/" + re.sub(r"([\\*?\[\]])", r"\\\1", entry["path"]) for entry in repository["files"]
    ]
    for glob in repository["globs"]:
        if glob.get("selection") != "adn-1":
            patterns += [p if glob.get("any_depth") else "/" + p for p in glob["patterns"]]
    return list(dict.fromkeys(patterns))


def exclusion(path: str, deny: dict) -> str | None:
    """``deny_listed`` (EXCLUDED_PATHS), ``credential_like`` (AR-4) or None; neither is stored."""
    if any(re.search(p, path) for p in deny["excluded_path_patterns"]) or set(
        path.split("/")
    ) & set(deny["excluded_path_segments"]):
        return "deny_listed"
    if re.search(deny["credential_name_pattern"], path.rsplit("/", 1)[-1]):
        return "credential_like"
    return None


def parse_ls_remote(raw: bytes) -> dict[str, str]:
    refs = {}
    for line in raw.decode("utf-8").splitlines():
        if line.strip():
            obj, name = line.split("\t", 1)
            refs[name] = obj
    return refs


def parse_ls_tree(raw: bytes) -> dict[str, tuple[str, str, str]]:
    listing = {}
    for record in raw.split(b"\0"):
        if record:
            header, path = record.decode("utf-8").split("\t", 1)
            mode, kind, obj = header.split(" ")
            listing[path] = (mode, kind, obj)
    return listing


class Repository:
    """One repository's git commands, run in the isolated environment and recorded as argv."""

    def __init__(self, entry: dict, output: Path, runner: Runner) -> None:
        self.entry, self.output, self.runner = entry, output, runner
        self.key, self.commit = entry["repo_key"], entry["commit"]
        self.clone = output / "clones" / self.key
        self.commands: list[list[str]] = []

    def git(self, *arguments: str, cwd: Path | None = None) -> bytes:
        argv = ["git", *GIT_OPTIONS, *arguments]
        self.commands.append(argv)
        return self.runner(argv, cwd=cwd or self.clone, env=git_environment())

    def resolve_ref(self) -> dict:
        ref, url = self.entry["ref"], self.entry["url"]
        if ref["kind"] == "head":
            head = parse_ls_remote(self.git("ls-remote", url, "HEAD", cwd=self.output)).get("HEAD")
            if head is None:
                raise ValueError(f"{self.key}: the remote advertises no HEAD")
            return {
                "ref": "HEAD",
                "object": head,
                "peeled": None,
                "head_moved": head != self.commit,
            }
        name = f"refs/tags/{ref['name']}"
        refs = parse_ls_remote(self.git("ls-remote", url, name, name + "^{}", cwd=self.output))
        obj, peeled = refs.get(name), refs.get(name + "^{}")
        if ref.get("annotated"):
            resolved = obj is not None and obj == ref.get("tag_object") and peeled == self.commit
        else:
            resolved = peeled is None and obj == self.commit
        if not resolved:
            raise ValueError(f"{self.key}: tag {ref['name']} does not resolve to the pinned commit")
        return {"ref": name, "object": obj, "peeled": peeled, "head_moved": None}

    def check_out(self) -> None:
        self.git("init", f"clones/{self.key}", cwd=self.output)
        self.git("remote", "add", "origin", self.entry["url"])
        self.git("fetch", "--depth", "1", "--filter=blob:none", "--no-tags", "origin", self.commit)
        if self.git("rev-parse", "FETCH_HEAD").decode().strip() != self.commit:
            raise ValueError(f"{self.key}: FETCH_HEAD differs from the pinned commit")
        patterns = sparse_patterns(self.entry)
        try:
            self.git("sparse-checkout", "set", "--no-cone", *patterns)
        except GitError:  # older git refuses on an unborn HEAD: configure the patterns directly
            self.git("config", "core.sparseCheckout", "true")
            self.git("config", "core.sparseCheckoutCone", "false")
            (self.clone / ".git" / "info").mkdir(exist_ok=True)
            with (self.clone / ".git" / "info" / "sparse-checkout").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write("".join(p + "\n" for p in patterns))
        self.git("checkout", "--detach", self.commit)

    def materialize(
        self, path: str, listing: dict, deny: dict, expected: dict | None = None
    ) -> dict:
        if path not in listing:
            raise ValueError(f"{self.key}: listed path {path} is missing at the pin")
        mode, kind, blob = listing[path]
        if (
            kind != "blob"
            or mode not in REGULAR_MODES
            or any(s in ("", ".", "..") for s in path.split("/"))
        ):
            raise ValueError(f"{self.key}: {path} is not a regular file")
        expected = expected or {}
        if (expected.get("blob") and blob != expected["blob"]) or not blob.startswith(
            expected.get("blob_prefix") or ""
        ):
            raise ValueError(f"{self.key}: {path} blob {blob} differs from the pin")
        record = {
            "path": path,
            "mode": mode,
            "blob": blob,
            "size": None,
            "raw_sha256": None,
            "stored": None,
        }
        if exclusion(path, deny):
            return record
        raw = self.git("cat-file", "blob", blob)
        if git_blob_id(raw) != blob or expected.get("size", len(raw)) != len(raw):
            raise ValueError(
                f"{self.key}: {path} bytes do not match blob {blob} or the pinned size"
            )
        target = self.output / "files" / self.key / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        record.update(size=len(raw), raw_sha256=sha256_hex(raw), stored=f"files/{self.key}/{path}")
        return record

    def add_pages(self, pages: list[str]) -> None:
        """ADN step 6: widen the sparse checkout to the selected pages and check out again."""
        patterns = ["/" + page for page in pages]
        try:
            self.git("sparse-checkout", "add", *patterns)
        except GitError:
            with (self.clone / ".git" / "info" / "sparse-checkout").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write("".join(p + "\n" for p in patterns))
            self.git("sparse-checkout", "reapply")
        self.git("checkout", "--detach", self.commit)


def fetch(
    config_path: Path,
    output: Path,
    *,
    evid: Path = EVID,
    file_roots: tuple[Path, ...] = (),
    runner: Runner = subprocess_runner,
    adn_select: Callable[[str, list[str]], dict] = adn_select,
) -> dict:
    """Fetch every admitted repository at its pin; write the files, the receipt and run.json."""
    started_at = datetime.now(timezone.utc).isoformat()
    config_raw, config_record = read_input(Path(config_path), "sources_config", evid)
    config = json.loads(config_raw)
    if config.get("schema_version") != "rag-sources-v1":
        raise ValueError("the sources configuration is not rag-sources-v1")
    deny = config["deny_lists"]
    hosts = sorted({check_repository(entry, deny, file_roots) for entry in config["repositories"]})
    if len({entry["repo_key"] for entry in config["repositories"]}) != len(config["repositories"]):
        raise ValueError("duplicate repo_key")
    pinned = config["tier1"]["engineering_v1"]
    pack_raw, pack_record = read_input(
        evid / pinned["path"], "engineering_v1", evid, pinned["sha256"]
    )
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError(f"output exists: {output}")
    if output.absolute().resolve().is_relative_to(REPOSITORY):
        raise ValueError("the tier-2 output must be outside the repository")
    version = (
        subprocess_runner(["git", "--version"], cwd=REPOSITORY, env=git_environment())
        .decode()
        .strip()
    )
    numbers = tuple(int(n) for n in re.findall(r"\d+", version)[:2])
    if numbers < MINIMUM_GIT:
        raise ValueError(f"git 2.40 or later is required, found {version}")
    output.mkdir(parents=True, exist_ok=False)
    with exclusive(output):
        status, error = "failed", None
        try:
            records, adn_selection = [], None
            for entry in config["repositories"]:
                repository = Repository(entry, output, runner)
                ls_remote = repository.resolve_ref()
                repository.check_out()
                listing = parse_ls_tree(
                    repository.git("ls-tree", "-r", "-z", "--full-tree", repository.commit)
                )
                selected = {file["path"]: file for file in entry["files"]}
                for glob in entry["globs"]:
                    if glob.get("selection") == "adn-1":
                        continue
                    matched = [path for path in listing if glob_matches(glob, path)]
                    if "listed_count" in glob and len(matched) != glob["listed_count"]:
                        raise ValueError(
                            f"{repository.key}: {len(matched)} paths match {glob['patterns']}, "
                            f"listed_count is {glob['listed_count']}"
                        )
                    for path in matched:
                        selected.setdefault(path, {})
                files = [
                    repository.materialize(path, listing, deny, selected[path])
                    for path in sorted(selected)
                ]
                for glob in entry["globs"]:
                    if glob.get("selection") == "adn-1":
                        adn_selection, pages = select_adn_pages(
                            repository, entry, glob, listing, deny, pack_raw, adn_select
                        )
                        files += pages
                records.append(
                    {
                        "repo_key": repository.key,
                        "url": entry["url"],
                        "commit": repository.commit,
                        "tag": entry["ref"].get("name") if entry["ref"]["kind"] == "tag" else None,
                        "ls_remote": ls_remote,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "commands": repository.commands,
                        "files": sorted(files, key=lambda record: record["path"]),
                    }
                )
            receipt = {
                "schema_version": SCHEMA_VERSION,
                "tool": tool_record(),
                "git_version": version,
                "hosts_contacted": hosts,
                "constants": constants(),
                "inputs": [config_record, pack_record],
                "repositories": records,
                "adn_selection": adn_selection,
            }
            write_new(output / "fetch-receipt.json", record_json(receipt))
            status = "complete"
        except BaseException as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            write_new(
                output / "run.json",
                record_json({**run_record(started_at), "status": status, "error": error}),
            )
    return receipt


def select_adn_pages(repository, entry, glob, listing, deny, pack_raw, adn_select):
    """Rule ADN-1 (§4.2) on the fetched index; return the selection and the materialized pages."""
    [index] = [
        file["path"]
        for file in entry["files"]
        if "index" in file.get("roles", []) and file["path"].endswith(".hhk")
    ]
    briefs = [
        task["brief"]
        for task in json.loads(pack_raw)["tasks"]
        if task["category"] == entry["category"]
    ]
    hhk = (repository.output / "files" / repository.key / index).read_bytes()
    selection = adn_select(n1(hhk), briefs)
    if selection.get("rule", "adn-1") != "adn-1":
        raise ValueError("the page selection is not rule ADN-1")
    pages = selection["pages"]
    for page in pages:
        if page not in listing:
            raise ValueError(f"{repository.key}: selected page {page} is missing at the pin")
        if not glob_matches(glob, page):
            raise ValueError(
                f"{repository.key}: selected page {page} is outside {glob['patterns']}"
            )
    repository.add_pages(pages)
    record = {
        "rule": "adn-1",
        "hhk_blob": listing[index][2],
        "identifiers": selection["identifiers"],
        "keys": selection["keys"],
        "unmatched_keys": selection["unmatched_keys"],
        "pages": pages,
    }
    return record, [repository.materialize(page, listing, deny) for page in pages]


def run_record(started_at: str) -> dict:
    """run.json (§1.3): environment facts, never compared between runs."""

    def repository_git(*arguments: str) -> str:
        return subprocess_runner(
            ["git", "--no-optional-locks", *arguments], cwd=REPOSITORY, env=git_environment()
        ).decode()

    status = repository_git("status", "--porcelain=v1", "-z", "--untracked-files=no")
    return {
        "tool": tool_record(),
        "argv": sys.argv,
        "started_at": started_at,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "aia_mp1_domain": os.environ.get("AIA_MP1_DOMAIN"),
        "repository_commit": repository_git("rev-parse", "HEAD").strip(),
        "modified_tracked_paths": sorted(
            entry[3:] for entry in status.split("\0") if len(entry) > 3
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Tier-2 fetch for the AEC retrieval pack (AEC-RAG-PACK §4)."
    )
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = fetch(args.config, args.output)
    except (OSError, ValueError, GitError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    stored = sum(
        1
        for repository in receipt["repositories"]
        for record in repository["files"]
        if record["stored"]
    )
    print(f"fetched {len(receipt['repositories'])} repositories, {stored} files stored")
    return 0


if __name__ == "__main__":
    sys.exit(main())
