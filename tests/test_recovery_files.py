"""Synthetic file captures, no large-file reads or network access."""

from copy import deepcopy

import pytest

from aia_mp1.recovery_process import FILE_CAPTURE, observe_files, preflight_owned


def experiment():
    files = [
        {"path": path, "bytes": 123, "sha256": "a" * 64}
        for path in (
            "/synthetic/model-00001-of-00002.gguf",
            "/synthetic/model-00002-of-00002.gguf",
            "/synthetic/llama-server",
        )
    ]
    return {
        "runtime_files": files,
        "transport_policy": {"model": files[0]["path"]},
        "owned_process": {"executable": files[2]["path"]},
    }


def test_all_shards_and_executable_are_hashed():
    calls = []

    def read(script, path, timeout):
        assert script == FILE_CAPTURE and timeout == 600
        calls.append(path)
        return f"123|100|200\n{'a' * 64}  {path}\n123|100|200\n"

    config = experiment()
    records = observe_files(config, read)
    assert calls == [f["path"] for f in config["runtime_files"]]
    assert len(records) == 3 and all(row["inode"] == 200 for row in records)


@pytest.mark.parametrize("change", ["missing_shard", "duplicate", "nonfirst", "bad_hash"])
def test_bad_manifest_never_reads_remote(change):
    config = deepcopy(experiment())
    if change == "missing_shard":
        del config["runtime_files"][1]
    elif change == "duplicate":
        config["runtime_files"][1] = config["runtime_files"][0]
    elif change == "nonfirst":
        config["transport_policy"]["model"] = config["runtime_files"][1]["path"]
    else:
        config["runtime_files"][0]["sha256"] = "unverified"
    with pytest.raises(ValueError):
        observe_files(config, lambda *a, **kw: pytest.fail("remote read"))


@pytest.mark.parametrize("change", ["hash", "size", "mtime", "inode", "truncated"])
def test_changed_files_cannot_pass(change):
    def read(script, path, timeout):
        lines = ["123|100|200", f"{'a' * 64}  {path}", "123|100|200"]
        if change == "hash":
            lines[1] = f"{'b' * 64}  {path}"
        elif change == "size":
            lines[0] = lines[2] = "124|100|200"
        elif change == "mtime":
            lines[2] = "123|101|200"
        elif change == "inode":
            lines[2] = "123|100|201"
        else:
            lines.pop()
        return "\n".join(lines)

    with pytest.raises(ValueError):
        observe_files(experiment(), read)


@pytest.mark.parametrize("changed", [False, True])
def test_metadata_is_rechecked_after_http_preflight(monkeypatch, changed):
    class Journal:
        def read(self):
            return {"experiment": experiment()}, [], {}, "head"

    monkeypatch.setattr("aia_mp1.recovery_process.observe_process", lambda *a: {"pid": 123})
    record = {"path": "/synthetic/file", "bytes": 123, "mtime": 100, "inode": 200}
    monkeypatch.setattr("aia_mp1.recovery_process.observe_files", lambda *a: [record])
    monkeypatch.setattr(
        "aia_mp1.recovery_process.preflight_next",
        lambda *a, **kw: {"journal_head_sha256": "head", "execution_enabled": False},
    )

    def read(script, path, timeout):
        assert path == record["path"] and timeout == 30
        return "123|101|200" if changed else "123|100|200"

    if changed:
        with pytest.raises(ValueError, match="metadata changed"):
            preflight_owned(Journal(), None, "synthetic-key", read)
    else:
        assert preflight_owned(Journal(), None, "synthetic-key", read)["runtime_files"] == [record]
