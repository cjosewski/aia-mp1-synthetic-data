import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from rag_tools_fixtures import (
    advance,
    bare_repository,
    blob_id,
    git,
    repository_entry,
    sources_config,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import fetch_rag_tier2 as fetch  # noqa: E402

LF = b"print('a')\n"
CRLF = b"import os\r\nprint(os.sep)\r\n"
FILES = {
    "License.txt": b"Synthetic Apache-2.0 license text\n",
    "README.md": b"# Synthetic samples\n",
    "tools/a.py": LF,
    "tools/deep/b.pyt": b"print('b')\n",
    "tools/win.py": CRLF,
    "unittests/portal_credentials.py": b"PASSWORD = 'synthetic placeholder'\n",
    "docs/Help.chm": b"synthetic compiled help\n",
    "notes.txt": b"never selected\n",
}
BRIEFS = [f"Synthetic Revit brief {n} using FilteredElementCollector." for n in range(10)]


def engineering_v1(evid: Path) -> dict:
    tasks = [
        {"id": f"aec_automation-{n + 1:02d}", "brief": brief, "category": "aec_automation"}
        for n, brief in enumerate(BRIEFS)
    ]
    tasks.insert(
        3, {"id": "gis_scripting-01", "brief": "Synthetic GIS brief.", "category": "gis_scripting"}
    )
    path = evid / "references" / "engineering-v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
    return {
        "path": "references/engineering-v1.json",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def samples(tmp_path, **changes) -> dict:
    url, commit, _ = bare_repository(tmp_path, "samples", FILES, attributes=b"*.py text eol=crlf\n")
    entry = repository_entry(
        "smp",
        "Synthetic",
        "samples",
        url,
        commit,
        {"kind": "head"},
        files=[
            {
                "path": "License.txt",
                "roles": ["license"],
                "tier": "T2",
                "decision_id": "G2",
                "blob": blob_id(FILES["License.txt"]),
            },
            {
                "path": "README.md",
                "roles": ["evidence"],
                "tier": "T2",
                "decision_id": "G2",
                "blob": None,
            },
            {
                "path": "docs/Help.chm",
                "roles": ["evidence"],
                "tier": "T2",
                "decision_id": "G2",
                "blob": None,
            },
        ],
        globs=[
            {
                "patterns": ["*.py", "*.pyt"],
                "any_depth": True,
                "roles": ["passage"],
                "mode": "lines",
                "tier": "T2",
                "decision_id": "G2",
                "listed_count": 4,
            }
        ],
    )
    entry.update(changes)
    return entry


def run(tmp_path, repositories, *, runner=None, adn_select=None, output=None, case=""):
    evid = tmp_path / case / "evid"
    config = tmp_path / case / "rag-sources.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        json.dumps(sources_config(repositories, engineering_v1(evid))), encoding="utf-8"
    )
    output = output or tmp_path / case / "out" / "tier2-v1"
    options = {"runner": runner} if runner else {}
    if adn_select:
        options["adn_select"] = adn_select
    receipt = fetch.fetch(config, output, evid=evid, file_roots=(tmp_path / "served",), **options)
    return receipt, output


def test_fetch_writes_raw_blob_bytes_and_a_complete_receipt(tmp_path):
    receipt, output = run(tmp_path, [samples(tmp_path)])
    assert receipt == json.loads((output / "fetch-receipt.json").read_text(encoding="utf-8"))
    assert receipt["schema_version"] == "rag-fetch-v1" and receipt["hosts_contacted"] == ["local"]
    assert receipt["tool"] == {
        "path": "tools/fetch_rag_tier2.py",
        "sha256": hashlib.sha256(Path(fetch.__file__).read_bytes()).hexdigest(),
    }
    assert [record["role"] for record in receipt["inputs"]] == ["sources_config", "engineering_v1"]
    assert {k: receipt["inputs"][1][k] for k in ("root", "path")} == {
        "root": "evidence",
        "path": "references/engineering-v1.json",
    }
    [repository] = receipt["repositories"]
    files = {record["path"]: record for record in repository["files"]}
    assert (
        list(files)
        == sorted(files)
        == [
            "License.txt",
            "README.md",
            "docs/Help.chm",
            "tools/a.py",
            "tools/deep/b.pyt",
            "tools/win.py",
            "unittests/portal_credentials.py",
        ]
    )
    # cat-file bytes bypass the checkout's eol=crlf conversion in both directions.
    assert (output / "files/smp/tools/a.py").read_bytes() == LF
    assert (output / "files/smp/tools/win.py").read_bytes() == CRLF
    for path in ("License.txt", "README.md", "tools/a.py", "tools/deep/b.pyt", "tools/win.py"):
        raw = (output / "files/smp" / path).read_bytes()
        assert files[path] == {
            "path": path,
            "mode": "100644",
            "blob": blob_id(raw),
            "size": len(raw),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "stored": f"files/smp/{path}",
        }
    for path in (
        "docs/Help.chm",
        "unittests/portal_credentials.py",
    ):  # deny-listed and credential-like
        assert files[path] == {
            "path": path,
            "mode": "100644",
            "blob": blob_id(FILES[path]),
            "size": None,
            "raw_sha256": None,
            "stored": None,
        }
        assert not (output / "files/smp" / path).exists()
    assert repository["ls_remote"] == {
        "ref": "HEAD",
        "object": repository["commit"],
        "peeled": None,
        "head_moved": False,
    }
    assert repository["fetched_at"].endswith("+00:00") and receipt["adn_selection"] is None
    run_record = json.loads((output / "run.json").read_text(encoding="utf-8"))
    assert {
        "tool",
        "argv",
        "started_at",
        "ended_at",
        "python",
        "platform",
        "pythonhashseed",
        "aia_mp1_domain",
        "repository_commit",
        "modified_tracked_paths",
    } <= set(run_record)
    assert sorted(p.name for p in output.iterdir()) == [
        "clones",
        "fetch-receipt.json",
        "files",
        "run.json",
    ]


def test_only_sparse_paths_are_checked_out_and_unselected_blobs_never_downloaded(tmp_path):
    _, output = run(tmp_path, [samples(tmp_path)])
    clone = output / "clones" / "smp"
    present = sorted(
        p.relative_to(clone).as_posix()
        for p in clone.rglob("*")
        if p.is_file() and ".git" not in p.parts
    )
    assert present == [
        "License.txt",
        "README.md",
        "docs/Help.chm",
        "tools/a.py",
        "tools/deep/b.pyt",
        "tools/win.py",
        "unittests/portal_credentials.py",
    ]
    assert (clone / "tools/a.py").read_bytes() == LF.replace(
        b"\n", b"\r\n"
    )  # what a checkout would have stored
    environment = {
        "PATH": os.environ["PATH"],
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_NO_LAZY_FETCH": "1",
    }
    missing = subprocess.run(
        ["git", "cat-file", "-e", blob_id(FILES["notes.txt"])],
        cwd=clone,
        env=environment,
        capture_output=True,
    )
    assert missing.returncode != 0


def test_every_git_command_runs_without_user_configuration_prompts_or_lfs(tmp_path):
    calls = []

    def recording(argv, *, cwd, env):
        calls.append((argv, env))
        return fetch.subprocess_runner(argv, cwd=cwd, env=env)

    receipt, _ = run(tmp_path, [samples(tmp_path)], runner=recording)
    assert calls and all(argv[:3] == ["git", "-c", "protocol.version=2"] for argv, _ in calls)
    for _, env in calls:
        assert {k: env[k] for k in fetch.GIT_ENVIRONMENT} == {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_LFS_SKIP_SMUDGE": "1",
            "GIT_ASKPASS": "",
        }
        assert "HOME" not in env and not any(
            k.startswith("GIT_") and k not in fetch.GIT_ENVIRONMENT for k in env
        )
    recorded = [argv for argv, _ in calls if "--version" not in argv]
    assert receipt["repositories"][0]["commands"] == recorded
    fetched = next(argv for argv in recorded if "fetch" in argv)
    assert fetched[fetched.index("fetch") :] == [
        "fetch",
        "--depth",
        "1",
        "--filter=blob:none",
        "--no-tags",
        "origin",
        receipt["repositories"][0]["commit"],
    ]


def test_refuses_an_existing_output_and_an_output_inside_the_repository(tmp_path):
    existing = tmp_path / "exists"
    existing.mkdir()
    with pytest.raises(ValueError, match="output exists"):
        run(tmp_path, [samples(tmp_path)], output=existing)
    with pytest.raises(ValueError, match="outside the repository"):
        run(tmp_path, [], output=fetch.REPOSITORY / "tier2-v1-test")
    assert not (fetch.REPOSITORY / "tier2-v1-test").exists()


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"url": "https://gitlab.com/Synthetic/samples.git"}, "only https://github.com"),
        ({"url": "https://github.com/Other/samples.git"}, "only https://github.com"),
        ({"owner": "Esri", "repo": "developer-support"}, "deny-listed"),
        ({"repo": "revit-api-stubs"}, "deny-listed"),
        ({"commit": "abc1234"}, "full 40-hex commit"),
        ({"ref": {"kind": "branch", "name": "main"}}, "ref kind"),
    ],
)
def test_refuses_unadmitted_hosts_repositories_and_refs_before_any_write(
    tmp_path, changes, message
):
    with pytest.raises(ValueError, match=message):
        run(tmp_path, [samples(tmp_path, **changes)])
    assert not (tmp_path / "out").exists()


def test_file_urls_need_the_injected_allowlist(tmp_path, capsys):
    evid = tmp_path / "evid"
    config = tmp_path / "rag-sources.json"
    config.write_text(
        json.dumps(sources_config([samples(tmp_path)], engineering_v1(evid))), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="only https://github.com"):
        fetch.fetch(config, tmp_path / "out" / "tier2-v1", evid=evid)
    assert fetch.main(["--config", str(config), "--output", str(tmp_path / "cli-out")]) == 2
    assert capsys.readouterr().err.startswith("error: refusing file://")
    assert not (tmp_path / "cli-out").exists()


def test_tags_must_resolve_to_the_pinned_commit(tmp_path):
    url, commit, tag_object = bare_repository(
        tmp_path, "tagged", {"LICENSE": b"MIT\n"}, tag="1.0.2", annotated=True
    )
    entry = repository_entry(
        "tag",
        "Synthetic",
        "tagged",
        url,
        commit,
        {"kind": "tag", "name": "1.0.2", "annotated": True, "tag_object": tag_object},
        files=[
            {
                "path": "LICENSE",
                "roles": ["license"],
                "tier": "T1",
                "decision_id": "C1",
                "blob": blob_id(b"MIT\n"),
            }
        ],
    )
    receipt, _ = run(tmp_path, [entry])
    assert receipt["repositories"][0]["ls_remote"] == {
        "ref": "refs/tags/1.0.2",
        "object": tag_object,
        "peeled": commit,
        "head_moved": None,
    }
    for ref in (
        {"kind": "tag", "name": "1.0.2", "annotated": True, "tag_object": "0" * 40},
        {"kind": "tag", "name": "1.0.2", "annotated": False},
        {"kind": "tag", "name": "9.9.9", "annotated": False},
    ):
        with pytest.raises(ValueError, match="tag"):
            run(tmp_path, [dict(entry, ref=ref)], case=f"{ref['name']}-{ref['annotated']}")


def test_a_moved_head_is_recorded_and_the_pin_is_still_used(tmp_path):
    entry = samples(tmp_path)
    later = advance(tmp_path, "samples")
    receipt, output = run(tmp_path, [entry])
    assert receipt["repositories"][0]["ls_remote"] == {
        "ref": "HEAD",
        "object": later,
        "peeled": None,
        "head_moved": True,
    }
    assert git("rev-parse", "HEAD", cwd=output / "clones" / "smp") == entry["commit"]
    assert not (output / "clones/smp/later.txt").exists()


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda e: e["files"][0].update(blob="0" * 40), "blob"),
        (lambda e: e["files"][0].update(blob=None, blob_prefix="ffffffff"), "blob"),
        (
            lambda e: e["files"].append(
                {
                    "path": "missing.md",
                    "roles": ["evidence"],
                    "tier": "T2",
                    "decision_id": "G2",
                    "blob": None,
                }
            ),
            "missing",
        ),
        (lambda e: e["globs"][0].update(listed_count=5), "listed_count"),
        (lambda e: e["files"][1].update(size=3), "size"),
    ],
)
def test_pin_mismatches_stop_the_fetch_and_keep_the_failed_directory(tmp_path, mutate, message):
    entry = samples(tmp_path)
    mutate(entry)
    with pytest.raises(ValueError, match=message):
        run(tmp_path, [entry])
    output = tmp_path / "out" / "tier2-v1"
    assert (
        output.is_dir()
        and not (output / ".writer.lock").exists()
        and not (output / "fetch-receipt.json").exists()
    )


def test_a_selected_symlink_is_refused(tmp_path):
    url, commit, _ = bare_repository(tmp_path, "linked", {"a.py": LF}, links={"b.py": "a.py"})
    entry = repository_entry(
        "lnk",
        "Synthetic",
        "linked",
        url,
        commit,
        {"kind": "head"},
        globs=[{"patterns": ["*.py"], "any_depth": True, "tier": "T2", "decision_id": "G2"}],
    )
    with pytest.raises(ValueError, match="not a regular file"):
        run(tmp_path, [entry])


PAGES = [f"html/2025/html/{n:08x}-0000-0000-0000-000000000000.htm" for n in (1, 2, 3)]
HHK = (
    '<HTML><BODY><UL>\r\n<LI><OBJECT type="text/sitemap"><param name="Name" value="FilteredElementCollector class">'
    '<param name="Local" value="html/00000001-0000-0000-0000-000000000000.htm"></OBJECT>\r\n'
    '<UL><LI><OBJECT type="text/sitemap"><param name="Name" value="FilteredElementCollector.OfClass method">'
    '<param name="Local" value="html/00000002-0000-0000-0000-000000000000.htm"></OBJECT></UL>\r\n</UL></BODY></HTML>\r\n'
).encode()


def adn_repository(tmp_path, hhk=HHK, name="chms"):
    files = {"LICENSE": b"MIT\n", "README.md": b"# Synthetic\n", "html/2025/RevitAPI.hhk": hhk}
    files.update({page: f"<html><title>{page}</title></html>\n".encode() for page in PAGES})
    url, commit, _ = bare_repository(tmp_path, name, files)
    return repository_entry(
        "adn",
        "Synthetic",
        "chms",
        url,
        commit,
        {"kind": "head"},
        category="aec_automation",
        files=[
            {
                "path": "LICENSE",
                "roles": ["license"],
                "tier": "T2",
                "decision_id": "A2",
                "blob": blob_id(b"MIT\n"),
            },
            {
                "path": "README.md",
                "roles": ["evidence"],
                "tier": "T2",
                "decision_id": "A2",
                "blob": None,
            },
            {
                "path": "html/2025/RevitAPI.hhk",
                "roles": ["index"],
                "tier": "T2",
                "decision_id": "A2",
                "blob": blob_id(hhk),
                "size": len(hhk),
            },
        ],
        globs=[
            {
                "patterns": ["html/2025/html/*.htm"],
                "any_depth": False,
                "selection": "adn-1",
                "tier": "T2",
                "decision_id": "A2",
            }
        ],
    )


def test_adn_pages_are_selected_from_the_fetched_index_by_rule_adn1_then_materialized(tmp_path):
    receipt, output = run(tmp_path, [adn_repository(tmp_path)])
    selection = receipt["adn_selection"]
    assert {k: selection[k] for k in ("rule", "hhk_blob", "identifiers", "pages")} == {
        "rule": "adn-1",
        "hhk_blob": blob_id(HHK),
        "identifiers": ["FilteredElementCollector"],
        "pages": PAGES[:2],
    }
    assert (
        selection["keys"][0] == "FilteredElementCollector class"
        and len(selection["unmatched_keys"]) == 5
    )
    stored = [record["path"] for record in receipt["repositories"][0]["files"] if record["stored"]]
    assert stored == sorted(["LICENSE", "README.md", "html/2025/RevitAPI.hhk", *PAGES[:2]])
    assert (
        output / "files/adn" / PAGES[1]
    ).read_bytes() == f"<html><title>{PAGES[1]}</title></html>\n".encode()
    assert (
        not (output / "files/adn" / PAGES[2]).exists()
        and not (output / "clones/adn" / PAGES[2]).exists()
    )


def test_adn_selection_receives_the_n1_index_and_the_category_briefs_in_task_order(tmp_path):
    seen = {}

    def select(hhk_text, briefs):
        seen.update(hhk_text=hhk_text, briefs=briefs)
        return {"identifiers": [], "keys": [], "unmatched_keys": [], "pages": PAGES[2:]}

    receipt, _ = run(tmp_path, [adn_repository(tmp_path)], adn_select=select)
    assert seen == {"hhk_text": HHK.decode().replace("\r\n", "\n") + "\n", "briefs": BRIEFS}
    assert receipt["adn_selection"]["pages"] == PAGES[2:]


def test_adn_selection_that_is_empty_or_absent_from_the_pinned_tree_stops_the_fetch(tmp_path):
    empty = HHK.replace(b"FilteredElementCollector", b"UnrelatedType")
    with pytest.raises(ValueError, match="ADN-1 selected 0 pages"):
        run(tmp_path, [adn_repository(tmp_path, hhk=empty, name="empty")], case="empty")

    def absent(hhk_text, briefs):
        return {
            "identifiers": [],
            "keys": [],
            "unmatched_keys": [],
            "pages": ["html/2025/html/ffffffff-0000-0000-0000-000000000000.htm"],
        }

    with pytest.raises(ValueError, match="missing"):
        run(tmp_path, [adn_repository(tmp_path, name="absent")], adn_select=absent, case="absent")


def test_a_failed_fetch_keeps_a_run_record_with_the_error_and_the_receipt_has_the_constants(
    tmp_path,
):
    import copy

    from aia_mp1 import retrieval as r

    entry = samples(tmp_path)
    good_entry = copy.deepcopy(entry)
    entry["globs"][0].update(listed_count=5)
    with pytest.raises(ValueError, match="listed_count"):
        run(tmp_path, [entry], case="failed")
    output = tmp_path / "failed" / "out" / "tier2-v1"
    record = json.loads((output / "run.json").read_text(encoding="utf-8"))
    assert record["status"] == "failed" and "listed_count" in record["error"]
    assert not (output / ".writer.lock").exists()
    receipt, good = run(tmp_path, [good_entry], case="good")
    assert receipt["constants"] == r.constants()
    assert json.loads((good / "run.json").read_text(encoding="utf-8"))["status"] == "complete"


def _altering(match, replace):
    def runner(argv, *, cwd, env):
        out = fetch.subprocess_runner(argv, cwd=cwd, env=env)
        return replace(out) if match(argv) else out

    return runner


def test_a_fetch_head_other_than_the_pin_stops_the_fetch(tmp_path):
    runner = _altering(
        lambda a: "rev-parse" in a and "FETCH_HEAD" in a, lambda out: b"f" * 40 + b"\n"
    )
    with pytest.raises(ValueError, match="FETCH_HEAD differs from the pinned commit"):
        run(tmp_path, [samples(tmp_path)], runner=runner)


def test_cat_file_bytes_that_do_not_hash_to_the_blob_stop_the_fetch(tmp_path):
    runner = _altering(lambda a: "cat-file" in a and "blob" in a, lambda out: out + b"x")
    with pytest.raises(ValueError, match="do not match blob"):
        run(tmp_path, [samples(tmp_path)], runner=runner)


def test_a_deny_listed_host_is_refused_by_name(tmp_path):
    entry = samples(tmp_path)
    entry["url"] = "https://revitapidocs.com/synthetic/samples.git"
    with pytest.raises(ValueError, match="host revitapidocs.com is deny-listed"):
        run(tmp_path, [entry])
