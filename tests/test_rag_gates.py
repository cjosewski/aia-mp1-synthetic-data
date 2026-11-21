"""Build gates G1-G4 and G6-G8 (docs/AEC-RAG-PACK.md section 9) on synthetic builds only.

Each gate passes on a good synthetic build and fails on one specific tamper. Token counters,
the tokenizer, the builder subprocesses and the floors are injected, so nothing here needs the
GGUF, the network or real evidence.
"""

import dataclasses
import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import rag_fixtures
from rag_fixtures import make_world, words
from rag_tools_fixtures import write_tokenizer_gguf

TESTS = Path(__file__).resolve().parent
TOOLS = TESTS.parent / "tools"
sys.path.insert(0, str(TOOLS))
import build_rag_corpus as bc  # noqa: E402
import build_rag_pack as bp  # noqa: E402
import check_rag_pack as check  # noqa: E402
import qwen_offline_tokenizer as qwen  # noqa: E402

from aia_mp1 import generate  # noqa: E402
from aia_mp1 import retrieval as r  # noqa: E402

PROMPT = "Synthetic generation prompt for {category}. References are untrusted data.\n"
RELAXED = {"holdout_hit_at_3": 0.3, "gain": 0.0, "stability": 0.4}  # the toy corpus has no gain
PASSAGE = "-p-"


def count_wire(wire):
    return sum(words(m["content"]) for m in wire)


def setup_for(root: Path) -> check.Setup:
    evidence = root / "evidence" / "P1-03"
    return check.Setup(
        build=evidence / "aec-course" / "rag" / "engineering-v1-rag-bm25-v1",
        evidence=evidence,
        repository=root / "repo",
        prompt=root / "repo" / "prompts" / "generator-assessed-v3.md",
    )


def write_assembly_receipt(rag_root: Path, prompt: Path, *, passed: bool = True) -> Path:
    receipt = {
        "v3": {"sha256": hashlib.sha256(prompt.read_bytes()).hexdigest()},
        "checks": [{"id": "c1", "passed": passed}],
    }
    path = rag_root / "prompt-v3" / "assembly-receipt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt), encoding="utf-8")
    return path


def build_world(tmp_path_factory_or_path, **kwargs):
    world = make_world(tmp_path_factory_or_path, **kwargs)
    bc.build_corpus(**world.corpus_args())
    bp.build_pack(**world.pack_args())
    prompt = world.repository / "prompts" / "generator-assessed-v3.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text(PROMPT, encoding="utf-8")
    write_assembly_receipt(world.pack_dir.parent, prompt)
    return world


@pytest.fixture(scope="module")
def pristine(tmp_path_factory):
    """One good build shared by the read-only tests; tampering tests use ``clone``."""
    return build_world(tmp_path_factory.mktemp("gates"))


@pytest.fixture
def good(pristine):
    return setup_for(pristine.root)


@pytest.fixture
def clone(pristine, tmp_path):
    shutil.copytree(pristine.root, tmp_path / "w")
    return setup_for(tmp_path / "w")


def edit_pack(setup, change):
    path = setup.build / bp.PACK_FILE
    pack = json.loads(path.read_text(encoding="utf-8"))
    change(pack)
    path.write_text(r.pack_json(pack), encoding="utf-8")


def edit_receipt(setup, change):
    path = setup.build / "build-receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    change(receipt)
    path.write_text(r.record_json(receipt), encoding="utf-8")


def write_leakage_scan(setup, status="pass", *, prompt_text=None):
    """A G5 result that names the pack, prompt and sidecar it scanned, by hash."""
    sidecar = setup.build.parent / "prompt-v3" / "guidance-provenance.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text('{"sentences": []}', encoding="utf-8")

    def entry(data):
        return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

    scan = {
        "status": status,
        "inputs": {
            "pack": entry((setup.build / bp.PACK_FILE).read_bytes()),
            "prompt_v3": entry(prompt_text.encode() if prompt_text else setup.prompt.read_bytes()),
            "guidance_provenance": entry(sidecar.read_bytes()),
        },
    }
    setup.gates.mkdir(exist_ok=True)
    (setup.gates / check.LEAKAGE_FILE).write_text(json.dumps(scan), encoding="utf-8")


def retitle(entry, text):
    entry["text"] = text
    entry["content_sha256"] = r.digest(text)


def flip(text):
    return text[:-1] + ("x" if text[-1] != "x" else "y")


def statuses(result):
    return {row["id"]: row["status"] for row in result["checks"]}


# ------------------------------------------------------------------ G1 provenance


def test_g1_passes_on_a_good_build_and_checks_every_item(good):
    result = check.g1_provenance(good, words)
    assert result["status"] == "pass", [x for x in result["checks"] if x["status"] != "pass"]
    assert [row["id"] for row in result["checks"]] == [f"G1.{n}" for n in range(10)]
    by_id = {row["id"]: row["detail"] for row in result["checks"]}
    assert by_id["G1.4"]["passages"] == by_id["G1.7"]["sources"] - 10 > 0
    assert by_id["G1.8"] == {"pairs": 50}
    assert by_id["G1.9"]["credential_read"] is False
    assert result["gate"] == "G1" and result["build"]["pack_digest"]
    assert {i["role"] for i in result["inputs"]} >= {"fetch_receipt", "tier1", "corpus_chunks"}


def test_g1_catches_an_edited_passage_even_when_its_hash_is_repaired(clone):
    def change(pack):
        entry = next(s for s in pack["sources"] if PASSAGE in s["id"])
        retitle(entry, flip(entry["text"]))

    edit_pack(clone, change)
    result = check.g1_provenance(clone, words)
    found = statuses(result)
    assert result["status"] == "fail"
    assert found["G1.4"] == found["G1.6"] == "fail"
    assert found["G1.7"] == "pass"  # the unchanged validator is satisfied; only the re-slice is not
    assert "pack text differs from the re-slice" in json.dumps(result["checks"][4])


def test_g1_catches_reordered_references(clone):
    def change(pack):
        task = next(t for t in pack["tasks"] if len(t["source_refs"]) >= 4)
        task["source_refs"][2], task["source_refs"][3] = (
            task["source_refs"][3],
            task["source_refs"][2],
        )

    edit_pack(clone, change)
    found = statuses(check.g1_provenance(clone, words))
    assert found["G1.6"] == found["G1.8"] == "fail"
    assert found["G1.4"] == found["G1.7"] == "pass"


def test_g1_catches_a_changed_stored_blob_and_a_changed_tier1_snapshot(clone):
    manifest = json.loads((clone.corpus / "corpus-manifest.json").read_text(encoding="utf-8"))
    record = next(f for f in manifest["files"] if f["tier"] == "T2" and "passage" in f["role"])
    stored = clone.corpus.parent / "tier2-v1" / "files" / record["repo_key"] / record["path"]
    stored.write_bytes(stored.read_bytes() + b"# edited\n")
    found = statuses(check.g1_provenance(clone, words))
    assert found["G1.1"] == found["G1.3"] == "fail"
    assert found["G1.7"] == "pass"


def test_g1_catches_a_changed_tier1_snapshot(clone):
    snapshot = next((clone.evidence / "references/preparation-20261110/upstream").iterdir())
    snapshot.write_bytes(snapshot.read_bytes() + b"x")
    found = statuses(check.g1_provenance(clone, words))
    assert found["G1.2"] == "fail"


def test_g1_catches_a_changed_removal_range(clone):
    def change(receipt):
        passage = next(p for p in receipt["passages"] if p["removed_within"])
        passage["removed_within"] = []

    edit_receipt(clone, change)
    result = check.g1_provenance(clone, words)
    assert statuses(result)["G1.4"] == "fail"


def test_g1_catches_a_tampered_environment_passage_and_the_token_cap(clone):
    def change(pack):
        entry = next(s for s in pack["sources"] if s["id"] == "sim-env-v1")
        retitle(entry, entry["text"] + "\nextra line")

    edit_pack(clone, change)
    found = statuses(check.g1_provenance(clone, words))
    assert found["G1.5"] == "fail" and found["G1.6"] == "fail"


def test_g1_environment_passage_above_600_tokens_fails(good):
    result = check.g1_provenance(good, lambda text: 601 if text.startswith("Environment") else 1)
    assert statuses(result)["G1.5"] == "fail"
    assert "above 600" in json.dumps(result["checks"][5])


def test_g1_is_incomplete_without_prompt_v3(good):
    result = check.g1_provenance(dataclasses.replace(good, prompt=None), words)
    assert result["status"] == "incomplete"
    assert statuses(result)["G1.9"] == "incomplete"
    assert [s for i, s in statuses(result).items() if i != "G1.9"] == ["pass"] * 9


def test_g1_refuses_a_missing_pack_as_an_input_error(good, tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(check.GateError, match="no pack"):
        check.g1_provenance(dataclasses.replace(good, build=tmp_path / "empty"), words)


# ------------------------------------------------------------------ G2 determinism

SEED_SCRIPT = textwrap.dedent(
    """
    import sys
    from pathlib import Path
    sys.path[:0] = [sys.argv[1], sys.argv[2]]
    import build_rag_corpus as bc
    import build_rag_pack as bp
    import rag_fixtures as f
    evidence, repository, config, tier2, step, output, corpus = sys.argv[3:10]
    if step == "corpus":
        bc.build_corpus(config=Path(config), tier2=Path(tier2), output=Path(output),
                        evidence=Path(evidence), repository=Path(repository),
                        count_tokens=f.words, tokenizer=dict(f.TOKENIZER))
    else:
        bp.build_pack(corpus=Path(corpus), output=Path(output), evidence=Path(evidence),
                      repository=Path(repository), count_tokens=f.words,
                      tokenizer=dict(f.TOKENIZER))
    """
)


def fixture_runner(setup, after=None):
    """Stands in for the real builder command: same builders, synthetic tokenizer."""
    env = {k: v for k, v in os.environ.items() if k != "AIA_MP1_DOMAIN"}

    def run(seed, step, output, corpus):
        subprocess.run(
            [
                sys.executable,
                "-c",
                SEED_SCRIPT,
                str(TESTS),
                str(TOOLS),
                str(setup.evidence),
                str(setup.repository),
                str(setup.repository / bc.CONFIG_PATH),
                str(setup.evidence / "aec-course/rag/tier2-v1"),
                step,
                str(output),
                str(corpus or ""),
            ],
            env={**env, "PYTHONHASHSEED": str(seed)},
            check=True,
            capture_output=True,
            text=True,
        )
        if after:
            after(seed, step, output)

    return run


def test_g2_passes_when_both_seeds_match_the_primary_build(clone):
    result = check.g2_determinism(clone, fixture_runner(clone))
    assert result["status"] == "pass", result["comparison"]
    assert set(result["comparison"]) == {"corpus", "pack"}
    for step in ("corpus", "pack"):
        assert result["comparison"][step]["identical_file_sets"]
        assert result["comparison"][step]["different"] == []
    pack_files = result["comparison"]["pack"]["files"]
    assert set(pack_files) == {bp.PACK_FILE, "build-receipt.json", "retrieval-report.json"}
    assert all(len(set(v.values())) == 1 for v in pack_files.values())
    seeds = [
        json.loads((clone.gates / f"determinism/seed{n}/{r.PACK_ID}/run.json").read_text())
        for n in (0, 1)
    ]
    assert [s["pythonhashseed"] for s in seeds] == ["0", "1"]  # fresh processes, run.json unread


def test_g2_fails_when_a_different_seeds_output_differs(clone):
    def after(seed, step, output):
        if seed == 1 and step == "pack":
            path = output / "retrieval-report.json"
            path.write_text(path.read_text().replace('"N": 3', '"N": 4', 1), encoding="utf-8")

    result = check.g2_determinism(clone, fixture_runner(clone, after))
    assert result["status"] == "fail"
    assert result["comparison"]["pack"]["different"] == ["retrieval-report.json"]
    assert result["comparison"]["corpus"]["different"] == []


def test_g2_fails_on_a_different_file_set_and_on_a_failed_builder(clone, tmp_path):
    def extra(seed, step, output):
        if seed == 0 and step == "corpus":
            (output / "stray.json").write_text("{}")

    result = check.g2_determinism(clone, fixture_runner(clone, extra))
    assert result["status"] == "fail"
    assert result["comparison"]["corpus"]["identical_file_sets"] is False

    def broken(seed, step, output, corpus):
        raise subprocess.CalledProcessError(2, ["build"], stderr="error: refused\n")

    shutil.rmtree(clone.gates)
    result = check.g2_determinism(clone, broken)
    assert result["status"] == "fail"
    assert result["builder_failures"][0]["error"] == "error: refused"


def test_g2_default_runner_runs_the_real_builders_with_the_hash_seed(clone, monkeypatch):
    calls = []
    monkeypatch.setattr(
        check.subprocess, "run", lambda argv, **kw: calls.append((argv, kw["env"])) or None
    )
    runner = check.BuilderRunner(
        dataclasses.replace(clone, gguf=Path("/x/model.gguf")), Path("/t2")
    )
    runner(1, "corpus", Path("/out/c"), None)
    runner(1, "pack", Path("/out/p"), Path("/out/c"))
    (corpus, env), (pack, _) = calls
    assert corpus[1].endswith("build_rag_corpus.py") and pack[1].endswith("build_rag_pack.py")
    assert corpus[corpus.index("--tier2") + 1] == "/t2"
    assert corpus[corpus.index("--config") + 1].endswith(bc.CONFIG_PATH)
    assert pack[pack.index("--corpus") + 1] == "/out/c"
    assert all(a[a.index("--gguf") + 1] == "/x/model.gguf" for a in (corpus, pack))
    assert env["PYTHONHASHSEED"] == "1"


def test_g2_refuses_an_existing_determinism_directory(clone):
    (clone.gates / "determinism").mkdir(parents=True)
    with pytest.raises(check.GateError, match="output exists"):
        check.g2_determinism(clone, fixture_runner(clone))


# ------------------------------------------------------------------ G3 tokenizer parity

MESSAGES = [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]


@pytest.fixture
def tiny(tmp_path):
    path = tmp_path / "tiny.gguf"
    file_sha, template_sha = write_tokenizer_gguf(path)
    return qwen.load_tokenizer(
        path, expected_sha256=file_sha, expected_template_sha256=template_sha
    )


def write_ledgers(evidence, tokenizer, wrong=()):
    true_count = qwen.prompt_tokens(tokenizer, MESSAGES)
    for index, relative in enumerate(qwen.PARITY_LEDGERS):
        ledger = evidence / relative
        ledger.parent.mkdir(parents=True)
        rows = []
        for line in range(50):
            recorded = true_count + (1 if (index, line) in wrong else 0)
            rows.append(
                json.dumps(
                    {
                        "input": MESSAGES,
                        "raw_response": {"usage": {"prompt_tokens": recorded}},
                        "output": "SECRET-ANSWER",
                    }
                )
            )
        ledger.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_g3_passes_when_all_450_counts_match_and_reports_counts_only(tmp_path, tiny):
    write_ledgers(tmp_path / "P1-03", tiny)
    result = check.g3_parity(tiny, tmp_path / "P1-03")
    assert (result["gate"], result["status"]) == ("G3", "pass")
    assert (result["attempts"], result["matched"]) == (450, 450)
    assert result["difference_distribution"] == {"0": 450}
    assert "SECRET-ANSWER" not in json.dumps(result)


def test_g3_fails_on_one_wrong_recorded_count(tmp_path, tiny):
    write_ledgers(tmp_path / "P1-03", tiny, wrong={(3, 7)})
    result = check.g3_parity(tiny, tmp_path / "P1-03")
    assert (result["status"], result["matched"]) == ("fail", 449)
    assert result["difference_distribution"] == {"-1": 1, "0": 449}


def test_g3_missing_ledgers_are_an_input_error(tmp_path, tiny):
    with pytest.raises(check.GateError, match="cannot run"):
        check.g3_parity(tiny, tmp_path / "absent")


# ------------------------------------------------------------------ G4 token preflight


def test_g4_renders_500_requests_from_100_distinct_wires(good):
    result = check.g4_preflight(good, count_wire)
    assert result["status"] == "pass"
    assert (result["captured_requests"], result["enumerated_requests"]) == (100, 500)
    assert result["distinct_wires"] == 100 and result["capture_mismatches"]["count"] == 0
    rows = result["rows"]
    assert len(rows) == 500 and set(rows[0]) == {
        "batch",
        "slot",
        "attempt",
        "task_id",
        "wire_sha256",
        "prompt_tokens",
    }
    assert [(x["batch"], x["slot"], x["attempt"]) for x in rows[:3]] == [
        (1, 0, 1),
        (1, 0, 2),
        (1, 1, 1),
    ]
    assert rows[0]["task_id"] == "gis_scripting-01" and rows[2]["task_id"] == "aec_automation-01"
    # a request is a pure function of slot, attempt, variant and pack: batches repeat each other
    assert {x["wire_sha256"] for x in rows if x["batch"] == 1} == {
        x["wire_sha256"] for x in rows if x["batch"] == 5
    }
    assert set(result["per_category"]) == set(r.CATEGORIES)
    assert result["maximum_prompt_tokens"] == max(x["prompt_tokens"] for x in rows)
    assert result["cap"] == 8192 and result["requests_over_cap"] == 0
    assert result["nfc_changed_pack_texts"] == 0 and result["nfc_changed_prompt"] is False


def test_g4_counts_with_the_injected_counter_on_the_captured_wire(good):
    seen = []
    result = check.g4_preflight(good, lambda wire: seen.append(wire) or 7)
    assert len(seen) == 100 and {x["prompt_tokens"] for x in result["rows"]} == {7}
    # Instructor's schema was appended to the system message, exactly as the client sends it
    assert '"equipment_problem"' in seen[0][0]["content"] and seen[0][1]["role"] == "user"


def test_g4_fails_when_one_request_breaches_the_cap(good):
    def counter(wire):
        return 8193 if "for slot 7." in wire[1]["content"] else count_wire(wire)

    result = check.g4_preflight(good, counter)
    assert result["status"] == "fail"
    assert result["requests_over_cap"] == 10  # slot 7, two attempts, five batches
    assert result["maximum_prompt_tokens"] == 8193
    exactly = check.g4_preflight(good, lambda wire: 8192)
    assert exactly["status"] == "pass"  # the cap itself is allowed


def test_g4_fails_when_the_capture_path_differs_from_the_independent_rebuild(good, monkeypatch):
    real = generate.generate_run

    def altered(config, prompt, sources, **kwargs):
        inner = kwargs["client"]

        class Altering:
            def generate(self, messages):
                messages[0]["content"] += " "
                return inner.generate(messages)

        return real(config, prompt, sources, **{**kwargs, "client": Altering()})

    monkeypatch.setattr(generate, "generate_run", altered)
    result = check.g4_preflight(good, count_wire)
    assert result["status"] == "fail"
    assert result["capture_mismatches"]["count"] == 100


def test_g4_is_incomplete_without_prompt_v3_and_reports_nfc_changes(clone):
    assert check.g4_preflight(dataclasses.replace(clone, prompt=None), count_wire)["status"] == (
        "incomplete"
    )

    def change(pack):
        entry = next(s for s in pack["sources"] if PASSAGE in s["id"])
        retitle(entry, entry["text"] + " café")

    edit_pack(clone, change)
    result = check.g4_preflight(clone, count_wire)
    assert result["nfc_changed_pack_texts"] == 1 and result["status"] == "pass"
    assert len(result["nfc_changed_pack_text_ids"]) == 1


# ------------------------------------------------------------------ G6 dry run


def test_g6_runs_the_final_pack_through_collect_cohort_and_assessment(good, tmp_path):
    result = check.g6_dry_run(good)
    assert result["status"] == "pass", [x for x in result["checks"] if x["status"] != "pass"]
    assert result["fake_client"] is True
    found = {row["id"]: row for row in result["checks"]}
    assert found["G6.1"]["detail"]["gate_status"] == "passed"  # the synthetic item passes the gate
    assert found["G6.1"]["detail"]["calls"] == 50 and found["G6.2"]["detail"]["records"] == 50
    assert found["G6.4"]["detail"]["available"] is True
    assert found["G6.5"]["detail"]["unchanged_inputs_reach_the_outcome_guard"].startswith(
        "unknown request outcome"
    )
    assert "refused" in found["G6.7"]["detail"] and found["G6.6"]["detail"]["calls"] == 0
    assert (
        result["hashes"]["pack_file_sha256"]
        == hashlib.sha256((good.build / bp.PACK_FILE).read_bytes()).hexdigest()
    )
    assert "discarded" in result["root"]


def test_g6_fails_on_a_pack_whose_hash_was_not_updated(clone):
    edit_pack(
        clone,
        lambda pack: pack["sources"][-1].update(text=flip(pack["sources"][-1]["text"])),
    )
    result = check.g6_dry_run(clone)
    assert result["status"] == "fail"
    assert [x["id"] for x in result["checks"]] == ["G6.0"]
    assert "reference content hash differs" in result["checks"][0]["detail"]["error"]


def test_g6_fails_when_collect_cannot_run_the_prompt(clone):
    clone.prompt.write_text("A prompt without the category placeholder.\n", encoding="utf-8")
    write_assembly_receipt(clone.build.parent, clone.prompt)
    result = check.g6_dry_run(clone)
    assert result["status"] == "fail" and statuses(result)["G6.1"] == "fail"


def test_g6_is_incomplete_without_prompt_v3_and_refuses_a_root_inside_the_repository(
    clone, tmp_path
):
    assert check.g6_dry_run(dataclasses.replace(clone, prompt=None))["status"] == "incomplete"
    with pytest.raises(check.GateError, match="worker failed"):
        check.g6_dry_run(clone, clone.repository / "dry")


# ------------------------------------------------------------------ G7 retrieval metrics


def test_g7_recomputes_every_value_and_matches_the_report(good):
    result = check.g7_metrics(good, RELAXED)
    assert result["status"] == "pass", result["problems"]
    assert result["report_values_match"] and result["report_mismatches"]["count"] == 0
    assert result["uneven_treatment"]["pass"] is True
    assert set(result["per_category"]) == set(r.CATEGORIES)
    assert result["tier_shares"]["T1"] + result["tier_shares"]["T2"] > 0
    assert "text" not in json.dumps(result["tasks"][0]).replace("passages", "")  # no chunk text
    assert result["floors"] == RELAXED


def test_g7_floors_are_the_specified_ones_and_the_toy_corpus_breaches_them(good):
    assert dict(r.METRIC_FLOORS) == {"holdout_hit_at_3": 0.60, "gain": 0.15, "stability": 0.50}
    result = check.g7_metrics(good)
    assert result["status"] == "fail" and result["report_values_match"]
    assert result["floors"] == dict(r.METRIC_FLOORS)
    assert "gis_scripting: gain 0.0 is below the floor 0.15" in result["problems"]
    assert result["floor_results"]["gis_scripting"] == {
        "holdout_hit_at_3": True,
        "gain": False,
        "stability": True,
    }
    # every category is judged separately: one failing category is enough
    report = json.loads((good.build / "retrieval-report.json").read_text(encoding="utf-8"))
    measured = {
        "per_category": report["metrics"]["per_category"],
        "uneven_treatment": {"empty_indexes": [], "categories_without_passages": []},
    }
    problems = check.judge_metrics(measured, dict(RELAXED, holdout_hit_at_3=0.9))
    assert [p.split(":")[0] for p in problems if "holdout_hit_at_3" in p] == [
        "structural_analysis",
        "cad_apis",
        "simulation",
    ]


def test_judge_metrics_reports_uneven_treatment_and_missing_values():
    category = {"holdout": {"hit_at_3": 0.8}, "gain": 0.4, "stability": 0.7}
    measured = {
        "per_category": {c: json.loads(json.dumps(category)) for c in r.CATEGORIES},
        "uneven_treatment": {
            "empty_indexes": ["cad_apis"],
            "categories_without_passages": ["simulation"],
            "pass": False,
        },
    }
    assert check.judge_metrics(measured, r.METRIC_FLOORS) == [
        "empty category indexes: ['cad_apis']",
        "categories without a retrieved passage: ['simulation']",
    ]
    measured["per_category"]["gis_scripting"]["gain"] = None
    measured["per_category"]["aec_automation"]["stability"] = 0.4999
    found = check.judge_metrics(measured, r.METRIC_FLOORS)
    assert "gis_scripting: gain None is below the floor 0.15" in found
    assert "aec_automation: stability 0.4999 is below the floor 0.5" in found


def test_g7_fails_when_the_report_differs_from_the_recomputed_values(clone):
    path = clone.build / "retrieval-report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["metrics"]["per_category"]["gis_scripting"]["gain"] = 0.9
    path.write_text(r.record_json(report), encoding="utf-8")
    result = check.g7_metrics(clone, RELAXED)
    assert result["status"] == "fail" and result["report_values_match"] is False
    assert result["report_mismatches"]["first"] == ["/per_category/gis_scripting/gain"]


def test_g7_uses_the_packs_selection_not_the_reports(clone):
    def change(pack):
        task = next(t for t in pack["tasks"] if len(t["source_refs"]) > 2)
        task["source_refs"].pop()

    edit_pack(clone, change)
    result = check.g7_metrics(clone, RELAXED)
    assert result["status"] == "fail" and not result["report_values_match"]


def test_g7_fails_on_uneven_treatment(tmp_path, monkeypatch):
    monkeypatch.setitem(rag_fixtures.BRIEFS, "simulation", "Zzqxv{n} wqplk{n}")
    world = build_world(tmp_path)
    result = check.g7_metrics(setup_for(world.root), RELAXED)
    assert result["report_values_match"] is True
    assert result["uneven_treatment"]["categories_without_passages"] == ["simulation"]
    assert result["status"] == "fail"
    assert any("without a retrieved passage" in p for p in result["problems"])


# ------------------------------------------------------------------ G8 baseline


def dry_baseline(setup, root):
    ran = check.g6_dry_run(setup, root)
    assert ran["status"] == "pass"
    return check.Baseline(root / "primary", check.DRY_COHORT, ran["hashes"]["cohort_sha256"])


@pytest.fixture(scope="module")
def synthetic_baseline(pristine, tmp_path_factory):
    root = tmp_path_factory.mktemp("baseline") / "dry"
    return dry_baseline(setup_for(pristine.root), root)


def real_repository(good):
    return dataclasses.replace(good, repository=check.REPO)


def test_the_pinned_module_hashes_are_the_ones_in_this_repository():
    for name, expected in check.PINNED_MODULES.items():
        assert hashlib.sha256((check.REPO / "src/aia_mp1" / name).read_bytes()).hexdigest() == (
            expected
        ), name
    assert len(check.PINNED_MODULES) == 12


def test_g8_passes_on_an_unchanged_baseline_without_printing_its_records(good, synthetic_baseline):
    result = check.g8_baseline(real_repository(good), synthetic_baseline)
    assert result["status"] == "pass", [x for x in result["checks"] if x["status"] != "pass"]
    assert [x["id"] for x in result["checks"]] == [
        "G8.1",
        "G8.2",
        "G8.3",
        "G8.3a",
        "G8.4",
        "G8.3b",
    ]
    assert result["checks"][2]["detail"] == {"members": 50}
    assert "question" not in json.dumps(result) and "answer" not in json.dumps(result)


def test_g8_fails_on_a_different_cohort_hash_or_rule_identity(good, synthetic_baseline):
    wrong = dataclasses.replace(synthetic_baseline, cohort_sha256="0" * 64)
    found = statuses(check.g8_baseline(real_repository(good), wrong))
    assert found["G8.2"] == "fail" and found["G8.1"] == found["G8.3"] == "pass"
    wrong = dataclasses.replace(synthetic_baseline, rule_identity="0" * 64)
    result = check.g8_baseline(real_repository(good), wrong)
    assert statuses(result)["G8.3a"] == "fail" and result["status"] == "fail"


def test_g8_fails_on_a_changed_pinned_file_or_prompt(good, synthetic_baseline, tmp_path):
    repository = tmp_path / "repo"
    (repository / "src/aia_mp1").mkdir(parents=True)
    (repository / "prompts").mkdir()
    for name in check.PINNED_MODULES:
        shutil.copyfile(check.REPO / "src/aia_mp1" / name, repository / "src/aia_mp1" / name)
    shutil.copyfile(check.REPO / check.PROMPT_V1, repository / check.PROMPT_V1)
    setup = dataclasses.replace(good, repository=repository)
    assert check.g8_baseline(setup, synthetic_baseline)["status"] == "pass"
    (repository / "src/aia_mp1/cli.py").write_bytes(
        (repository / "src/aia_mp1/cli.py").read_bytes() + b"\n"
    )
    result = check.g8_baseline(setup, synthetic_baseline)
    assert result["status"] == "fail" and statuses(result)["G8.4"] == "fail"
    assert result["checks"][4]["detail"]["modules"] == ["cli.py"]
    (repository / check.PROMPT_V1).write_text("changed", encoding="utf-8")
    assert statuses(check.g8_baseline(setup, synthetic_baseline))["G8.3b"] == "fail"


def test_g8_fails_when_a_recorded_event_is_edited(good, synthetic_baseline, tmp_path):
    root = tmp_path / "copy"
    shutil.copytree(synthetic_baseline.cohort_root, root / "primary")
    events = root / "primary" / f"{check.DRY_COLLECTION}-b01" / "events.jsonl"
    lines = events.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    source = first["reference_context"]["sources"][-1]
    source["text"] = flip(source["text"])
    lines[0] = json.dumps(first, ensure_ascii=False, allow_nan=False)
    events.write_text("\n".join(lines) + "\n", encoding="utf-8")
    edited = dataclasses.replace(synthetic_baseline, cohort_root=root / "primary")
    result = check.g8_baseline(real_repository(good), edited)
    found = statuses(result)
    assert found["G8.1"] == "fail"
    assert found["G8.2"] == found["G8.3"] == "fail"  # nothing is trusted after a failed load


# ------------------------------------------------------------------ all, gates.json, CLI


def parts_for(clone, tiny, baseline):
    return check.Parts(
        count_tokens=words,
        tokenizer=tiny,
        count_wire=count_wire,
        run_builder=fixture_runner(clone),
        floors=RELAXED,
        baseline=baseline,
    )


def synthetic_repository_pins(clone):
    """A stand-in for the pinned modules and prompt v1 inside the synthetic repository."""
    stub = clone.repository / "src/aia_mp1/generate.py"
    stub.parent.mkdir(parents=True)
    stub.write_text("# stand-in\n", encoding="utf-8")
    prompt = clone.repository / check.PROMPT_V1
    prompt.write_text("Synthetic prompt one.\n", encoding="utf-8")
    from aia_mp1.tracing import digest

    return {"generate.py": hashlib.sha256(stub.read_bytes()).hexdigest()}, digest(
        prompt.read_text(encoding="utf-8")
    )


def test_all_runs_every_gate_and_summarizes_them_in_gates_json(clone, tiny, tmp_path):
    write_ledgers(clone.evidence, tiny)
    ran = check.g6_dry_run(clone, tmp_path / "dry")
    modules, prompt_digest = synthetic_repository_pins(clone)
    baseline = check.Baseline(
        tmp_path / "dry" / "primary",
        check.DRY_COHORT,
        ran["hashes"]["cohort_sha256"],
        rule_identity=check.PINNED_MODULES["gate.py"],
        prompt_v1_digest=prompt_digest,
        modules=modules,
    )
    results = check.run_gates(
        clone, parts_for(clone, tiny, baseline), list(check.GATE_NAMES), summary=True
    )
    summary = json.loads((clone.gates / "gates.json").read_text(encoding="utf-8"))
    assert summary == results["summary"] and summary["all_passed"] is True
    assert list(summary["gates"]) == ["G1", "G2", "G3", "G4", "G6", "G7", "G8"]
    for gate, row in summary["gates"].items():
        written = (clone.gates / f"{check.GATE_NAMES[gate]}.json").read_bytes()
        assert row["status"] == "pass" and row["sha256"] == hashlib.sha256(written).hexdigest()
        assert json.loads(written)["gate"] == gate
    assert [p.name for p in sorted(clone.gates.glob("*.json"))] == sorted(
        [f"{n}.json" for n in check.GATE_NAMES.values()] + ["gates.json"]
    )
    # G5 belongs to scan_rag_leakage.py: reported when its file exists, never required here
    assert summary["leakage_scan"]["status"] == "not_run" and summary["all_passed_with_g5"] is False
    assert not (clone.gates / ".writer.lock").exists()
    before = (clone.gates / "gates.json").read_bytes()
    with pytest.raises(check.GateError, match="output exists"):
        check.run_gates(clone, parts_for(clone, tiny, baseline), ["G7"], summary=True)
    assert (clone.gates / "gates.json").read_bytes() == before


def test_one_failed_gate_makes_all_passed_false_and_the_other_gates_still_write(clone, tiny):
    write_ledgers(clone.evidence, tiny)
    parts = check.Parts(tokenizer=tiny, floors=None)  # the specified floors: the toy corpus fails
    clone.gates.mkdir()
    write_leakage_scan(clone)
    results = check.run_gates(clone, parts, ["G3", "G7"], summary=True)
    assert [results[g]["status"] for g in ("G3", "G7")] == ["pass", "fail"]
    assert results["summary"]["all_passed"] is False
    assert results["summary"]["leakage_scan"]["status"] == "pass"
    assert (clone.gates / "tokenizer-parity.json").is_file()


def run_cli(*args):
    return check.main([str(a) for a in args])


def test_cli_input_errors_print_error_and_exit_2(good, tmp_path, capsys):
    cases = [
        ("provenance", "--build", tmp_path / "absent", "--gguf", "x"),
        ("retrieval-metrics", "--build", tmp_path),  # no pack in the directory
        ("provenance", "--build", good.build, "--evidence", good.evidence),  # no --gguf
        ("g4", "--build", good.build, "--gguf", tmp_path / "absent.gguf", "--prompt", good.prompt),
        ("dry-run", "--build", good.build),  # no --prompt
        ("tokenizer-parity", "--build", good.build, "--gguf", tmp_path / "absent.gguf"),
    ]
    for case in cases:
        assert run_cli(*case) == 2, case
        err = capsys.readouterr().err
        assert err.startswith("error: ") and err.count("\n") == 1, (case, err)
    assert not (good.build / "gates").exists()


def test_cli_missing_required_arguments_exit_2(capsys):
    for argv in (["all", "--build", "x"], ["baseline"], []):
        with pytest.raises(SystemExit) as stop:
            check.main(argv)
        assert stop.value.code == 2
    assert "error:" in capsys.readouterr().err


def test_cli_failed_gate_exits_1_writes_once_and_refuses_a_rerun(clone, capsys):
    argv = [
        "g7",
        "--build",
        clone.build,
        "--evidence",
        clone.evidence,
        "--repository",
        clone.repository,
    ]
    assert run_cli(*argv) == 1  # the toy corpus breaches the specified floors
    assert capsys.readouterr().out == "G7 retrieval-metrics: fail\n"
    written = json.loads((clone.gates / "retrieval-metrics.json").read_text(encoding="utf-8"))
    assert written["status"] == "fail" and written["floors"] == dict(r.METRIC_FLOORS)
    first = (clone.gates / "retrieval-metrics.json").read_bytes()
    assert run_cli(*argv) == 2
    assert capsys.readouterr().err.startswith("error: output exists")
    assert (clone.gates / "retrieval-metrics.json").read_bytes() == first
    assert not (clone.gates / ".writer.lock").exists()


def test_cli_passing_gate_exits_0_and_incomplete_gate_exits_1(clone, tiny, monkeypatch, capsys):
    write_ledgers(clone.evidence, tiny)
    monkeypatch.setattr(qwen, "load_tokenizer", lambda *a, **k: tiny)
    common = [
        "--build",
        clone.build,
        "--evidence",
        clone.evidence,
        "--repository",
        clone.repository,
    ]
    assert run_cli("tokenizer-parity", *common, "--gguf", "model.gguf") == 0
    assert capsys.readouterr().out == "G3 tokenizer-parity: pass\n"
    missing = clone.repository / "prompts" / "absent.md"
    assert run_cli("token-preflight", *common, "--gguf", "model.gguf", "--prompt", missing) == 1
    written = json.loads((clone.gates / "token-preflight.json").read_text(encoding="utf-8"))
    assert written["status"] == "incomplete"


def test_a_worker_that_prints_no_json_is_an_input_error(good, monkeypatch):
    monkeypatch.setattr(check, "TOOL", TESTS / "rag_fixtures.py")  # runs, prints nothing
    with pytest.raises(check.GateError, match="dry-run worker failed"):
        check.run_in_domain("dry-run", {})


def test_a_worker_timeout_is_an_input_error_not_a_traceback(monkeypatch):
    monkeypatch.setattr(check, "WORKER_TIMEOUT", 0.001)
    with pytest.raises(check.GateError, match="dry-run worker timed out after 0.001 s"):
        check.run_in_domain("dry-run", {})


def test_a_g5_result_for_another_prompt_or_pack_is_stale_not_pass(clone):
    write_leakage_scan(clone, prompt_text="a different prompt revision\n")
    assert check.leakage_scan(clone)["status"] == "stale"
    write_leakage_scan(clone)
    assert check.leakage_scan(clone)["status"] == "pass"
    edit_pack(clone, lambda pack: pack.update(version=pack["version"] + "x"))
    assert check.leakage_scan(clone)["status"] == "stale"


def test_the_prompt_must_be_the_v3_that_passed_assembly(clone):
    assert check.assembly_problem(clone) is None
    clone.prompt.write_text(clone.prompt.read_text(encoding="utf-8") + "Edited.\n")
    assert check.assembly_problem(clone) == (
        "fail",
        "--prompt is not the v3 the assembly receipt names",
    )
    assert check.g4_preflight(clone, count_wire)["status"] == "fail"
    assert check.g6_dry_run(clone)["status"] == "fail"
    assert statuses(check.g1_provenance(clone, words))["G1.9"] == "fail"
    write_assembly_receipt(clone.build.parent, clone.prompt, passed=False)
    assert check.assembly_problem(clone)[0] == "fail"
    (clone.build.parent / "prompt-v3" / "assembly-receipt.json").unlink()
    assert check.assembly_problem(clone)[0] == "incomplete"
    assert check.g4_preflight(clone, count_wire)["status"] == "incomplete"
    assert statuses(check.g1_provenance(clone, words))["G1.9"] == "incomplete"


def test_a_gate_input_error_under_all_is_recorded_and_gates_json_is_still_written(
    clone, monkeypatch
):
    def broken(setup, parts):
        raise check.GateError("the dry-run worker failed: synthetic")

    monkeypatch.setitem(check.GATE_RUNNERS, "G6", broken)
    parts = check.Parts(floors=None)
    results = check.run_gates(clone, parts, ["G6", "G7"], summary=True)
    assert results["G6"]["status"] == "error"
    assert results["summary"]["all_passed"] is False
    assert (clone.gates / "gates.json").is_file() and (clone.gates / "dry-run.json").is_file()
    assert json.loads((clone.gates / "dry-run.json").read_text())["reason"].startswith(
        "the dry-run worker failed"
    )
    (clone.gates / "dry-run.json").unlink()
    with pytest.raises(check.GateError, match="worker failed"):  # a single gate still raises
        check.run_gates(clone, parts, ["G6"], summary=False)


def test_g1_0_fails_when_the_two_receipts_name_different_tokenizers(clone):
    edit_receipt(clone, lambda receipt: receipt.update(tokenizer={"synthetic": "other"}))
    result = check.g1_provenance(clone, words)
    assert statuses(result)["G1.0"] == "fail"


@pytest.mark.parametrize("field", ["raw_bytes", "raw_sha256", "blob"])
def test_g1_3_re_verifies_the_manifests_raw_provenance_against_the_fetch(clone, field):
    path = clone.corpus / "corpus-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    record = next(f for f in manifest["files"] if f["tier"] == "T2")
    record[field] = record[field] + 1 if field == "raw_bytes" else "0" * len(record[field])
    path.write_text(r.record_json(manifest), encoding="utf-8")
    result = check.g1_provenance(clone, words)
    assert statuses(result)["G1.3"] == "fail"
    assert "raw provenance differs" in json.dumps(result["checks"])


def test_g1_3_re_verifies_license_evidence_hashes(clone):
    path = clone.corpus / "corpus-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["repositories"][0]["license_files"][0]["evidence_sha256"] = "0" * 64
    path.write_text(r.record_json(manifest), encoding="utf-8")
    assert statuses(check.g1_provenance(clone, words))["G1.3"] == "fail"


def test_g2_fails_when_the_primary_build_differs_and_every_file_has_three_hashes(clone):
    report = clone.build / "retrieval-report.json"
    report.write_text(report.read_text().replace('"N": 3', '"N": 4', 1), encoding="utf-8")
    result = check.g2_determinism(clone, fixture_runner(clone))
    assert result["status"] == "fail"
    assert result["comparison"]["pack"]["different"] == ["retrieval-report.json"]
    for name, hashes in result["comparison"]["pack"]["files"].items():
        assert set(hashes) == {"primary", "seed0", "seed1"}, name


# ------------------------------------- each sub-check fails on its own tamper, by its own id


def failed_detail(result, check_id):
    row = next(x for x in result["checks"] if x["id"] == check_id)
    assert row["status"] == "fail", (check_id, row)
    return json.dumps(row)


def test_g1_4_names_a_passage_set_attribution_and_chunk_table_tamper_separately(clone):
    edit_receipt(clone, lambda rc: rc["passages"].pop())
    assert "receipt passages differ from the pack" in failed_detail(
        check.g1_provenance(clone, words), "G1.4"
    )


def test_g1_4_catches_an_attribution_only_edit(clone):
    def change(pack):
        entry = next(s for s in pack["sources"] if PASSAGE in s["id"])
        entry["attribution"] += " (edited)"

    edit_pack(clone, change)
    assert "entry fields differ from the templates" in failed_detail(
        check.g1_provenance(clone, words), "G1.4"
    )


def test_g1_4_catches_a_chunk_table_text_edit_with_its_hash_repaired(clone):
    path = clone.corpus / "chunks.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]
    receipt = json.loads((clone.build / "build-receipt.json").read_text(encoding="utf-8"))
    key = receipt["passages"][0]["chunk_key"]
    row = next(x for x in rows if x["chunk_key"] == key)
    row["text"] = flip(row["text"])
    row["content_sha256"] = r.digest(row["text"])
    path.write_text("".join(r.jsonl_line(x) + "\n" for x in rows), encoding="utf-8")
    assert "chunk table text differs from the re-slice" in failed_detail(
        check.g1_provenance(clone, words), "G1.4"
    )


def test_g1_0_names_each_receipt_and_chunk_row_disagreement(clone):
    edit_receipt(clone, lambda rc: rc["corpus"].update({"chunks.jsonl": "0" * 64}))
    assert "build receipt names a different chunks.jsonl" in failed_detail(
        check.g1_provenance(clone, words), "G1.0"
    )


def test_g1_0_catches_a_changed_report_through_the_receipt_outputs(clone):
    report = clone.build / "retrieval-report.json"
    report.write_text(report.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert "build receipt outputs differ from the files" in failed_detail(
        check.g1_provenance(clone, words), "G1.0"
    )


def test_g1_0_catches_edited_task_references_and_inconsistent_chunk_rows(clone):
    edit_receipt(clone, lambda rc: rc["tasks"][0].update(source_refs=["gis-p-000000000000"]))
    assert "task references differ from the pack" in failed_detail(
        check.g1_provenance(clone, words), "G1.0"
    )


def test_g1_0_catches_a_chunk_row_whose_hash_does_not_match_its_text(clone):
    path = clone.corpus / "chunks.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]
    rows[0]["text"] = flip(rows[0]["text"])
    path.write_text("".join(r.jsonl_line(x) + "\n" for x in rows), encoding="utf-8")
    assert "chunk rows are inconsistent" in failed_detail(check.g1_provenance(clone, words), "G1.0")


def test_g1_5_catches_edited_receipt_environment_rows(clone):
    edit_receipt(clone, lambda rc: rc["environment"][0].update(tokens=1))
    assert "receipt environment rows differ" in failed_detail(
        check.g1_provenance(clone, words), "G1.5"
    )


def test_g1_6_catches_static_entries_that_are_not_first(clone):
    def change(pack):
        pack["sources"].append(pack["sources"].pop(0))

    edit_pack(clone, change)
    assert "static entries are not the first five" in failed_detail(
        check.g1_provenance(clone, words), "G1.6"
    )


def test_g1_7_catches_a_source_count_the_receipt_does_not_expect(clone):
    edit_receipt(clone, lambda rc: rc["passages"].pop())
    assert statuses(check.g1_provenance(clone, words))["G1.7"] == "fail"


def test_g1_2_catches_tier1_results_that_differ_from_the_corpus_receipt(clone):
    path = clone.corpus / "corpus-receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["tier1_verification"]["6_cross_check"] = []
    path.write_text(r.record_json(receipt), encoding="utf-8")
    assert statuses(check.g1_provenance(clone, words))["G1.2"] == "fail"
