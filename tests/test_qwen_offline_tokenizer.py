import hashlib
import json
import struct
import sys
from pathlib import Path

import pytest
from rag_tools_fixtures import GGUF_ARRAY, GGUF_STRING, gguf_bytes, token_id, write_tokenizer_gguf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import qwen_offline_tokenizer as qwen  # noqa: E402

UNKNOWN_TYPE = (
    b"GGUF" + struct.pack("<IQQ", 3, 0, 1) + struct.pack("<Q", 3) + b"bad" + struct.pack("<I", 13)
)


def load(path, **options):
    file_sha, template_sha = write_tokenizer_gguf(path, **options)
    return qwen.load_tokenizer(
        path, expected_sha256=file_sha, expected_template_sha256=template_sha
    )


@pytest.fixture
def tokenizer(tmp_path):
    return load(tmp_path / "tiny.gguf")


def test_header_parse_reads_every_scalar_type_and_nested_arrays(tmp_path):
    entries = [
        ("u8", 0, 250),
        ("i8", 1, -7),
        ("u16", 2, 65000),
        ("i16", 3, -300),
        ("u32", 4, 4_000_000_000),
        ("i32", 5, -2_000_000_000),
        ("f32", 6, 0.5),
        ("bool", 7, True),
        ("text", 8, "Grüße"),
        ("u64", 10, 2**63 + 5),
        ("i64", 11, -(2**62)),
        ("f64", 12, 1.25),
        ("strings", GGUF_ARRAY, (GGUF_STRING, ["a", "", "ü"])),
        ("nested", GGUF_ARRAY, (GGUF_ARRAY, [(4, [1, 2]), (4, [])])),
    ]
    path = tmp_path / "all.gguf"
    path.write_bytes(gguf_bytes(entries))
    assert qwen.read_gguf_metadata(path) == {
        "u8": 250,
        "i8": -7,
        "u16": 65000,
        "i16": -300,
        "u32": 4_000_000_000,
        "i32": -2_000_000_000,
        "f32": 0.5,
        "bool": True,
        "text": "Grüße",
        "u64": 2**63 + 5,
        "i64": -(2**62),
        "f64": 1.25,
        "strings": ["a", "", "ü"],
        "nested": [[1, 2], []],
    }


@pytest.mark.parametrize(
    "raw, message",
    [
        (b"GGUX" + gguf_bytes([])[4:], "not a GGUF file"),
        (gguf_bytes([], version=1), "unsupported GGUF version"),
        (UNKNOWN_TYPE, "unknown GGUF value type 13"),
        (gguf_bytes([("k", 8, "value")], tail=b"")[:-2], "truncated GGUF header"),
        (gguf_bytes([("k", 8, "a"), ("k", 8, "b")]), "duplicate GGUF key"),
    ],
)
def test_header_parse_refuses_malformed_files(tmp_path, raw, message):
    path = tmp_path / "bad.gguf"
    path.write_bytes(raw)
    with pytest.raises(ValueError, match=message):
        qwen.read_gguf_metadata(path)


def test_load_refuses_wrong_hashes_symlinks_and_other_tokenizers(tmp_path):
    path = tmp_path / "tiny.gguf"
    file_sha, template_sha = write_tokenizer_gguf(path)
    with pytest.raises(ValueError, match="GGUF sha256"):
        qwen.load_tokenizer(path, expected_sha256="0" * 64, expected_template_sha256=template_sha)
    with pytest.raises(ValueError, match="chat template sha256"):
        qwen.load_tokenizer(path, expected_sha256=file_sha, expected_template_sha256="0" * 64)
    link = tmp_path / "link.gguf"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="symlink"):
        qwen.load_tokenizer(link, expected_sha256=file_sha, expected_template_sha256=template_sha)
    with pytest.raises(ValueError, match="Qwen2 byte-level BPE"):
        load(tmp_path / "other.gguf", pre="llama3")


def test_whole_file_is_hashed_once_per_process(tmp_path, monkeypatch):
    path = tmp_path / "tiny.gguf"
    file_sha, template_sha = write_tokenizer_gguf(path)
    calls = []
    original = hashlib.file_digest
    monkeypatch.setattr(
        hashlib, "file_digest", lambda *a, **k: calls.append(1) or original(*a, **k)
    )
    for _ in range(3):
        qwen.load_tokenizer(path, expected_sha256=file_sha, expected_template_sha256=template_sha)
    assert len(calls) == 1


def test_bpe_merges_by_lowest_rank_with_golden_ids(tokenizer):
    assert tokenizer.encode("hello world") == [token_id("hello"), token_id("Ġworld")]
    # Rank 9 "b c" beats rank 10 "a b", although "a b" is further left.
    assert tokenizer.encode("abc") == [ord("a"), token_id("bc")]
    # Digits are pre-tokenized one by one, so merge "2 0" never applies.
    assert tokenizer.encode("2020") == [ord("2"), ord("0"), ord("2"), ord("0")]
    # NFC turns e + combining acute into U+00E9: two UTF-8 bytes, not three.
    assert tokenizer.encode("é") == [0xC3, 0xA9]
    # "hello", then "Ġ" + "hello" (no merge joins them), then two newline bytes.
    assert tokenizer.count_tokens("hello hello\n\n") == 1 + 2 + 2


def test_special_tokens_are_atomic_longest_first_only_when_parsed(tokenizer):
    text = "<|im_start|>hello<think>!<think><plain>"
    assert tokenizer.encode(text, parse_special=True) == [
        token_id("<|im_start|>"),
        token_id("hello"),
        token_id("<think>!"),
        token_id("<think>"),
        *[ord(c) for c in "<plain>"],  # a normal (type 1) token is never matched atomically
    ]
    assert token_id("<|im_start|>") not in tokenizer.encode(text)
    assert tokenizer.count_tokens(text) == len(tokenizer.encode(text, parse_special=False)) > 30
    assert tokenizer.count_tokens("<|im_end|>", parse_special=True) == 1


def test_identity_names_the_file_template_and_vocabulary(tmp_path):
    path = tmp_path / "tiny.gguf"
    file_sha, template_sha = write_tokenizer_gguf(path)
    identity = qwen.load_tokenizer(
        path, expected_sha256=file_sha, expected_template_sha256=template_sha
    ).identity
    assert identity["gguf_sha256"] == file_sha and identity["chat_template_sha256"] == template_sha
    assert set(identity) == {"gguf_sha256", "chat_template_sha256", "vocabulary_digest"}
    changed = load(tmp_path / "fewer-merges.gguf", merges=["h e"]).identity
    assert changed["vocabulary_digest"] != identity["vocabulary_digest"]


def test_template_render_keeps_block_whitespace_and_passes_no_tools(tmp_path):
    template = (
        "{% if tools %}TOOLS{% endif %}{% for m in messages %}[{{ m.role }}]\n{{ m.content }}\n{% endfor %}"
        "  {% if add_generation_prompt %}\n<gen>{% endif %}"
    )
    tok = load(tmp_path / "t.gguf", template=template)
    rendered = tok.render([{"role": "system", "content": "S"}, {"role": "user", "content": "U"}])
    # trim_blocks=False keeps the newline after a block tag; lstrip_blocks=False keeps the indent.
    assert rendered == "[system]\nS\n[user]\nU\n  \n<gen>"
    assert tok.chat_template == template


def test_wire_capture_appends_the_schema_to_the_system_message():
    messages = [
        {"role": "system", "content": "Synthetic system."},
        {"role": "user", "content": "Synthetic user."},
    ]
    body = qwen.capture_request(messages)
    wire = qwen.wire_messages(messages)
    assert body["messages"] == wire
    assert [m["role"] for m in wire] == ["system", "user"]
    assert (
        wire[0]["content"].startswith("Synthetic system.")
        and '"equipment_problem"' in wire[0]["content"]
    )
    assert wire[1] == messages[1]
    assert (body["temperature"], body["max_tokens"], body["model"]) == (
        0.6,
        4096,
        qwen.SERVED_MODEL,
    )


def test_prompt_tokens_count_the_rendered_wire_with_special_tokens(tmp_path):
    tok = load(tmp_path / "bytes.gguf", merges=[])
    messages = [
        {"role": "system", "content": "Sys é."},
        {"role": "user", "content": "Ask <think> 42."},
    ]
    wire = qwen.wire_messages(messages)
    assert tok.render(wire) == "".join(
        f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in wire
    ) + ("<|im_start|>assistant\n")
    # Without merges every UTF-8 byte is one token; each ChatML marker and the user's
    # "<think>" (a user-defined token) is one atomic token.
    text_bytes = sum(len(f"{m['role']}\n{m['content']}\n".encode()) for m in wire) + len(
        b"assistant\n"
    )
    atomic = 2 * len(wire) + 1 + 1
    assert qwen.prompt_tokens(tok, messages) == text_bytes - len(b"<think>") + atomic


def test_parity_reports_counts_only_and_cli_refuses_existing_output(
    tmp_path, tokenizer, monkeypatch, capsys
):
    evidence = tmp_path / "P1-03"
    messages = [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]
    true_count = qwen.prompt_tokens(tokenizer, messages)
    for index, relative in enumerate(qwen.PARITY_LEDGERS):
        ledger = evidence / relative
        ledger.parent.mkdir(parents=True)
        recorded = true_count + (1 if index == 0 else 0)
        row = {
            "input": messages,
            "raw_response": {"usage": {"prompt_tokens": recorded}},
            "output": "SECRET-ANSWER",
        }
        ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")
    result = qwen.parity(tokenizer, evidence)
    assert (result["status"], result["attempts"], result["matched"]) == ("fail", 9, 8)
    assert result["difference_distribution"] == {"-1": 1, "0": 8}
    assert "SECRET-ANSWER" not in json.dumps(result)
    monkeypatch.setattr(qwen, "load_tokenizer", lambda *a, **k: tokenizer)
    output = tmp_path / "parity.json"
    assert (
        qwen.main(["parity", "--evidence", str(evidence), "--output", str(output)]) == 1
    )  # written, failed
    assert json.loads(output.read_text(encoding="utf-8")) == result
    assert "8 of 9" in capsys.readouterr().out
    assert qwen.main(["parity", "--evidence", str(evidence), "--output", str(output)]) == 2
    assert capsys.readouterr().err.startswith("error: ")
    assert json.loads(output.read_text(encoding="utf-8")) == result


def test_parity_refuses_a_record_without_recorded_usage(tmp_path, tokenizer):
    evidence = tmp_path / "P1-03"
    for relative in qwen.PARITY_LEDGERS:
        (evidence / relative).parent.mkdir(parents=True)
        (evidence / relative).write_text(
            json.dumps({"input": [], "raw_response": None}) + "\n", encoding="utf-8"
        )
    with pytest.raises(ValueError, match="lacks raw_response.usage.prompt_tokens"):
        qwen.parity(tokenizer, evidence)


REAL_LEDGERS = [qwen.EVID / relative for relative in qwen.PARITY_LEDGERS]


@pytest.mark.skipif(
    not qwen.GGUF_PATH.is_file() or not all(path.is_file() for path in REAL_LEDGERS),
    reason="pinned GGUF or recorded baseline ledgers absent",
)
def test_real_parity_reproduces_all_450_recorded_prompt_counts():
    result = qwen.parity(qwen.load_tokenizer(), qwen.EVID)
    assert (result["attempts"], result["matched"], result["status"]) == (450, 450, "pass")
