"""Pack builder (§6-§7): validation, static bytes, references, determinism, re-slicing, report."""

import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from rag_fixtures import TOKENIZER, make_world, output_files, words

from aia_mp1 import retrieval as r
from aia_mp1.sources import context_for, load_pack, validate_pack

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import build_rag_corpus as bc  # noqa: E402
import build_rag_pack as bp  # noqa: E402

PASSAGE_ID = re.compile(r"(gis|aec|str|cad|sim)-p-[0-9a-f]{12}")


def build_all(world, **pack_extra):
    bc.build_corpus(**world.corpus_args())
    return bp.build_pack(**world.pack_args(**pack_extra))


@pytest.fixture
def built(tmp_path):
    world = make_world(tmp_path)
    result = build_all(world)
    pack_path = world.pack_dir / bp.PACK_FILE
    return world, result, pack_path


def base_pack(world):
    return json.loads((world.evidence / "references/engineering-v1.json").read_text())


def test_pack_passes_the_unchanged_validator(built):
    world, result, pack_path = built
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    assert pack == result["pack"]
    assert validate_pack(pack) is pack
    assert load_pack(pack_path) == pack
    assert pack_path.read_text(encoding="utf-8") == r.pack_json(pack)
    retrieved = [s for s in pack["sources"] if PASSAGE_ID.fullmatch(s["id"])]
    assert len(pack["sources"]) == 10 + len(retrieved) and retrieved
    assert [k for k in pack] == [
        "schema_version",
        "pack_id",
        "version",
        "approved_by",
        "approved_at",
        "approval_basis",
        "permission_status",
        "sources",
        "tasks",
    ]
    assert pack["pack_id"] == "engineering-v1-rag-bm25-v1" and pack["approved_at"] == "2026-11-20"
    manifest_sha = r.sha256_hex((world.corpus / "corpus-manifest.json").read_bytes())
    assert f"Corpus manifest sha256 {manifest_sha}." in pack["approval_basis"]
    assert "\n" not in pack["approval_basis"]


def test_static_entries_are_byte_identical_and_tasks_change_only_refs(built):
    world, result, pack_path = built
    base_text = (world.evidence / "references/engineering-v1.json").read_text(encoding="utf-8")
    new_text = pack_path.read_text(encoding="utf-8")
    spans = r.static_source_spans(base_text)
    assert len(spans) == 5 and all(span in new_text for span in spans)
    assert r.static_source_spans(new_text)[:5] == spans
    base = base_pack(world)
    pack = result["pack"]
    assert pack["sources"][:5] == base["sources"]
    for old, new in zip(base["tasks"], pack["tasks"], strict=True):
        assert list(new) == ["id", "brief", "category", "source_refs"]
        assert {k: new[k] for k in ("id", "brief", "category")} == {
            k: old[k] for k in ("id", "brief", "category")
        }


def test_reference_order_is_static_environment_then_rank(built):
    world, result, _ = built
    pack = result["pack"]
    report = {t["task_id"]: t for t in result["report"]["tasks"]}
    base = {t["id"]: t for t in base_pack(world)["tasks"]}
    ids = [s["id"] for s in pack["sources"]]
    for task in pack["tasks"]:
        code = r.CATEGORY_CODES[task["category"]]
        refs = task["source_refs"]
        assert refs[0] == base[task["id"]]["source_refs"][0]
        assert refs[1] == f"{code}-env-v1"
        assert refs[2:] == report[task["id"]]["selected"]
        assert all(x.startswith(f"{code}-p-") for x in refs[2:])
        ranked = [
            c["chunk_key"]
            for c in report[task["id"]]["top_candidates"]
            if c["decision"] == "selected"
        ]
        assert len(ranked) == len(refs) - 2
    env = ids[5:10]
    assert env == [f"{r.CATEGORY_CODES[c]}-env-v1" for c in r.CATEGORIES]
    passages = {p["id"]: p for p in result["receipt"]["passages"]}
    files = {
        f["file_key"]: f
        for f in json.loads((world.corpus / "corpus-manifest.json").read_text())["files"]
    }
    order = {c: i for i, c in enumerate(r.CATEGORIES)}
    keys = [
        (
            order[files[passages[i]["file_key"]]["category"]],
            files[passages[i]["file_key"]]["file_index"],
            passages[i]["start"],
            passages[i]["end"],
        )
        for i in ids[10:]
    ]
    assert keys == sorted(keys)


def test_entries_have_twelve_fields_four_uses_local_only_and_ids(built):
    _, result, _ = built
    for entry in result["pack"]["sources"]:
        assert tuple(entry) == r.SOURCE_FIELDS
        assert entry["allowed_uses"] == list(r.ALLOWED_USES)
        assert entry["export_permission"] == "local_only"
        assert entry["content_sha256"] == r.digest(entry["text"])
        if PASSAGE_ID.fullmatch(entry["id"]):
            assert entry["id"].endswith(entry["content_sha256"][:12])
            assert entry["installation"].startswith(f"See {entry['id'][:3]}-env-v1 ")
    by_id = {s["id"]: s for s in result["pack"]["sources"]}
    receipt = {p["file_key"]: p for p in result["receipt"]["passages"]}
    page = next(p for k, p in receipt.items() if k.startswith("adn2025/"))
    page_entry = by_id[page["id"]]
    assert "#L" not in page_entry["url"]
    title = page_entry["text"].split("\n")[0]
    assert page_entry["version"].endswith(
        f"(text extraction) lines {page['start']}-{page['end']}; {title}"
    )
    code = next(p for k, p in receipt.items() if k.startswith("ptt/transit/"))
    assert by_id[code["id"]]["url"].endswith(f"route_tools.py#L{code['start']}-L{code['end']}")
    assert by_id[code["id"]]["attribution"].endswith(
        " File header: Copyright 2024 Synthetic Mapping Co. Licensed under the Apache License, "
        "Version 2.0"
    )
    assert by_id[code["id"]]["license_evidence"] == "aec-course/rag/tier2-v1/files/ptt/License.txt"


def test_passage_id_collision_stops_the_build(built):
    world, result, _ = built
    base = base_pack(world)
    environment = {
        c: next(s for s in result["pack"]["sources"] if s["id"] == f"{r.CATEGORY_CODES[c]}-env-v1")
        for c in r.CATEGORIES
    }
    first = r.passage_entry(
        category="cad_apis",
        text="Part::Box volume",
        owner="o",
        repo="x",
        commit="a" * 40,
        path="a.py",
        derived=False,
        start=1,
        end=1,
        version_scope="v",
        label=None,
        retrieved_at="t",
        license_expression="MIT",
        license_evidence="e",
        attribution="a",
    )
    second = dict(first, text="other text", content_sha256=r.digest("other text"))
    with pytest.raises(ValueError, match="collision"):
        r.assemble_pack(
            base, environment, [((3, 0, 1, 1), first), ((3, 1, 1, 1), second)], {}, "0" * 64
        )
    same = r.assemble_pack(
        base,
        environment,
        [((3, 0, 1, 1), first), ((3, 0, 1, 1), first)],
        {"cad_apis-01": [first["id"]]},
        "0" * 64,
    )
    assert [s["id"] for s in same["sources"]].count(first["id"]) == 1


def test_context_for_returns_every_reference_in_order(built):
    _, result, _ = built
    pack = result["pack"]
    by_id = {s["id"]: s for s in pack["sources"]}
    for category in r.CATEGORIES:
        tasks = [t for t in pack["tasks"] if t["category"] == category]
        for ordinal in range(10):
            context = context_for(pack, category, ordinal)
            assert context["pack_sha256"] == r.digest(pack)
            assert context["task"] == tasks[ordinal]
            assert context["sources"] == [by_id[x] for x in tasks[ordinal]["source_refs"]]


def test_environment_passages_text_attribution_and_fields(built):
    world, result, _ = built
    by_id = {s["id"]: s for s in result["pack"]["sources"]}
    sim = by_id["sim-env-v1"]
    commit = "7" * 40
    assert sim["text"] == (
        "Environment passage v1 for Synthetic SciPy 1.16.1. Each block below is verbatim from "
        "the named pinned file; nothing here was executed.\n"
        f"[synthetic-sci/sci@{commit[:12]} pyproject.toml lines 3-4]\n"
        'requires-python = ">=3.11"\n'
        'dependencies = ["numpy>=1.25.2,<2.6"]'
    )
    assert sim["url"] == f"https://github.com/synthetic-sci/sci/tree/{commit}"
    assert sim["version"] == "Synthetic SciPy 1.16.1; environment passage v1"
    assert (
        sim["installation"] == "This entry is the environment passage for Synthetic SciPy 1.16.1."
    )
    gis = by_id["gis-env-v1"]["text"].split("\n")
    assert gis[1].endswith("docs/arcgis-dist.json lines 2-5]")
    assert gis[6].endswith("docs/ArcPy-Cheatsheet.pdf (text extraction) lines 5-6]")
    assert by_id["gis-env-v1"]["attribution"].endswith(
        "Cheat sheet notice: Copyright © 2025 Synthetic Mapping Co. All rights reserved. Other "
        "marks belong to their respective mark owners."
    )
    regents = by_id["str-env-v1"]["attribution"]
    assert regents.startswith("Synthetic OpenSeesPy docs. Regents notice, verbatim:\nCopyright @")
    assert regents.endswith("SYNTHETIC CLOSING LINE TO BENEFIT THE END USER.")
    assert by_id["cad-env-v1"]["attribution"].endswith(
        " File header: (c) 2020 Synthetic Castillo <synthetic@example.invalid>"
    )
    assert by_id["aec-env-v1"]["retrieved_at"] == "2026-11-21T00:00:00+00:00"
    assert by_id["str-env-v1"]["retrieved_at"] == "2026-11-21T00:00:00+00:00"
    receipt = {e["id"]: e for e in result["receipt"]["environment"]}
    assert receipt["sim-env-v1"]["tokens"] == words(sim["text"])
    assert receipt["cad-env-v1"]["blocks"][1]["lines"] == [6, 8, 9]


def test_environment_lines_block_overlapping_chunks(built):
    _, result, _ = built
    for task in result["report"]["tasks"]:
        decisions = {c["chunk_key"]: c["decision"] for c in task["top_candidates"]}
        if task["task_id"].startswith("cad_apis"):
            key = "freecad102/src/Mod/Part/parttests/part_test_objects.py#L6-L18"
            assert decisions.get(key, "overlap") in ("overlap", "below_floor")
            assert key not in [
                c["chunk_key"] for c in task["top_candidates"] if c["decision"] == "selected"
            ]
    selected = {p["chunk_key"] for p in result["receipt"]["passages"]}
    assert "arcpy/docs/ArcPy-Cheatsheet.pdf!text#L1-L10" not in selected


def test_environment_passage_above_600_tokens_is_refused(tmp_path):
    world = make_world(tmp_path)
    bc.build_corpus(**world.corpus_args())

    def count(text):
        return 601 if text.startswith("Environment passage v1") else words(text)

    with pytest.raises(ValueError, match="above 600"):
        bp.build_pack(**world.pack_args(count_tokens=count))
    assert not (world.pack_dir / bp.PACK_FILE).exists()


def test_pack_builder_refuses_a_corpus_that_differs_from_its_receipt(tmp_path):
    world = make_world(tmp_path)
    bc.build_corpus(**world.corpus_args())
    chunks = world.corpus / "chunks.jsonl"
    chunks.write_text(chunks.read_text().replace("Toolbox", "Toolb0x"))
    with pytest.raises(bc.BuildError, match="differ from the corpus receipt"):
        bp.build_pack(**world.pack_args())


def test_two_builds_are_byte_identical(tmp_path):
    world = make_world(tmp_path)
    build_all(world)
    corpus_b, pack_b = tmp_path / "b" / "corpus", tmp_path / "b" / "pack"
    bc.build_corpus(**world.corpus_args(output=corpus_b))
    bp.build_pack(**world.pack_args(corpus=corpus_b, output=pack_b))
    assert output_files(corpus_b) == output_files(world.corpus)
    assert output_files(pack_b) == output_files(world.pack_dir)
    assert set(output_files(world.pack_dir)) == {
        bp.PACK_FILE,
        "build-receipt.json",
        "retrieval-report.json",
    }


SEED_SCRIPT = textwrap.dedent(
    """
    import sys
    from pathlib import Path
    sys.path[:0] = [sys.argv[1], sys.argv[2]]
    import build_rag_corpus as bc
    import build_rag_pack as bp
    import rag_fixtures as f
    evidence, repository, config, tier2, corpus, pack = map(Path, sys.argv[3:9])
    bc.build_corpus(config=config, tier2=tier2, output=corpus, evidence=evidence,
                    repository=repository, count_tokens=f.words, tokenizer=dict(f.TOKENIZER))
    bp.build_pack(corpus=corpus, output=pack, evidence=evidence, repository=repository,
                  count_tokens=f.words, tokenizer=dict(f.TOKENIZER))
    """
)


def test_hash_seed_0_and_1_builds_are_byte_identical(tmp_path):
    world = make_world(tmp_path)
    build_all(world)
    env = {k: v for k, v in os.environ.items() if k != "AIA_MP1_DOMAIN"}
    runs = {}
    for seed in (0, 1):
        corpus, pack = tmp_path / f"seed{seed}" / "corpus", tmp_path / f"seed{seed}" / "pack"
        subprocess.run(
            [
                sys.executable,
                "-c",
                SEED_SCRIPT,
                str(Path(__file__).parent),
                str(TOOLS),
                str(world.evidence),
                str(world.repository),
                str(world.config_path),
                str(world.tier2),
                str(corpus),
                str(pack),
            ],
            env={**env, "PYTHONHASHSEED": str(seed)},
            check=True,
            capture_output=True,
        )
        runs[seed] = (output_files(corpus), output_files(pack))
        assert json.loads((pack / "run.json").read_text())["pythonhashseed"] == str(seed)
    assert runs[0] == runs[1] == (output_files(world.corpus), output_files(world.pack_dir))


def test_reslice_detects_an_edit_a_changed_removal_and_a_changed_file(built):
    world, result, _ = built
    by_id = {s["id"]: s for s in result["pack"]["sources"]}
    manifest = json.loads((world.corpus / "corpus-manifest.json").read_text())
    files = {f["file_key"]: f for f in manifest["files"]}
    config = json.loads(world.config_path.read_text())

    def reader():
        verification = json.loads(
            (world.evidence / "aec-course/analysis/source-verification.json").read_text()
        )
        out = bc.InputReader(
            evidence=world.evidence, repository=world.repository, tier2=world.tier2
        )
        out.allow_upstream(
            k.split("/", 1)[1]
            for k in verification["upstream_files_sha256"]
            if k.startswith("upstream/")
        )
        return out

    for passage in result["receipt"]["passages"]:
        text = bp._file_text(reader(), config, files[passage["file_key"]])
        assert (
            r.reslice(text, passage["start"], passage["end"], passage["removed_within"])
            == (by_id[passage["id"]]["text"])
        )
    target = next(p for p in result["receipt"]["passages"] if p["removed_within"])
    record = files[target["file_key"]]
    text = bp._file_text(reader(), config, record)
    expected = by_id[target["id"]]["text"]
    edited = expected[:-1] + ("x" if expected[-1] != "x" else "y")
    assert r.reslice(text, target["start"], target["end"], target["removed_within"]) != edited
    assert r.reslice(text, target["start"], target["end"], []) != expected
    stored = world.tier2 / f"files/{record['repo_key']}/{record['path']}"
    stored.write_bytes(stored.read_bytes().replace(b"workspace", b"workspac3"))
    with pytest.raises(bc.BuildError, match="differs"):
        bp._file_text(reader(), config, record)
    tampered = r.n1(stored.read_bytes())
    assert r.reslice(tampered, target["start"], target["end"], target["removed_within"]) != (
        expected
    )


def test_report_and_receipt_hold_no_chunk_text(built):
    world, result, _ = built
    report = (world.pack_dir / "retrieval-report.json").read_text(encoding="utf-8")
    receipt = (world.pack_dir / "build-receipt.json").read_text(encoding="utf-8")
    rows = [json.loads(x) for x in (world.corpus / "chunks.jsonl").read_text().splitlines()]
    for row in rows:
        for line in row["text"].split("\n"):
            if len(line.strip()) >= 24:
                assert json.dumps(line.strip())[1:-1] not in report
                assert json.dumps(line.strip())[1:-1] not in receipt
    assert '"text"' not in report


def test_build_receipt_and_report_structure(built):
    world, result, pack_path = built
    receipt = json.loads((world.pack_dir / "build-receipt.json").read_text())
    assert receipt == result["receipt"]
    # The leakage scan (G5) matches its inputs to the pack through these three fields.
    assert receipt["corpus"] == {
        name: r.sha256_hex((world.corpus / name).read_bytes())
        for name in ("corpus-manifest.json", "chunks.jsonl", "corpus-receipt.json")
    }
    manifest = json.loads((world.corpus / "corpus-manifest.json").read_text())
    assert manifest["fetch_receipt"] == {
        "path": "aec-course/rag/tier2-v1/fetch-receipt.json",
        "sha256": r.sha256_hex((world.tier2 / "fetch-receipt.json").read_bytes()),
    }
    assert receipt["pack"]["file_sha256"] == r.sha256_hex(pack_path.read_bytes())
    assert receipt["pack"]["digest"] == r.digest(result["pack"])
    assert receipt["outputs"]["retrieval-report.json"] == r.sha256_hex(
        (world.pack_dir / "retrieval-report.json").read_bytes()
    )
    assert receipt["tokenizer"] == TOKENIZER
    assert receipt["constants"]["SELECT_MAX_TOKENS"] == 1600
    assert set(receipt["code"]) == {
        "src/aia_mp1/retrieval.py",
        "tools/build_rag_corpus.py",
        "tools/build_rag_pack.py",
        "tools/qwen_offline_tokenizer.py",
        "src/aia_mp1/sources.py",
    }
    assert all(r.input_path_problem(x["root"], x["path"]) is None for x in receipt["inputs"])
    assert {x["root"] for x in receipt["inputs"]} == {"corpus", "evidence", "repository", "tier2"}
    report = result["report"]
    assert set(report["categories"]) == set(r.CATEGORIES)
    task = report["tasks"][0]
    assert set(task) == {
        "task_id",
        "query_terms",
        "identifiers",
        "top_raw",
        "floor",
        "top_candidates",
        "selected",
        "selected_tokens",
        "prose_only",
        "leave_one_sentence_out",
    }
    assert task["query_terms"] == sorted(task["query_terms"])
    metrics = report["metrics"]
    assert set(metrics["per_category"]) == set(r.CATEGORIES)
    assert metrics["floors"] == {"holdout_hit_at_3": 0.6, "gain": 0.15, "stability": 0.5}
    assert metrics["uneven_treatment"]["pass"]
    assert not (world.pack_dir / ".writer.lock").exists()


def test_cli_failure_prints_an_error_and_exits_2(tmp_path, capsys):
    world = make_world(tmp_path)
    code = bp.main(
        [
            "--corpus",
            str(world.corpus),
            "--gguf",
            str(tmp_path / "missing.gguf"),
            "--output",
            str(world.pack_dir),
            "--evidence",
            str(world.evidence),
        ]
    )
    assert code == 2
    assert capsys.readouterr().err.startswith("error: ")
    assert not world.pack_dir.exists()


def test_refuses_a_corpus_counted_with_another_tokenizer(tmp_path):
    world = make_world(tmp_path)
    bc.build_corpus(**world.corpus_args())
    other = {**TOKENIZER, "synthetic": "another counter"}
    with pytest.raises(bp.BuildError, match="different tokenizer"):
        bp.build_pack(**world.pack_args(tokenizer=other))
    assert not (world.pack_dir / bp.PACK_FILE).exists()


def test_an_environment_block_must_come_from_an_environment_or_passage_file(tmp_path):
    def license_block(config):
        passage = config["environment_passages"][0]
        passage["blocks"][0]["file_key"] = "arcpy/LICENSE.txt"

    world = make_world(tmp_path, config_hook=license_block)
    bc.build_corpus(**world.corpus_args())
    with pytest.raises(bp.BuildError, match="neither an environment nor a passage file"):
        bp.build_pack(**world.pack_args())


def test_an_environment_passage_id_must_match_its_category(tmp_path):
    def mislabel(config):
        config["environment_passages"][0]["id"] = "aec-env-v1"

    world = make_world(tmp_path, config_hook=mislabel)
    bc.build_corpus(**world.corpus_args())
    with pytest.raises(bp.BuildError, match="does not match its category"):
        bp.build_pack(**world.pack_args())
