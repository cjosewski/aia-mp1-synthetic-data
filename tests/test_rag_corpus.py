"""Corpus builder (§3, §5): admission refusals, single-file exclusions, AR-5, ADN-1, manifest."""

import json
import shutil
import sys
from pathlib import Path

import pytest
from rag_fixtures import (
    HHK,
    PAGE_1,
    PAGE_2,
    file_spec,
    make_world,
    repository,
)

from aia_mp1 import retrieval as r

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_rag_corpus as bc  # noqa: E402


def build(world):
    return bc.build_corpus(**world.corpus_args())


def refused(tmp_path, match, **hooks):
    world = make_world(tmp_path, **hooks)
    with pytest.raises(bc.BuildError, match=match):
        build(world)
    assert (world.corpus / "run.json").exists()
    assert not (world.corpus / "corpus-manifest.json").exists()
    assert json.loads((world.corpus / "run.json").read_text())["status"] == "failed"
    return world


# ---------------------------------------------------------------- AR-1 and AR-7 refusals


def test_refuses_an_unadmitted_repository(tmp_path):
    def extra(receipt):
        copy = dict(receipt["repositories"][0], repo_key="unlisted")
        receipt["repositories"].append(copy)

    refused(tmp_path, "unadmitted repository", receipt_hook=extra)


def test_refuses_an_unadmitted_commit(tmp_path):
    def moved(receipt):
        receipt["repositories"][1]["commit"] = "9" * 40

    refused(tmp_path, "unadmitted commit", receipt_hook=moved)


@pytest.mark.parametrize("commit", ["main", "2222222"])
def test_refuses_a_branch_name_or_short_sha(tmp_path, commit):
    def branch(config):
        repository(config, "ptt")["commit"] = commit

    refused(tmp_path, "branch name or short SHA", config_hook=branch)


def test_refuses_a_deny_listed_host(tmp_path):
    def host(config):
        repository(config, "ptt")["url"] = "https://revitapidocs.com/synthetic-esri/x.git"

    refused(tmp_path, "deny-listed host", config_hook=host)


@pytest.mark.parametrize(
    "owner,name", [("jeremytammik", "RevitSdkSamples"), ("synthetic", "revit-api-stubs")]
)
def test_refuses_a_deny_listed_repository(tmp_path, owner, name):
    def denied(repositories):
        tbc = next(x for x in repositories if x["repo_key"] == "tbc2025")
        tbc["owner"], tbc["repo"] = owner, name

    refused(tmp_path, "deny-listed repository", repositories_hook=denied)


def test_refuses_a_repository_without_a_license_file(tmp_path):
    def no_license(config):
        file_spec(config, "ptt", "License.txt")["roles"] = ["evidence"]

    refused(tmp_path, "no license file", config_hook=no_license)


def test_refuses_a_missing_attribution(tmp_path):
    def blank(config):
        repository(config, "ptt")["attribution"]["passage"] = " "

    refused(tmp_path, "no attribution", config_hook=blank)


def test_refuses_a_missing_decision_id(tmp_path):
    def missing(config):
        file_spec(config, "ospdoc", "src/wipe.rst")["decision_id"] = None

    refused(tmp_path, "decision ID", config_hook=missing)


def test_refuses_an_export_other_than_local_only(tmp_path):
    def permitted(config):
        config["export_permission"] = "permitted"

    refused(tmp_path, "local_only", config_hook=permitted)


def test_refuses_more_than_the_four_uses(tmp_path):
    def uses(config):
        config["allowed_uses"].append("public_export")

    refused(tmp_path, "four assessed uses", config_hook=uses)


# ---------------------------------------------------------------- AR-2, AR-6, AR-8, §3.7


def test_refuses_a_path_outside_section_3_3(tmp_path):
    def unlisted(receipt):
        files = receipt["repositories"][0]["files"]
        files.append(dict(files[0], path="docs/unlisted.md"))

    refused(tmp_path, "not an admitted path", receipt_hook=unlisted)


def test_refuses_a_glob_count_other_than_section_3_3(tmp_path):
    def count(config):
        repository(config, "freecad102")["globs"][0]["listed_count"] = 55

    refused(tmp_path, "matched 1 paths", config_hook=count)


def test_refuses_a_blob_other_than_section_3_3(tmp_path):
    def blob(config):
        file_spec(config, "tbc2025", "License.md")["blob"] = "0" * 40

    refused(tmp_path, "blob differs", config_hook=blob)


def test_refuses_stored_bytes_that_differ_from_the_receipt(tmp_path):
    world = make_world(tmp_path)
    world.stored[("ptt", "License.txt")].write_bytes(b"tampered\n")
    with pytest.raises(bc.BuildError, match="AR-8: stored bytes"):
        build(world)


def test_refuses_a_size_mismatch(tmp_path):
    def size(receipt):
        receipt["repositories"][1]["files"][0]["size"] += 1

    refused(tmp_path, "AR-8: stored bytes", receipt_hook=size)


def test_refuses_an_adn_selection_other_than_adn_1(tmp_path):
    def pages(receipt):
        receipt["adn_selection"]["pages"] = ["html/2025/" + PAGE_1]

    refused(tmp_path, "AR-6", receipt_hook=pages)


def test_refuses_a_tier1_hash_mismatch_in_source_verification(tmp_path):
    def wrong(verification):
        key = sorted(verification["upstream_files_sha256"])[0]
        verification["upstream_files_sha256"][key] = "f" * 64

    refused(tmp_path, "differs from the pinned", verification_hook=wrong)


def test_refuses_an_extraction_receipt_mismatch(tmp_path):
    def wrong(extraction):
        extraction["output_sha256"] = "0" * 64

    refused(tmp_path, "extraction receipt names a different text", extraction_hook=wrong)


def test_refuses_a_fetched_tier1_blob_that_differs_from_its_snapshot(tmp_path):
    world = make_world(tmp_path)
    data = b"MIT License\nCopyright (c) 2013 Someone Else\n"
    world.stored[("tbc2025", "License.md")].write_bytes(data)
    receipt = json.loads((world.tier2 / "fetch-receipt.json").read_text())
    entry = next(
        f
        for x in receipt["repositories"]
        if x["repo_key"] == "tbc2025"
        for f in x["files"]
        if f["path"] == "License.md"
    )
    entry.update(size=len(data), raw_sha256=r.sha256_hex(data), blob=r.git_blob_id(data))
    config = json.loads(world.config_path.read_text())
    file_spec(config, "tbc2025", "License.md")["blob"] = entry["blob"]
    world.config_path.write_text(r.record_json(config))
    receipt["inputs"][0]["sha256"] = r.sha256_hex(world.config_path.read_bytes())
    (world.tier2 / "fetch-receipt.json").write_text(r.record_json(receipt))
    with pytest.raises(bc.BuildError, match="differs from tier 1"):
        build(world)


def test_refuses_an_existing_output_directory(tmp_path):
    world = make_world(tmp_path)
    world.corpus.mkdir(parents=True)
    with pytest.raises(bc.BuildError, match="AR-9"):
        build(world)
    assert list(world.corpus.iterdir()) == []


def test_refuses_a_symlinked_input(tmp_path):
    world = make_world(tmp_path)
    target = world.stored[("ptt", "License.txt")]
    copy = tmp_path / "elsewhere.txt"
    copy.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(copy)
    with pytest.raises(bc.BuildError, match="symlink refused"):
        build(world)


def test_read_input_allowlist_and_deny_list(tmp_path):
    world = make_world(tmp_path)
    reader = bc.InputReader(evidence=world.evidence, repository=world.repository, tier2=world.tier2)
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    with pytest.raises(bc.BuildError, match="outside the allowlist"):
        reader.read(outside, "x")
    unlisted = world.evidence / "references" / "other.json"
    unlisted.write_text("{}")
    with pytest.raises(bc.BuildError, match="not on the allowlist"):
        reader.read(unlisted, "x")
    for relative, reason in [
        ("aec-course/assessments/run-1/notes.json", "forbidden path segment"),
        ("references/labels/x.json", "forbidden path segment"),
        ("references/data.jsonl", "forbidden file name"),
        (
            "qualification/m4-recovery-contract-followup-20261117/packet-final/sources/other.txt",
            "qualification",
        ),
        ("aec-course/analysis/other.json", "aec-course/analysis"),
        ("aec-course/api-development-1/x.json", "api-"),
    ]:
        path = world.evidence / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
        with pytest.raises(bc.BuildError, match=reason):
            reader.read(path, "x")
    upstream = world.evidence / r.UPSTREAM_PREFIX / "unnamed.txt"
    upstream.write_text("x")
    with pytest.raises(bc.BuildError, match="not named in source-verification"):
        reader.read(upstream, "tier1")
    pinned = world.evidence / "references/engineering-v1.json"
    with pytest.raises(bc.BuildError, match="differs from the pinned"):
        reader.read(pinned, "engineering_v1", sha256="0" * 64)
    data = reader.read(pinned, "engineering_v1")
    assert reader.inputs() == [
        {
            "root": "evidence",
            "path": "references/engineering-v1.json",
            "role": "engineering_v1",
            "sha256": r.sha256_hex(data),
            "bytes": len(data),
        }
    ]


def test_input_path_problem_for_recorded_inputs():
    assert r.input_path_problem("tier2", "files/ptt/License.txt") is None
    assert r.input_path_problem("corpus", "chunks.jsonl") is None
    assert r.input_path_problem("repository", "prompts/generator-assessed-v3-guidance.md") is None
    assert r.input_path_problem("evidence", "aec-course/assessments/x/data.jsonl")
    assert r.input_path_problem("tier2", "../outside")
    assert r.input_path_problem("tokenizer", "/tmp/other.gguf")
    assert r.input_path_problem("repository", "config/aec-course/rubric-v2.json")


# ---------------------------------------------------------------- exclusions and AR-5


def test_single_file_exclusions_and_their_reasons(tmp_path):
    manifest = build(make_world(tmp_path))["manifest"]
    assert [(x["repo_key"], x["path"], x["reason"]) for x in manifest["excluded"]] == [
        ("ptt", "RevitSdkSamples/sample.py", "deny_listed"),
        ("ptt", "legacy/map_tool.py", "arcmap_era"),
        ("ptt", "legacy/old_tool.py", "not_python3"),
        ("ptt", "unittests/portal_credentials.py", "credential_like"),
        ("tbc2025", "BuildingCoder/CmdRemoved.cs", "not_compiled"),
    ]
    assert all(len(x["blob"]) == 40 for x in manifest["excluded"])
    admitted = {f["file_key"] for f in manifest["files"]}
    assert "ptt/tools/convert.pyt" in admitted
    assert "tbc2025/BuildingCoder/CmdBoundingBox.cs" in admitted


def test_ar5_compile_remove_and_disabled_default_items():
    candidates = ["BuildingCoder/A.cs", "BuildingCoder/B.cs", "BuildingCoder/Old.cs"]
    remove = (
        '<Project Sdk="Microsoft.NET.Sdk"><ItemGroup>'
        '<Compile Remove="Old.cs" /><Compile Update="A.cs" /></ItemGroup></Project>'
    )
    assert bc.live_samples(remove, "BuildingCoder", candidates) == {
        "BuildingCoder/A.cs",
        "BuildingCoder/B.cs",
    }
    explicit = (
        '<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">'
        "<PropertyGroup><EnableDefaultCompileItems>False</EnableDefaultCompileItems>"
        '</PropertyGroup><ItemGroup><Compile Include="A.cs" />'
        '<Compile Include="Sub\\Deep.cs" /></ItemGroup></Project>'
    )
    assert bc.live_samples(explicit, "BuildingCoder", candidates) == {"BuildingCoder/A.cs"}


def test_ar5_semicolon_lists_and_case_insensitive_matching():
    candidates = ["BuildingCoder/A.cs", "BuildingCoder/B.cs", "BuildingCoder/Old.cs"]
    remove = (
        '<Project Sdk="Microsoft.NET.Sdk"><ItemGroup>'
        '<Compile Remove="old.cs;B.cs" /></ItemGroup></Project>'
    )
    assert bc.live_samples(remove, "BuildingCoder", candidates) == {"BuildingCoder/A.cs"}
    explicit = (
        "<Project><PropertyGroup><EnableDefaultCompileItems>false</EnableDefaultCompileItems>"
        '</PropertyGroup><ItemGroup><Compile Include="a.cs; Old.cs" /></ItemGroup></Project>'
    )
    assert bc.live_samples(explicit, "BuildingCoder", candidates) == {
        "BuildingCoder/A.cs",
        "BuildingCoder/Old.cs",
    }


# ---------------------------------------------------------------- ADN-1 (§4.2)


def entry(name, local=None, subs=()):
    params = f'<param name="Name" value="{name}">'
    if local:
        params += f'<param name="Local" value="{local}">'
    sub = ""
    if subs:
        sub = "<UL>" + "".join(entry(n, x) for n, x in subs) + "</UL>"
    return f'<LI> <OBJECT type="text/sitemap">{params}</OBJECT>{sub}'


def page(n):
    return f"html/{n:08d}-0000-0000-0000-000000000000.htm"


def test_adn1_on_the_fixture_index():
    briefs = ["List walls with a FilteredElementCollector. Use Document.GetElement for lookups."]
    selection = r.adn_select(HHK, briefs)
    assert selection["identifiers"] == ["FilteredElementCollector", "Document.GetElement"]
    assert selection["pages"] == ["html/2025/" + PAGE_1, "html/2025/" + PAGE_2]
    assert "GetElement property" in selection["unmatched_keys"]
    assert "FilteredElementCollector interface" in selection["unmatched_keys"]


def test_adn1_keys_direct_locals_get_enumeration_members_and_filters():
    index = (
        "<UL>"
        + "".join(
            [
                entry("BoundingBox property", page(1)),
                entry("HOST_AREA_COMPUTED enumeration member", page(2)),
                entry("OST_Walls enumeration member", page(3)),
                entry(
                    "WallType class",
                    page(4),
                    [("WallType Members", page(5)), ("WallType Properties", "html/not-a-guid.htm")],
                ),
                entry("AsDouble method", None, [("Parameter.AsDouble Method", page(6))]),
                entry("Unrelated class", page(7)),
            ]
        )
        + "</UL>"
    )
    brief = (
        "Call get_BoundingBox and read HOST_AREA_COMPUTED and OST_Walls for a WallType; "
        "use Parameter.AsDouble and Missing.Thing."
    )
    selection = r.adn_select(index, [brief])
    assert r.adn_keys("get_BoundingBox") == [("BoundingBox property", None)]
    assert r.adn_keys("OST_Walls") == [("OST_Walls enumeration member", None)]
    assert r.adn_keys("Parameter.AsDouble") == [
        ("AsDouble method", "Parameter.AsDouble"),
        ("AsDouble property", "Parameter.AsDouble"),
    ]
    assert selection["pages"] == ["html/2025/" + page(n) for n in (1, 2, 3, 4, 5, 6)]
    assert "Thing method" in selection["unmatched_keys"]
    assert "WallType interface" in selection["unmatched_keys"]


def test_adn1_stops_when_empty_or_above_sixty_pages():
    briefs = ["Use the FilteredElementCollector."]
    big = (
        "<UL>"
        + entry(
            "FilteredElementCollector class",
            None,
            [(f"FilteredElementCollector.M{n} Method", page(n)) for n in range(61)],
        )
        + "</UL>"
    )
    with pytest.raises(ValueError, match="61 pages"):
        r.adn_select(big, briefs)
    assert len(r.adn_select(big, briefs, enforce_limits=False)["pages"]) == 61
    with pytest.raises(ValueError, match="0 pages"):
        r.adn_select("<UL></UL>", briefs)


# ---------------------------------------------------------------- manifest


FILE_FIELDS = {
    "file_key",
    "file_index",
    "repo_key",
    "path",
    "tier",
    "role",
    "category",
    "mode",
    "language",
    "blob",
    "raw_bytes",
    "raw_sha256",
    "normalized_sha256",
    "normalized_lines",
    "derived",
    "t1_snapshot",
    "license_expression",
    "license_files",
    "attribution",
    "notices",
    "decision_id",
    "decision_basis",
    "version_scope",
    "allowed_uses",
    "export_permission",
    "retrieved_at",
}


def test_manifest_fields_and_file_order(tmp_path):
    world = make_world(tmp_path)
    result = build(world)
    manifest = json.loads((world.corpus / "corpus-manifest.json").read_text())
    assert manifest == result["manifest"]
    assert set(manifest) == {
        "schema_version",
        "corpus_id",
        "sources_config",
        "fetch_receipt",
        "source_verification",
        "engineering_v1",
        "decisions",
        "deny_lists",
        "repositories",
        "files",
        "excluded",
    }
    order = [x["repo_key"] for x in world.config["repositories"]]
    keys = [(order.index(f["repo_key"]), f["path"]) for f in manifest["files"]]
    assert keys == sorted(keys)
    assert [f["file_index"] for f in manifest["files"]] == list(range(len(manifest["files"])))
    for record in manifest["files"]:
        extra = {"license_judgment"} if record["repo_key"] == "adn2025" else set()
        assert set(record) == FILE_FIELDS | extra
        assert record["allowed_uses"] == list(r.ALLOWED_USES)
        assert record["export_permission"] == "local_only"
        assert record["license_files"] and record["attribution"] and record["decision_id"]
        assert record["retrieved_at"] == (
            "2026-11-10T00:00:00+00:00" if record["tier"] == "T1" else "2026-11-21T00:00:00+00:00"
        )
    by_key = {f["file_key"]: f for f in manifest["files"]}
    pdf = by_key["arcpy/docs/ArcPy-Cheatsheet.pdf!text"]
    assert pdf["derived"]["kind"] == "pdf_text" and pdf["normalized_sha256"] is None
    page = by_key[f"adn2025/html/2025/{PAGE_1}!text"]
    assert page["derived"]["extractor"] == "aia_mp1.retrieval.sandcastle_text"
    assert page["language"] == "html"
    walls = by_key["tbc2025/BuildingCoder/CmdListWalls.cs"]
    assert walls["attribution"].endswith(
        " File header: Copyright (C) 2009-2021 by Synthetic Tammik, Example Inc. All rights "
        "reserved."
    )
    assert walls["t1_snapshot"]["path"].startswith("references/preparation-20261110/upstream/")
    assert by_key["freecad102/src/Mod/Part/App/FeaturePartBox.cpp"]["decision_basis"] == (
        "synthetic OP-2 basis"
    )
    assert by_key["freecad102/src/Mod/Part/parttests/part_test_objects.py"]["role"] == (
        "passage+environment"
    )
    env = by_key["ospdoc/conf.py"]
    assert "Regents notice, verbatim:\nCopyright @ 1999-2020" in env["attribution"]
    assert env["notices"][0]["kind"] == "regents_notice"
    decisions = {d["id"]: d for d in manifest["decisions"]}
    assert decisions["A2"]["license_judgment"]["statement"] == "synthetic judgment"
    assert "license_judgment" not in decisions["A1"]
    assert decisions["G1"]["record"] == {"path": "ITERATION_LOG.md", "entry": "Synthetic decisions"}
    repo = manifest["repositories"][0]
    assert set(repo) == {
        "repo_key",
        "owner",
        "repo",
        "url",
        "commit",
        "tag",
        "tag_object",
        "category",
        "tiers",
        "decision_ids",
        "license_expression",
        "license_files",
        "version_scope",
        "allowed_uses",
        "export_permission",
    }
    receipt = json.loads((world.corpus / "corpus-receipt.json").read_text())
    assert receipt["outputs"]["corpus-manifest.json"] == r.sha256_hex(
        (world.corpus / "corpus-manifest.json").read_bytes()
    )
    assert all(r.input_path_problem(x["root"], x["path"]) is None for x in receipt["inputs"])
    assert not (world.corpus / ".writer.lock").exists()


def test_chunk_rows_are_sorted_verbatim_and_complete(tmp_path):
    world = make_world(tmp_path)
    result = build(world)
    rows = [json.loads(x) for x in (world.corpus / "chunks.jsonl").read_text().splitlines()]
    assert rows == result["chunks"]
    order = {c: i for i, c in enumerate(r.CATEGORIES)}
    keys = [(order[x["category"]], x["file_index"], x["start"], x["end"]) for x in rows]
    assert keys == sorted(keys)
    assert set(rows[0]) == {
        "chunk_key",
        "category",
        "file_key",
        "file_index",
        "start",
        "end",
        "segment_label",
        "removed_within",
        "text",
        "content_sha256",
        "qwen_tokens",
        "n_terms",
    }
    by_key = {x["chunk_key"]: x for x in rows}
    route = by_key["ptt/transit/route_tools.py#L4-L11"]
    assert route["removed_within"] == [[10, 10, "commented_out_code"]]
    assert "overwriteOutput" not in route["text"]
    source = r.n1(world.stored[("ptt", "transit/route_tools.py")].read_bytes())
    assert r.reslice(source, 4, 11, route["removed_within"]) == route["text"]
    cheat = by_key["arcpy/docs/ArcPy-Cheatsheet.pdf!text#L1-L10"]
    assert cheat["removed_within"] == [[7, 8, "notice_block"]] and "©" not in cheat["text"]
    assert by_key["freecad102/src/Mod/Part/App/ConePy.xml#L12-L14"]["segment_label"] == (
        "Part.Cone attribute Radius1"
    )
    assert by_key["scipy1161/scipy/integrate/_ivp/ivp.py#L8-L19"]["segment_label"] == (
        "solve_ivp signature and docstring"
    )
    assert not any("_private" in x["text"] for x in rows)


# ---------------------------------------------------------------- CLI and the real tier 1


def test_cli_failure_prints_an_error_and_exits_2(tmp_path, capsys):
    world = make_world(tmp_path)
    code = bc.main(
        [
            "--config",
            str(world.config_path),
            "--tier2",
            str(world.tier2),
            "--gguf",
            str(tmp_path / "missing.gguf"),
            "--output",
            str(world.corpus),
            "--evidence",
            str(world.evidence),
        ]
    )
    assert code == 2
    assert capsys.readouterr().err.startswith("error: ")
    assert not world.corpus.exists()


@pytest.mark.skipif(not bc.DEFAULT_EVIDENCE.is_dir(), reason="real evidence is absent")
def test_real_tier1_inputs_verify_against_the_admission_table():
    """Read-only: §3.7 steps 1-5 and the tier-1 mapping on the allowlisted real inputs."""
    reader = bc.InputReader(evidence=bc.DEFAULT_EVIDENCE, repository=bc.REPO)
    config = json.loads(reader.read(bc.REPO / bc.CONFIG_PATH, "sources_config"))
    bc.check_config(config)
    tier1 = bc.verify_tier1(reader, config)
    assert tier1["steps"]["3_upstream_files"] == 28
    by_owner = {(c["owner"], c["repo"]): c for c in config["repositories"]}
    mapped = set()
    for item in tier1["provenance"]["upstream"]:
        target = bc._provenance_target(item["url"])
        if target is not None:
            mapped.add((by_owner[target[:2]]["repo_key"], target[3]))
    expected = {
        (c["repo_key"], f["path"])
        for c in config["repositories"]
        for f in c["files"]
        if f["tier"] == "T1"
    }
    assert mapped == expected and len(expected) == 27
    lines = r.split_lines(tier1["cheat_sheet_text"])
    assert r.notice_block(lines) == (290, 293)
    assert len(r.static_source_spans(tier1["pack_bytes"].decode("utf-8"))) == 5
    aec = [t["brief"] for t in tier1["pack"]["tasks"] if t["category"] == "aec_automation"]
    assert len(r.adn_identifiers(aec)) == 17
    assert all(x["root"] in ("evidence", "repository") for x in reader.inputs())


# ------------------------------------------------ line separators the ledger reader splits on


def _inject_separator(char):
    def inject(repositories):
        ospdoc = next(x for x in repositories if x["repo_key"] == "ospdoc")
        spec = next(f for f in ospdoc["files"] if f["path"] == "src/wipe.rst")
        spec["_content"] = (
            f".. function:: wipe()\n\n   Clear the model{char}before a new truss.\n"
        ).encode("utf-8")

    return inject


@pytest.mark.parametrize("char", ["\x85", "\u2028", "\u2029"])
def test_refuses_text_the_ledger_reader_would_split(tmp_path, char):
    refused(
        tmp_path, "ospdoc/src/wipe.rst line 3 holds U\\+", repositories_hook=_inject_separator(char)
    )


@pytest.mark.parametrize("char", ["\x85", "\u2028", "\u2029"])
def test_the_pack_build_reads_chunks_by_lf_and_refuses_the_separator(tmp_path, monkeypatch, char):
    import build_rag_pack as bp

    world = make_world(tmp_path, repositories_hook=_inject_separator(char))
    with monkeypatch.context() as patch:
        patch.setattr(r, "separator_location", lambda text: None)
        build(world)
    assert any(char in line for line in (world.corpus / "chunks.jsonl").read_text().split("\n"))
    with pytest.raises(bp.BuildError, match="pinned ledger reader"):
        bp.build_pack(**world.pack_args())


# --------------------------------------------- roots under, behind or inside forbidden places


def _relocate(world, destination):
    """Move the tier-2 tree to ``destination`` and return the new root."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(world.tier2), str(destination))
    return destination


@pytest.mark.parametrize("area", ["assessments", "api-judge-x"])
def test_refuses_a_tier2_root_inside_a_forbidden_area(tmp_path, area):
    world = make_world(tmp_path)
    root = _relocate(world, world.evidence / "aec-course" / area / "tier2-v1")
    with pytest.raises(bc.BuildError, match="input refused .*(assessments|api-)"):
        build_with(world, tier2=root)


def test_refuses_a_symlinked_root(tmp_path):
    world = make_world(tmp_path)
    real = _relocate(world, world.evidence / "aec-course" / "rag" / "tier2-real")
    world.tier2.symlink_to(real)
    with pytest.raises(bc.BuildError, match="symlink refused"):
        build(world)


def test_refuses_a_root_behind_a_symlinked_ancestor(tmp_path):
    world = make_world(tmp_path)
    real = _relocate(world, world.evidence / "aec-course" / "assessments" / "x" / "tier2-v1")
    link = world.evidence / "aec-course" / "rag" / "via"
    link.symlink_to(real.parent)
    with pytest.raises(bc.BuildError, match="forbidden path segment 'assessments'"):
        build_with(world, tier2=link / "tier2-v1")


def build_with(world, **extra):
    return bc.build_corpus(**world.corpus_args(**extra))


def test_refuses_a_fetch_that_contacted_another_host(tmp_path):
    refused(
        tmp_path,
        "other than github.com",
        receipt_hook=lambda rc: rc.update(hosts_contacted=["local"]),
    )


def test_refuses_a_fetch_made_with_another_sources_config(tmp_path):
    def other(receipt):
        receipt["inputs"][0]["sha256"] = "0" * 64

    refused(tmp_path, "different sources config", receipt_hook=other)
    refused(tmp_path / "none", "different sources config", receipt_hook=lambda rc: rc.pop("inputs"))


def test_the_returned_receipt_equals_the_receipt_on_disk(tmp_path):
    world = make_world(tmp_path)
    result = build(world)
    written = json.loads((world.corpus / "corpus-receipt.json").read_text(encoding="utf-8"))
    assert result["receipt"] == written
    assert r.record_json(result["receipt"]) == (world.corpus / "corpus-receipt.json").read_text()
    assert set(result["outputs"]) == {"chunks.jsonl", "corpus-manifest.json", "corpus-receipt.json"}


def test_code_hashes_are_taken_once_per_process(tmp_path, monkeypatch):
    monkeypatch.setattr(bc, "REPO", tmp_path)
    (tmp_path / "mod_once.py").write_text("one\n", encoding="utf-8")
    first = bc.code_hashes(["mod_once.py", "absent.py"])
    (tmp_path / "mod_once.py").write_text("two\n", encoding="utf-8")
    assert bc.code_hashes(["mod_once.py"]) == {"mod_once.py": first["mod_once.py"]}
    assert first["absent.py"] is None and first["mod_once.py"] == r.sha256_hex(b"one\n")
    monkeypatch.delitem(bc._CODE_AT_START, "mod_once.py")
    monkeypatch.delitem(bc._CODE_AT_START, "absent.py")


def test_license_entries_hash_the_bytes_at_their_evidence_path(tmp_path):
    world = make_world(tmp_path)
    manifest = build(world)["manifest"]
    entries = [e for x in manifest["repositories"] for e in x["license_files"]]
    assert entries
    for entry in entries:
        assert (
            r.sha256_hex((world.evidence / entry["evidence_path"]).read_bytes())
            == entry["evidence_sha256"]
        )
    tier1 = [e for e in entries if "preparation" in e["evidence_path"]]
    assert tier1 and any(e["evidence_sha256"] != e["sha256"] for e in tier1)  # N1 adds an LF


def test_a_stored_credential_named_file_is_excluded_not_admitted(tmp_path, monkeypatch):
    import rag_fixtures

    monkeypatch.setattr(
        rag_fixtures,
        "_never_stored",
        lambda path: "RevitSdkSamples" in path.split("/"),
    )
    world = make_world(tmp_path)
    assert ("ptt", "unittests/portal_credentials.py") in world.stored
    result = build(world)
    reasons = {(x["repo_key"], x["path"]): x["reason"] for x in result["manifest"]["excluded"]}
    assert reasons[("ptt", "unittests/portal_credentials.py")] == "credential_like"
    assert all("portal_credentials" not in row["file_key"] for row in result["chunks"])


def test_the_real_config_repositories_are_exactly_the_section_3_2_rows():
    """AR-1: the nine repository pins of the specification, no more and no fewer."""
    import re

    repo_root = Path(__file__).resolve().parents[1]
    spec = (repo_root / "docs/AEC-RAG-PACK.md").read_text(encoding="utf-8")
    rows = re.findall(
        r"^\| `(\w+)` \| ([\w.-]+/[\w.-]+) \| `([0-9a-f]{40})` \|.*\| `([^`|]+)` \|$",
        spec[spec.index("### 3.2 Admitted repositories") : spec.index("Version scope, written")],
        re.M,
    )
    config = json.loads((repo_root / "config/aec-course/rag-sources-v1.json").read_text())
    assert len(rows) == 9
    assert [
        (c["repo_key"], f"{c['owner']}/{c['repo']}", c["commit"], c["license_expression"])
        for c in config["repositories"]
    ] == rows


def test_decisions_that_rest_on_later_owner_decisions_point_at_that_entry(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    config = json.loads((repo_root / "config/aec-course/rag-sources-v1.json").read_text())
    log = (repo_root / "ITERATION_LOG.md").read_text(encoding="utf-8")
    pointed = {
        d["id"]: d["additional_record"] for d in config["decisions"] if "additional_record" in d
    }
    assert set(pointed) == {"S1", "S2", "C1"}  # OP-9 (S1, S2) and OP-2 (C1)
    for record in pointed.values():
        heading, _, section = record["entry"].partition(" (")
        assert f"### {heading}" in log and section.rstrip(")") in log

    def add(config):
        next(d for d in config["decisions"] if d["id"] == "C1")["additional_record"] = pointed["C1"]

    manifest = build(make_world(tmp_path, config_hook=add))["manifest"]
    decision = next(d for d in manifest["decisions"] if d["id"] == "C1")
    assert decision["additional_record"] == pointed["C1"] and decision["record"]["path"]


# ------------------------------------------------ guards that no test used to reach (AR-1 to AR-8)


def _tamper_stored(world, key, path, mutate):
    """Rewrite one stored tier-2 file and its receipt item; ``mutate(item, data)`` returns bytes."""
    stored = world.stored[(key, path)]
    receipt = json.loads((world.tier2 / "fetch-receipt.json").read_text())
    item = next(
        f
        for x in receipt["repositories"]
        if x["repo_key"] == key
        for f in x["files"]
        if f["path"] == path
    )
    data = mutate(item, stored.read_bytes())
    stored.write_bytes(data)
    (world.tier2 / "fetch-receipt.json").write_text(r.record_json(receipt))


def test_ar8_the_git_blob_id_is_recomputed_even_when_size_and_sha256_are_repaired(tmp_path):
    world = make_world(tmp_path)

    def repaired(item, data):
        data = data + b"# replaced\n"
        item.update(size=len(data), raw_sha256=r.sha256_hex(data))  # blob left at the pin
        return data

    _tamper_stored(world, "ospdoc", "src/wipe.rst", repaired)
    with pytest.raises(bc.BuildError, match="AR-8: stored bytes of ospdoc/src/wipe.rst"):
        build(world)


def test_ar8_a_stored_sha256_that_differs_from_the_receipt_is_refused(tmp_path):
    world = make_world(tmp_path)
    _tamper_stored(
        world, "ospdoc", "src/wipe.rst", lambda item, data: item.update(raw_sha256="0" * 64) or data
    )
    with pytest.raises(bc.BuildError, match="AR-8: stored bytes"):
        build(world)


@pytest.mark.parametrize("field", ["license_expression", "version_scope"])
def test_ar7_refuses_a_blank_license_expression_or_version_scope(tmp_path, field):
    def blank(config):
        repository(config, "ptt")[field] = " "

    refused(tmp_path, f"AR-7: ptt has no {field}", config_hook=blank)


def test_ar2_an_explicit_file_missing_from_the_fetch_is_refused(tmp_path):
    def drop(receipt):
        ospdoc = next(x for x in receipt["repositories"] if x["repo_key"] == "ospdoc")
        ospdoc["files"] = [f for f in ospdoc["files"] if f["path"] != "src/wipe.rst"]

    refused(tmp_path, "AR-2: ospdoc/src/wipe.rst is missing from the fetch", receipt_hook=drop)


def test_ar1_the_fetched_url_and_tag_must_be_the_admitted_ones(tmp_path):
    def url(receipt):
        receipt["repositories"][0]["url"] = "https://github.com/other/other.git"

    def tag(receipt):
        receipt["repositories"][0]["tag"] = "unadmitted-tag"

    refused(tmp_path / "u", "unadmitted URL", receipt_hook=url)
    refused(tmp_path / "t", "unadmitted ref", receipt_hook=tag)


def test_ar1_a_non_github_host_is_refused_even_when_it_is_not_deny_listed(tmp_path):
    def host(config):
        repository(config, "ptt")["url"] = "https://gitlab.com/Esri/public-transit-tools.git"

    refused(tmp_path, "must be the github.com repository", config_hook=host)


def test_ar6_an_extra_fetched_adn_page_is_refused(tmp_path):
    def extra(receipt):
        adn = next(x for x in receipt["repositories"] if x["repo_key"] == "adn2025")
        adn["files"].append(
            {
                "path": "html/2025/html/00000000-0000-0000-0000-00000000dead.htm",
                "mode": "100644",
                "blob": "e" * 40,
                "size": None,
                "raw_sha256": None,
                "stored": None,
            }
        )

    refused(tmp_path, "AR-6: .* is not an ADN-1 page", receipt_hook=extra)


def test_ar10_a_dll_path_is_denied_by_the_excluded_path_patterns():
    deny = json.loads(
        (Path(__file__).resolve().parents[1] / "config/aec-course/rag-sources-v1.json").read_text()
    )["deny_lists"]
    assert bc.denied_path("BuildingCoder/x/Bin.dll", deny) and bc.denied_path("a/b.chm", deny)
    assert not bc.denied_path("BuildingCoder/CmdBoundingBox.cs", deny)


def test_txt1_the_configured_notice_span_is_enforced(tmp_path):
    def wrong(config):
        spec = next(
            f for c in config["repositories"] for f in c["files"] if f.get("derived") == "pdf_text"
        )
        spec["notice_block_lines"] = [1, 2]

    refused(tmp_path, "TXT-1: cheat-sheet notice block", config_hook=wrong)


@pytest.mark.parametrize(
    "field, value, match",
    [
        ("line_count", 99, "expected 99"),
        ("contains", "a phrase the page lacks", "copies requirement"),
    ],
)
def test_the_regents_notice_pins_are_enforced(tmp_path, field, value, match):
    def wrong(config):
        repository(config, "ospdoc")["regents_notice"][field] = value

    world = make_world(tmp_path, config_hook=wrong)
    with pytest.raises(ValueError, match=match):
        build(world)


def test_a_source_verification_hash_that_differs_from_provenance_is_refused(tmp_path):
    def moved(verification):
        name = next(k for k in verification["upstream_files_sha256"] if k.startswith("upstream/"))
        verification["upstream_files_sha256"][name] = "0" * 64

    refused(tmp_path, "differs", verification_hook=moved)


def test_a_tier1_file_without_a_snapshot_mapping_is_refused(tmp_path):
    def promote(config):
        file_spec(config, "ospdoc", "src/wipe.rst")["tier"] = "T1"

    world = make_world(tmp_path, config_hook=promote)
    with pytest.raises(bc.BuildError, match="§3.7"):
        build(world)
