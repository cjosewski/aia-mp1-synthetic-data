import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
from rag_tools_fixtures import NOTE_FRAGMENT, REGENTS_NOTICE, leakage_layout

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import scan_rag_leakage as leakage  # noqa: E402

FRAGMENT = "the fixture answer omits the declared unit check entirely"  # nine tokens: two 8-grams
NOTE = f"synthetic reviewer note says {FRAGMENT}"
GUIDANCE = f"Plain guidance sentence. {FRAGMENT}."  # twelve tokens: five 8-grams


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_g5_tokens_and_ngrams_follow_the_spec():
    assert leakage.g5_tokens("Shape.Volume, OID@ 3.5 net8-Windows") == [
        "shape",
        "volume",
        "oid",
        "3",
        "5",
        "net8",
        "windows",
    ]
    assert list(leakage.ngram_strings("a b c d e f g")) == []
    assert list(leakage.ngram_strings("a b c d e f g h i")) == [
        "a b c d e f g h",
        "b c d e f g h i",
    ]


def test_planted_fragment_in_a_reviews_file_is_caught_and_counted_only(tmp_path):
    review = write(tmp_path / "evidence/P1-03/aec-course/assessments/x/reviews/note.md", NOTE)
    files = leakage.forbidden_files(tmp_path / "evidence", [])
    assert [(relative, leakage.forbidden_class(relative)) for relative, _ in files] == [
        ("P1-03/aec-course/assessments/x/reviews/note.md", "reviews")
    ]
    result = leakage.scan(
        {"guidance": [GUIDANCE]}, [], [("reviews", [review.read_text(encoding="utf-8")])]
    )
    assert result["hits"]["guidance"]["reviews"] == {"distinct_ngrams": 2, "entries_with_hit": 1}
    assert result["candidates"]["guidance"] == {
        "entries": 1,
        "ngrams": 5,
        "exempt": 0,
        "scanned": 5,
    }
    assert (
        sum(cell["distinct_ngrams"] for row in result["hits"].values() for cell in row.values())
        == 2
    )
    assert FRAGMENT.split()[1] not in json.dumps(result) and "note.md" not in json.dumps(result)


def test_the_same_fragment_in_an_allowed_upstream_text_is_exempt():
    upstream = f"Upstream licensed documentation: {FRAGMENT}, as published."
    result = leakage.scan({"guidance": [GUIDANCE]}, [upstream], [("reviews", [NOTE])])
    assert result["hits"]["guidance"]["reviews"] == {"distinct_ngrams": 0, "entries_with_hit": 0}
    assert result["candidates"]["guidance"]["exempt"] == 2


def test_json_contributes_string_values_only_and_ngrams_never_span_strings():
    raw = json.dumps(
        {
            "the fixture answer omits": "the declared unit check entirely",
            "x": ["the fixture", "answer omits"],
        }
    )
    texts, parsed = leakage.file_texts(raw.encode(), ".json")
    assert parsed and texts == ["the declared unit check entirely", "the fixture", "answer omits"]
    result = leakage.scan({"guidance": [GUIDANCE]}, [], [("other", texts)])
    assert result["hits"]["guidance"]["other"]["distinct_ngrams"] == 0
    lines = (json.dumps({"a": "one two"}) + "\n" + json.dumps(["three"]) + "\n").encode()
    assert leakage.file_texts(lines, ".jsonl") == (["one two", "three"], True)
    assert leakage.file_texts(b"{broken", ".json") == (["{broken"], False)


@pytest.mark.parametrize(
    "relative, expected",
    [
        ("P1-03/a/human-labels.jsonl", "labels"),
        ("P1-03/a/labels/reviews/x.md", "labels"),
        ("P1-03/a/human-review-reports/r.md", "reviews"),
        ("P1-03/a/human-adjudication-2/data.jsonl", "reviews"),
        ("P1-03/MY-ANSWERS-3.md", "reviews"),
        ("P1-03/run/attempts.jsonl", "answers"),
        ("P1-03/run/task-cards.json", "task_notes"),
        ("P1-03/aec-course/api-correctness-v2/out.json", "judge"),
        ("P1-03/aec-course/analysis/summary.json", "judge"),
        (".grounded-docs-trial/out.md", "judge"),
        (".rag-generator-design-20261120/understand-failures.md", "design"),
        (".rag-generator-design-20261120/proposals-judges.json", "judge"),
        ("P1-03/notes/README.md", "other"),
    ],
)
def test_forbidden_classes_take_the_first_matching_path_test(relative, expected):
    assert leakage.forbidden_class(relative) == expected


def test_allowlisted_inputs_references_and_the_rag_tree_are_never_scanned(tmp_path):
    evidence = tmp_path / "evidence"
    packet = "qualification/m4-recovery-contract-followup-20261117/packet-final/sources"
    for relative in [
        "P1-03/references/engineering-v1.json",
        "P1-03/aec-course/rag/corpus-v1/chunks.jsonl",
        "P1-03/aec-course/analysis/source-verification.json",
        f"P1-03/{packet}/ArcPy-Cheatsheet.txt",
        "elsewhere/tier2/fetch-receipt.json",
        "P1-03/aec-course/analysis/other.json",
        "P1-03/run/attempts.jsonl",
        "P1-03/run/blob.bin",
    ]:
        write(evidence / relative, "{}")
    (evidence / "P1-03/run/linked.md").symlink_to(evidence / "P1-03/run/attempts.jsonl")
    found = [
        relative
        for relative, _ in leakage.forbidden_files(evidence, [evidence / "elsewhere/tier2"])
    ]
    assert found == ["P1-03/aec-course/analysis/other.json", "P1-03/run/attempts.jsonl"]


def test_path_check_counts_forbidden_and_unlisted_inputs():
    receipts = {
        "fetch": {
            "inputs": [
                {"root": "repository", "path": "config/aec-course/rag-sources-v1.json"},
                {"root": "evidence", "path": "references/engineering-v1.json"},
            ]
        },
        "corpus": {
            "inputs": [
                {"root": "evidence", "path": "aec-course/assessments/x/data.jsonl"},
                {"root": "tier2", "path": "files/arcpy/LICENSE.txt"},
                {
                    "root": "evidence",
                    "path": "references/preparation-20261110/upstream/opensees-documentation-license.html",
                },
                {
                    "root": "tokenizer",
                    "path": "/home/chadjosewski/models/unsloth__Qwen3-30B-A3B-GGUF/Qwen3-30B-A3B-Q4_K_M.gguf",
                },
            ]
        },
        "build": {
            "inputs": [
                {"root": "corpus", "path": "corpus-manifest.json"},
                {"root": "evidence", "path": "qualification/other/notes.md"},
                {"root": "repository", "path": "prompts/generator-assessed-v3.md"},
                {"root": "repository", "path": "prompts/judge-v1.md"},
                {"path": "no-root.json"},
            ]
        },
    }
    assert leakage.path_check(receipts) == {
        "receipts": 3,
        "receipts_without_inputs": 0,
        "inputs": 11,
        "not_allowlisted": 2,
        "forbidden_pattern": 2,
    }
    assert leakage.path_check({"fetch": {}})["receipts_without_inputs"] == 1


def scan_layout(tmp_path, **options):
    layout = leakage_layout(tmp_path, **options)
    result = leakage.run(
        layout["build"], layout["prompt"], layout["evidence"], config=layout["config"]
    )
    written = (layout["build"] / "gates" / "leakage-scan.json").read_text(encoding="utf-8")
    assert json.loads(written) == result
    return layout, result, written


def test_run_catches_a_planted_note_fragment_and_writes_counts_only(tmp_path):
    layout, result, written = scan_layout(tmp_path, guidance_sentence=f"Never say {NOTE_FRAGMENT}.")
    assert result["status"] == "fail" and result["gate"] == "G5"
    # The guidance and the sidecar sentence that repeats it (config_free_text) both hit the note.
    for cclass in ("guidance", "config_free_text"):
        assert result["hits"][cclass]["reviews"] == {"distinct_ngrams": 2, "entries_with_hit": 1}
    hit = {("guidance", "reviews"), ("config_free_text", "reviews")}
    other = [
        cell for c, row in result["hits"].items() for f, cell in row.items() if (c, f) not in hit
    ]
    assert all(cell == {"distinct_ngrams": 0, "entries_with_hit": 0} for cell in other)
    assert (
        result["candidates"]["passage_text"]["exempt"]
        == result["candidates"]["passage_text"]["ngrams"]
        == 4
    )
    # config: decision scope, version scope, template, note; manifest: attribution, two
    # notices; sidecar: two sentences
    assert result["candidates"]["config_free_text"]["entries"] == 9
    assert result["forbidden"]["reviews"]["files"] == 1 and result["forbidden_files"] == 3
    for secret in (
        "omits",
        "declared",
        "note.md",
        "recommendation",
        "assessments",
        "Synthetic reviewer",
        "context.md",
        "quoting",
    ):
        assert secret not in written
    assert not (layout["build"] / "gates" / ".writer.lock").exists()


def test_run_exempts_the_same_fragment_when_an_allowed_upstream_file_holds_it(tmp_path):
    upstream = f"Upstream synthetic guide says {NOTE_FRAGMENT} in its own words.\n"
    _, result, _ = scan_layout(
        tmp_path, guidance_sentence=f"Never say {NOTE_FRAGMENT}.", upstream=upstream
    )
    assert result["hits"]["guidance"]["reviews"]["distinct_ngrams"] == 0
    assert result["candidates"]["guidance"]["exempt"] == 2 and result["status"] == "pass"


def test_run_fails_on_a_receipt_that_lists_an_assessment_ledger(tmp_path):
    inputs = [
        {"root": "tier2", "path": "files/up/docs/guide.md"},
        {"root": "evidence", "path": "aec-course/assessments/x/data.jsonl"},
    ]
    _, result, _ = scan_layout(
        tmp_path, guidance_sentence="Keep units explicit.", corpus_inputs=inputs
    )
    assert result["path_check"]["forbidden_pattern"] == 1 and result["status"] == "fail"
    assert (
        sum(cell["distinct_ngrams"] for row in result["hits"].values() for cell in row.values())
        == 0
    )


def test_run_refuses_an_existing_output_a_changed_corpus_text_and_a_prompt_without_the_clause(
    tmp_path, capsys
):
    layout, _, _ = scan_layout(tmp_path, guidance_sentence="Keep units explicit.")
    arguments = [
        "--build",
        str(layout["build"]),
        "--prompt",
        str(layout["prompt"]),
        "--evidence",
        str(layout["evidence"]),
    ]
    assert leakage.main(arguments) == 2 and "output exists" in capsys.readouterr().err
    changed = leakage_layout(tmp_path / "changed", guidance_sentence="Keep units explicit.")
    (changed["tier2"] / "files/up/docs/guide.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from the manifest"):
        leakage.run(
            changed["build"], changed["prompt"], changed["evidence"], config=changed["config"]
        )
    broken = leakage_layout(tmp_path / "broken", guidance_sentence="Keep units explicit.")
    broken["prompt"].write_text(
        broken["prompt"].read_text(encoding="utf-8").replace("Retrieved excerpts v3", "Excerpts"),
        encoding="utf-8",
    )
    receipt = broken["build"].parent / "prompt-v3" / "assembly-receipt.json"
    value = json.loads(receipt.read_text(encoding="utf-8"))
    value["v3"]["sha256"] = hashlib.sha256(broken["prompt"].read_bytes()).hexdigest()
    receipt.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="pinned retrieval clause"):
        leakage.run(broken["build"], broken["prompt"], broken["evidence"], config=broken["config"])


def test_run_refuses_a_corpus_or_tier2_the_pack_was_not_built_from(tmp_path):
    for name, target in (("manifest", "corpus"), ("fetch", "tier2")):
        layout = leakage_layout(tmp_path / name, guidance_sentence="Keep units explicit.")
        receipt = layout[target] / (
            "corpus-manifest.json" if name == "manifest" else "fetch-receipt.json"
        )
        receipt.write_text(receipt.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="not built from the scanned corpus"):
            leakage.run(
                layout["build"], layout["prompt"], layout["evidence"], config=layout["config"]
            )
        assert not (layout["build"] / "gates" / "leakage-scan.json").exists()


def test_license_notices_are_exempt_through_the_license_file_copies(tmp_path):
    _, kept, _ = scan_layout(tmp_path / "kept", guidance_sentence="Keep units explicit.")
    assert kept["hits"]["config_free_text"]["judge"]["distinct_ngrams"] == 0
    assert kept["status"] == "pass"
    _, dropped, written = scan_layout(
        tmp_path / "dropped", guidance_sentence="Keep units explicit.", license_in_manifest=False
    )
    # Without the license copy in the allowed set, the quoted notice's 8-grams are hits.
    notice_grams = len(leakage.g5_tokens(REGENTS_NOTICE)) - leakage.LEAKAGE_N + 1
    assert dropped["hits"]["config_free_text"]["judge"] == {
        "distinct_ngrams": notice_grams,
        "entries_with_hit": 1,
    }
    assert dropped["status"] == "fail" and "regents" not in written


# ------------------------------------------------------------ coverage of the forbidden walk


def test_suffix_matching_is_case_insensitive_and_symlinks_and_unreadable_dirs_are_reported(
    tmp_path,
):
    evidence = tmp_path / "evidence"
    for name in ("notes.md", "notes.MD", "answers.TXT", "page.HTM", "skip.bin"):
        write(evidence / "P1-03/aec-course/reviews" / name, "x")
    (evidence / "P1-03/aec-course/reviews/link.md").symlink_to(
        evidence / "P1-03/aec-course/reviews/notes.md"
    )
    (evidence / "P1-03/linked-dir").symlink_to(evidence / "P1-03/aec-course")
    skipped: list[str] = []
    found = [r for r, _ in leakage.forbidden_files(evidence, [], skipped)]
    assert [Path(r).name for r in found] == ["answers.TXT", "notes.MD", "notes.md", "page.HTM"]
    assert sorted(skipped) == ["P1-03/aec-course/reviews/link.md", "P1-03/linked-dir"]
    locked = evidence / "P1-03/locked"
    write(locked / "a.md", "x")
    locked.chmod(0)
    try:
        if not os.access(locked, os.R_OK):  # a user who ignores modes cannot make one
            with pytest.raises(OSError):
                leakage.forbidden_files(evidence, [])
    finally:
        locked.chmod(0o755)


def test_a_symlink_under_the_evidence_tree_fails_the_scan(tmp_path):
    layout = leakage_layout(tmp_path, guidance_sentence="Keep units explicit.")
    link = layout["evidence"] / "P1-03/aec-course/reviews-link.md"
    link.symlink_to(layout["note"])
    result = leakage.run(
        layout["build"], layout["prompt"], layout["evidence"], config=layout["config"]
    )
    assert result["status"] == "fail"
    assert result["skipped_symlinks"] == ["P1-03/aec-course/reviews-link.md"]


def test_one_truncated_jsonl_line_does_not_turn_the_whole_file_into_raw_text():
    good = json.dumps({"note": "first line of a review note about the fixture"})
    raw = (good + '\n{"note": "second line of the note that was interrupted').encode()
    texts, parsed = leakage.file_texts(raw, ".jsonl")
    assert parsed is False
    assert texts[0] == "first line of a review note about the fixture"
    assert texts[1].startswith('{"note": "second line')
    assert len(texts) == 2


def test_path_check_requires_upstream_names_to_be_named_in_source_verification():
    prefix = "references/preparation-20261110/"
    receipts = {
        "corpus": {
            "inputs": [
                {"root": "evidence", "path": prefix + "upstream/arcpy_license.txt"},
                {"root": "evidence", "path": prefix + "upstream/REVIEW-NOTES.md"},
            ]
        }
    }
    assert leakage.path_check(receipts)["not_allowlisted"] == 0
    counts = leakage.path_check(receipts, {"upstream/arcpy_license.txt"})
    assert counts["not_allowlisted"] == 1 and counts["forbidden_pattern"] == 0


# ------------------------------------------------------------------- pinned and locked inputs


def test_run_refuses_an_unpinned_rubric_and_a_config_the_corpus_was_not_built_from(tmp_path):
    layout = leakage_layout(tmp_path, guidance_sentence="Keep units explicit.")
    rubric = tmp_path / "rubric-edited.json"
    rubric.write_bytes((leakage.RUBRIC_V2).read_bytes() + b" ")
    with pytest.raises(ValueError, match="frozen pin"):
        leakage.run(
            layout["build"],
            layout["prompt"],
            layout["evidence"],
            config=layout["config"],
            rubric=rubric,
        )
    assert not (layout["build"] / "gates" / "leakage-scan.json").exists()
    layout["config"].write_bytes(layout["config"].read_bytes() + b" ")
    with pytest.raises(ValueError, match="not the one the corpus was built from"):
        leakage.run(layout["build"], layout["prompt"], layout["evidence"], config=layout["config"])
    assert not (layout["build"] / "gates" / ".writer.lock").exists()


def test_run_holds_the_lock_for_the_whole_scan(tmp_path):
    layout = leakage_layout(tmp_path, guidance_sentence="Keep units explicit.")
    gates = layout["build"] / "gates"
    gates.mkdir()
    (gates / ".writer.lock").write_text("held", encoding="utf-8")
    with pytest.raises(FileExistsError):
        leakage.run(layout["build"], layout["prompt"], layout["evidence"], config=layout["config"])
    assert (gates / ".writer.lock").read_text(encoding="utf-8") == "held"
    assert not (gates / "leakage-scan.json").exists()


def test_corpus_text_paths_are_checked_against_the_allowlist(tmp_path):
    layout = leakage_layout(tmp_path, guidance_sentence="Keep units explicit.")
    manifest_path = layout["corpus"] / "corpus-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["repositories"][0]["license_files"][0]["evidence_path"] = (
        "aec-course/assessments/x/reviews/note.md"
    )
    with pytest.raises(ValueError, match="not allowlisted"):
        list(
            leakage.corpus_texts(
                manifest,
                json.loads(layout["config"].read_text()),
                layout["tier2"],
                layout["evidence"] / "P1-03",
            )
        )


# --------------------------------------- every candidate class and allowed-set member counts


LONG = (
    "an unusual synthetic sentence about calibrating turbine blade tolerances "
    "against a reference gauge before every shift"
)


def test_run_scans_the_clause(tmp_path):
    from assemble_generator_v3 import CLAUSE

    layout = leakage_layout(tmp_path, guidance_sentence="Keep units explicit.")
    write(layout["evidence"] / ".rag-generator-design-20261120/clause-notes.md", CLAUSE)
    result = leakage.run(
        layout["build"], layout["prompt"], layout["evidence"], config=layout["config"]
    )
    assert result["hits"]["clause"]["design"]["distinct_ngrams"] > 0
    assert result["candidates"]["clause"]["entries"] == 1 and result["status"] == "fail"


@pytest.mark.parametrize("field", ["approval_basis", "installation"])
def test_run_scans_the_approval_basis_and_installation_text(tmp_path, field):
    layout = leakage_layout(tmp_path, guidance_sentence="Keep units explicit.")
    pack_path = layout["build"] / "engineering-v1-rag-bm25-v1.json"
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    if field == "approval_basis":
        pack[field] = LONG
    else:
        pack["sources"][0][field] = LONG
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    write(layout["evidence"] / ".rag-generator-design-20261120/planted.md", LONG)
    result = leakage.run(
        layout["build"], layout["prompt"], layout["evidence"], config=layout["config"]
    )
    assert result["hits"]["entry_free_text"]["design"]["distinct_ngrams"] > 0
    assert result["status"] == "fail"


def test_engineering_v1_rubric_v2_and_prompt_v1_strings_are_allowed(tmp_path):
    rubric = json.loads(leakage.RUBRIC_V2.read_text(encoding="utf-8"))
    rubric_sentence = rubric["instructor_approval"]
    v1_sentence = " ".join(leakage.PROMPT_V1.read_text(encoding="utf-8").split()[:20])
    layout = leakage_layout(
        tmp_path,
        guidance_sentence=f"{rubric_sentence} {v1_sentence}",
        engineering_brief=LONG,
        extra_passages=(LONG,),
    )
    for name, text in (("a", rubric_sentence), ("b", v1_sentence), ("c", LONG)):
        write(layout["evidence"] / f"P1-03/run/{name}/data.jsonl", json.dumps({"x": text}))
    result = leakage.run(
        layout["build"], layout["prompt"], layout["evidence"], config=layout["config"]
    )
    hits = sum(c["distinct_ngrams"] for row in result["hits"].values() for c in row.values())
    assert hits == 0 and result["status"] == "pass"
    assert result["candidates"]["passage_text"]["exempt"] > 4  # the extra passage is exempt


def test_run_refuses_a_prompt_that_is_not_the_assembled_v3(tmp_path):
    layout = leakage_layout(tmp_path, guidance_sentence="Keep units explicit.")
    layout["prompt"].write_text(
        layout["prompt"].read_text(encoding="utf-8") + "Added later.\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="assembly receipt names"):
        leakage.run(layout["build"], layout["prompt"], layout["evidence"], config=layout["config"])
    receipt = layout["build"].parent / "prompt-v3" / "assembly-receipt.json"
    receipt.unlink()
    with pytest.raises(ValueError, match="assembly receipt is missing"):
        leakage.run(layout["build"], layout["prompt"], layout["evidence"], config=layout["config"])
