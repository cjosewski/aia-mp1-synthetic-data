import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import assemble_generator_v3 as v3  # noqa: E402
import qwen_offline_tokenizer as qwen  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SENTENCES = [
    (
        "State where and how the code runs and the installed versions it assumes.",
        ["completeness"],
        ["where_and_how_to_run"],
    ),
    (
        "Name the prerequisites a reader needs before the first step.",
        ["completeness"],
        ["prerequisites"],
    ),
    ("Keep every given value from the task unchanged.", ["fidelity"], ["keep_brief_givens"]),
    (
        "Give one concrete check with its expected value, such as a count or a measured length.",
        ["verification"],
        ["one_concrete_check"],
    ),
    (
        "Name the specific data or model risk of the operation and the safeguard that prevents it.",
        ["safety"],
        ["specific_risk_and_safeguard"],
    ),
    (
        "Say when a qualified professional must review results that feed design decisions.",
        ["professional_boundary"],
        ["professional_review"],
    ),
    ("Use tips for insight that the steps do not already give.", ["tips"], ["tips_beyond_steps"]),
    ("Write in plain language and define any unavoidable term.", ["clarity"], ["plain_language"]),
]
BODY = (
    " ".join(s for s, _, _ in SENTENCES[:3])
    + "\n\n"
    + " ".join(s for s, _, _ in SENTENCES[3:])
    + "\n"
)
GUIDANCE = "## Answer guidance v3\n\n" + BODY
BRIEF = "Synthetic brief asks for a wall schedule that lists every level and its height in metres."


class WordCounter:
    identity = {"synthetic": "word counter"}

    @staticmethod
    def count_tokens(text, *, parse_special=False):
        return len(text.split())


def sidecar(guidance: bytes, sentences=SENTENCES, **changes) -> dict:
    value = {
        "schema_version": "guidance-provenance-v1",
        "guidance_sha256": hashlib.sha256(guidance).hexdigest(),
        "inputs": [
            {"path": path, "sha256": hashlib.sha256((REPO / path).read_bytes()).hexdigest()}
            for path in v3.SIDECAR_INPUTS
        ],
        "sentences": [
            {"text": text, "dimensions": dims, "topics": topics} for text, dims, topics in sentences
        ],
    }
    value.update(changes)
    return value


def lay_out(tmp_path, guidance=GUIDANCE, provenance=None):
    raw = guidance.encode("utf-8") if isinstance(guidance, str) else guidance
    paths = {
        "guidance": tmp_path / "prompts" / "generator-assessed-v3-guidance.md",
        "provenance": tmp_path / "rag" / "prompt-v3" / "guidance-provenance.json",
        "output": tmp_path / "prompts" / "generator-assessed-v3.md",
        "pack": tmp_path / "references" / "engineering-v1.json",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    paths["guidance"].write_bytes(raw)
    paths["provenance"].write_text(json.dumps(provenance or sidecar(raw)), encoding="utf-8")
    tasks = [
        {
            "id": f"gis_scripting-{n:02d}",
            "brief": BRIEF if n == 1 else f"Other synthetic brief {n}.",
            "category": "gis_scripting",
        }
        for n in range(1, 11)
    ]
    paths["pack"].write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
    return paths


def assemble(paths, **options):
    options = {
        "tokenizer": WordCounter(),
        "pack_sha256": hashlib.sha256(paths["pack"].read_bytes()).hexdigest(),
        **options,
    }
    return v3.assemble(
        paths["guidance"], paths["provenance"], paths["output"], pack=paths["pack"], **options
    )


def failed(paths, **options) -> set[str]:
    with pytest.raises(v3.AssemblyRefused) as refused:
        assemble(paths, **options)
    assert (
        not paths["output"].exists()
        and not (paths["provenance"].parent / "assembly-receipt.json").exists()
    )
    return {check["id"] for check in refused.value.failed}


def test_clause_constant_is_the_pinned_three_line_clause():
    raw = v3.CLAUSE.encode("ascii")
    assert (
        hashlib.sha256(raw).hexdigest()
        == "e904e0b346291ae98206f8ddc31895700571a6a8529c817201cf46cfd1773d28"
    )
    assert (
        len(raw) == 699
        and v3.CLAUSE.count("\n") == 3
        and v3.CLAUSE.startswith("## Retrieved excerpts v3\n\n")
    )


def test_v3_is_v1_then_the_clause_then_the_guidance_with_a_receipt(tmp_path):
    paths = lay_out(tmp_path)
    receipt = assemble(paths)
    v1 = (REPO / "prompts/generator-assessed-v1.md").read_bytes()
    assembled = paths["output"].read_bytes()
    assert assembled == v1 + b"\n" + v3.CLAUSE.encode() + b"\n" + GUIDANCE.encode()
    assert assembled.decode().count("{category}") == 1
    stored = json.loads(
        (paths["provenance"].parent / "assembly-receipt.json").read_text(encoding="utf-8")
    )
    assert stored == receipt
    assert receipt["v3"]["sha256"] == hashlib.sha256(assembled).hexdigest() and receipt["v3"][
        "bytes"
    ] == len(assembled)
    assert (
        receipt["v1"]["sha256"] == v3.V1_SHA256 and receipt["clause"]["sha256"] == v3.CLAUSE_SHA256
    )
    assert (
        receipt["guidance"]["qwen_tokens"] == len(GUIDANCE.split())
        and receipt["tokenizer"] == WordCounter.identity
    )
    assert all(check["passed"] for check in receipt["checks"]) and len(receipt["checks"]) == 18
    assert receipt["prompt_variant"] == "assessed-rag-bm25-v1"
    assert not (paths["provenance"].parent / ".writer.lock").exists()


@pytest.mark.parametrize(
    "guidance, expected",
    [
        ("﻿" + GUIDANCE, {"c1_encoding"}),
        (GUIDANCE.replace("\n", "\r\n"), {"c1_encoding"}),
        (GUIDANCE + "\n", {"c1_encoding"}),
        (GUIDANCE.rstrip("\n"), {"c1_encoding"}),
        (GUIDANCE.replace("## Answer guidance v3", "## Answer guidance"), {"c2_heading"}),
        (GUIDANCE.replace("v3\n\n", "v3\nText.\n"), {"c2_heading"}),  # line 2 is outside the body
        (GUIDANCE + "- A list item.\n", {"c4_plain_paragraphs", "s4_sentences"}),
        (GUIDANCE + "2. A numbered item.\n", {"c4_plain_paragraphs", "s4_sentences"}),
        (
            GUIDANCE.replace("unavoidable term.", "unavoidable term"),
            {"c4_plain_paragraphs", "s4_sentences"},
        ),
        (
            GUIDANCE.replace("the task unchanged", "the {task} unchanged"),
            {"c5_braces", "s4_sentences"},
        ),
        (
            GUIDANCE.replace("the task unchanged", "task gis_scripting-03 unchanged"),
            {"c6_task_ids", "c7_code_tokens", "s4_sentences"},
        ),
        (
            GUIDANCE.replace("the task unchanged", "the task_input unchanged"),
            {"c7_code_tokens", "s4_sentences"},
        ),
        (
            GUIDANCE.replace("such as a count", "e.g. a count, i.e. a tally, or Shape.Volume"),
            {"c7_code_tokens", "s4_sentences"},
        ),
        (
            GUIDANCE.replace("the code runs", "the revit code runs"),
            {"c8_product_names", "s4_sentences"},
        ),
        (
            GUIDANCE.replace("the code runs", "the C# code runs"),
            {"c8_product_names", "s4_sentences"},
        ),
        (
            GUIDANCE.replace(
                "Keep every", "Show a schedule that lists every level and its height. Keep every"
            ),
            {"c9_brief_ngrams", "s4_sentences"},
        ),
        (
            GUIDANCE.replace("before the first step", "in three steps"),
            {"c10_v1_consistency", "s4_sentences"},
        ),
        (
            GUIDANCE.replace("Keep every", "The code has been tested. Keep every"),
            {"c10_v1_consistency", "s4_sentences"},
        ),
        (
            GUIDANCE.replace("Keep every", "Add a summary field. Keep every"),
            {"c10_v1_consistency", "s4_sentences"},
        ),
    ],
)
def test_each_guidance_constraint_refuses(tmp_path, guidance, expected):
    paths = lay_out(tmp_path, guidance, provenance=sidecar(GUIDANCE.encode()))
    assert failed(paths) - {"s2_guidance_sha256"} == expected


def test_example_abbreviations_and_at_least_three_steps_are_allowed(tmp_path):
    allowed = GUIDANCE.replace("such as a count", "e.g. a count").replace(
        "before the first step", "for the at least three steps"
    )
    sentences = list(SENTENCES)
    sentences[1] = (
        "Name the prerequisites a reader needs for the at least three steps.",
        ["completeness"],
        ["prerequisites"],
    )
    sentences[3:4] = [  # the sidecar rule splits after "e.g."
        (
            "Give one concrete check with its expected value, e.g.",
            ["verification"],
            ["one_concrete_check"],
        ),
        ("a count or a measured length.", ["verification"], ["one_concrete_check"]),
    ]
    paths = lay_out(tmp_path, allowed, provenance=sidecar(allowed.encode(), sentences))
    assert all(check["passed"] for check in assemble(paths)["checks"])


def test_the_token_cap_counts_the_whole_guidance_file(tmp_path):
    paths = lay_out(tmp_path)
    assert assemble(paths)["guidance"]["qwen_tokens"] <= v3.GUIDANCE_MAX_TOKENS

    class Heavy(WordCounter):
        @staticmethod
        def count_tokens(text, *, parse_special=False):
            return 321 if text == GUIDANCE else 1

    assert failed(lay_out(tmp_path / "heavy"), tokenizer=Heavy()) == {"c3_token_cap"}


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda s: s.update(schema_version="guidance-provenance-v0"), {"s1_schema"}),
        (lambda s: s.update(guidance_sha256="0" * 64), {"s2_guidance_sha256"}),
        (lambda s: s["inputs"].pop(), {"s3_inputs"}),
        (lambda s: s["inputs"][0].update(sha256="0" * 64), {"s3_inputs"}),
        (lambda s: s["sentences"].pop(), {"s4_sentences", "s6_topic_coverage"}),
        (lambda s: s["sentences"][0].update(text="Different sentence."), {"s4_sentences"}),
        (lambda s: s["sentences"][0].update(dimensions=["accuracy"]), {"s5_labels"}),
        (lambda s: s["sentences"][0].update(topics=[]), {"s5_labels", "s6_topic_coverage"}),
        (lambda s: s["sentences"][7].update(topics=["prerequisites"]), {"s6_topic_coverage"}),
    ],
)
def test_each_sidecar_rule_refuses(tmp_path, mutate, expected):
    value = sidecar(GUIDANCE.encode())
    mutate(value)
    assert failed(lay_out(tmp_path, provenance=value)) == expected


def test_refuses_a_v1_hash_mismatch(tmp_path):
    changed = tmp_path / "v1.md"
    changed.write_bytes((REPO / "prompts/generator-assessed-v1.md").read_bytes() + b" ")
    assert failed(lay_out(tmp_path), v1=changed) == {"v1_sha256"}


def test_refuses_a_missing_guidance_file_or_sidecar_and_an_existing_output(tmp_path):
    paths = lay_out(tmp_path)
    paths["guidance"].unlink()
    with pytest.raises(v3.AssemblyRefused, match="guidance file is missing"):
        assemble(paths)
    paths = lay_out(tmp_path / "no-sidecar")
    paths["provenance"].unlink()
    with pytest.raises(v3.AssemblyRefused, match="sidecar is missing"):
        assemble(paths)
    paths = lay_out(tmp_path / "exists")
    paths["output"].write_text("existing\n", encoding="utf-8")
    with pytest.raises(v3.AssemblyRefused, match="exists"):
        assemble(paths)
    assert paths["output"].read_text(encoding="utf-8") == "existing\n"
    assert not (paths["provenance"].parent / "assembly-receipt.json").exists()


def test_cli_prints_an_error_and_exits_2_on_refusal(tmp_path, capsys):
    paths = lay_out(tmp_path)
    paths["guidance"].unlink()
    code = v3.main(
        [
            "--guidance",
            str(paths["guidance"]),
            "--provenance",
            str(paths["provenance"]),
            "--output",
            str(paths["output"]),
            "--pack",
            str(paths["pack"]),
        ]
    )
    assert code == 2 and capsys.readouterr().err.startswith("error: the guidance file is missing")
    assert not paths["output"].exists()


@pytest.mark.skipif(not qwen.GGUF_PATH.is_file(), reason="pinned GGUF absent")
def test_the_real_tokenizer_counts_the_clause_at_132_tokens():
    assert qwen.load_tokenizer().count_tokens(v3.CLAUSE) == 132


def test_sidecar_input_objects_may_list_their_keys_in_any_order(tmp_path):
    value = sidecar(GUIDANCE.encode())
    value["inputs"] = [{"sha256": x["sha256"], "path": x["path"]} for x in value["inputs"]]
    assert all(c["passed"] for c in assemble(lay_out(tmp_path, provenance=value))["checks"])
    value["inputs"][0]["extra"] = 1
    assert failed(lay_out(tmp_path / "extra", provenance=value)) == {"s3_inputs"}


def test_an_edited_rubric_with_a_matching_sidecar_is_refused(tmp_path, monkeypatch):
    copy = tmp_path / "copy"
    for path in v3.SIDECAR_INPUTS:
        (copy / path).parent.mkdir(parents=True, exist_ok=True)
        (copy / path).write_bytes((REPO / path).read_bytes())
    rubric = copy / v3.SIDECAR_INPUTS[0]
    rubric.write_bytes(rubric.read_bytes() + b" ")
    monkeypatch.setattr(v3, "REPOSITORY", copy)
    value = sidecar(GUIDANCE.encode())
    value["inputs"] = [
        {"path": p, "sha256": hashlib.sha256((copy / p).read_bytes()).hexdigest()}
        for p in v3.SIDECAR_INPUTS
    ]
    assert failed(lay_out(tmp_path / "run", provenance=value)) == {"s3_inputs"}


@pytest.mark.parametrize(
    "text",
    [
        "The code was tested on site, so readers do not need to check it.",
        "Add a 'warnings' field to the answer.",
        "The result is verified before use.",
        "The script has already been checked by a colleague.",
        "Give a dozen steps.",
        "Give exactly five steps.",
    ],
)
def test_c10_refuses_contradictions_of_v1(text):
    assert v3.consistency_problems([text])


@pytest.mark.parametrize(
    "text",
    [
        "Do not add extra fields.",
        "Give three or more steps.",
        "Give at least three steps.",
        "Split the work into one step per action.",
        "Do not claim the code was tested, and say so plainly.",
    ],
)
def test_c10_accepts_sentences_that_agree_with_v1(text):
    assert v3.consistency_problems([text]) == []


def test_exactly_the_token_cap_is_accepted(tmp_path):
    class AtCap(WordCounter):
        @staticmethod
        def count_tokens(text, *, parse_special=False):
            return v3.GUIDANCE_MAX_TOKENS if text == GUIDANCE else 1

    assert assemble(lay_out(tmp_path), tokenizer=AtCap())["guidance"]["qwen_tokens"] == 320


def test_an_indented_list_item_is_refused_like_an_unindented_one(tmp_path):
    changed = GUIDANCE + "  - An indented item.\n"
    paths = lay_out(tmp_path, changed, provenance=sidecar(changed.encode()))
    assert "c4_plain_paragraphs" in failed(paths)
