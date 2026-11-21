"""Offline Qwen3 tokenizer, chat-template render and Instructor wire capture (AEC-RAG-PACK §9 G3).

A port of the Qwen2 byte-level BPE that llama-server applies to the pinned GGUF. Only the GGUF
key-value header is parsed, never tensor data, and the whole file is hashed once per process
against the pin. A prompt count renders the locked Instructor JSON-mode request, captured through
``httpx.MockTransport``, with the GGUF chat template. No server or network is contacted.

``parity`` (gate G3) reads only ``input`` and ``raw_response.usage.prompt_tokens`` from the 450
recorded attempts and reports counts and hashes, never another field.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import struct
import sys
import unicodedata
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

import httpx
import jinja2
import regex

from aia_mp1.model_client import InstructorClient
from aia_mp1.tracing import digest

REPOSITORY = Path(__file__).resolve().parents[1]
EVID = REPOSITORY.parent / "artifacts" / "evidence" / "P1-03"
GGUF_PATH = Path("/home/chadjosewski/models/unsloth__Qwen3-30B-A3B-GGUF/Qwen3-30B-A3B-Q4_K_M.gguf")
GGUF_SHA256 = "9f1a24700a339b09c06009b729b5c809e0b64c213b8af5b711b3dbdfd0c5ba48"
CHAT_TEMPLATE_SHA256 = "5da44855ab7e0641774d5ed0ff0b4f89671d01df7d316e54d06557a962211cb4"
# The baseline's served model ID, with two leading backslashes. It does not change the messages.
SERVED_MODEL = "\\\\192.168.0.55\\AIA\\LLM_models\\Qwen3-30B-A3B-Q4_K_M.gguf"
PRETOKENIZER = regex.compile(
    r"(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+"
)
ATOMIC_TOKEN_TYPES = (3, 4)  # control and user-defined
PARITY_LEDGERS = tuple(
    f"aec-course/baseline-001-b0{n}/attempts.jsonl" for n in range(1, 5)
) + tuple(f"corrected-001-b0{n}/attempts.jsonl" for n in range(1, 6))
PARITY_EXPECTED = 450
PARITY_FIELDS = ["input", "raw_response.usage.prompt_tokens"]

_SCALARS = {
    0: "B",
    1: "b",
    2: "H",
    3: "h",
    4: "I",
    5: "i",
    6: "f",
    7: "?",
    10: "Q",
    11: "q",
    12: "d",
}
_STRING, _ARRAY = 8, 9
_UNMERGED = 1 << 62
_FILE_SHA256: dict[tuple, str] = {}


def _read(stream, size: int) -> bytes:
    data = stream.read(size)
    if len(data) != size:
        raise ValueError("truncated GGUF header")
    return data


def _string(stream) -> str:
    (size,) = struct.unpack("<Q", _read(stream, 8))
    return _read(stream, size).decode("utf-8")


def _value(stream, kind: int):
    if kind in _SCALARS:
        layout = "<" + _SCALARS[kind]
        return struct.unpack(layout, _read(stream, struct.calcsize(layout)))[0]
    if kind == _STRING:
        return _string(stream)
    if kind == _ARRAY:
        element, count = struct.unpack("<IQ", _read(stream, 12))
        if element in _SCALARS:
            layout = f"<{count}{_SCALARS[element]}"
            return list(struct.unpack(layout, _read(stream, struct.calcsize(layout))))
        if element not in (_STRING, _ARRAY):
            raise ValueError(f"unknown GGUF value type {element}")
        return [_value(stream, element) for _ in range(count)]
    raise ValueError(f"unknown GGUF value type {kind}")


def read_gguf_metadata(path) -> dict:
    """Parse the GGUF key-value header (types 0-12, arrays included); tensors are never read."""
    with Path(path).open("rb") as stream:
        if stream.read(4) != b"GGUF":
            raise ValueError("not a GGUF file")
        (version,) = struct.unpack("<I", _read(stream, 4))
        if version not in (2, 3):
            raise ValueError(f"unsupported GGUF version {version}")
        _tensors, count = struct.unpack("<QQ", _read(stream, 16))
        metadata = {}
        for _ in range(count):
            key = _string(stream)
            (kind,) = struct.unpack("<I", _read(stream, 4))
            if key in metadata:
                raise ValueError(f"duplicate GGUF key {key}")
            metadata[key] = _value(stream, kind)
    return metadata


def file_sha256(path: Path) -> str:
    """The sha256 of a whole file, once per process for each path, size, mtime and inode."""
    status = path.stat()
    key = (str(path.resolve()), status.st_size, status.st_mtime_ns, status.st_ino)
    if key not in _FILE_SHA256:
        with path.open("rb") as stream:
            _FILE_SHA256[key] = hashlib.file_digest(stream, "sha256").hexdigest()
    return _FILE_SHA256[key]


def _byte_symbols() -> list[str]:
    """GPT-2's byte-to-unicode map, indexed by byte value."""
    printable = {
        *range(ord("!"), ord("~") + 1),
        *range(ord("¡"), ord("¬") + 1),
        *range(ord("®"), ord("ÿ") + 1),
    }
    symbols, extra = [], 256
    for byte in range(256):
        if byte in printable:
            symbols.append(chr(byte))
        else:
            symbols.append(chr(extra))
            extra += 1
    return symbols


class QwenTokenizer:
    """Qwen2 byte-level BPE over a GGUF vocabulary, with the GGUF chat template."""

    def __init__(self, metadata: dict, gguf_sha256: str) -> None:
        if (metadata.get("tokenizer.ggml.model"), metadata.get("tokenizer.ggml.pre")) != (
            "gpt2",
            "qwen2",
        ):
            raise ValueError("GGUF tokenizer is not Qwen2 byte-level BPE")
        tokens = metadata["tokenizer.ggml.tokens"]
        token_type = metadata["tokenizer.ggml.token_type"]
        merges = metadata["tokenizer.ggml.merges"]
        if len(token_type) != len(tokens) or len(set(tokens)) != len(tokens):
            raise ValueError("GGUF vocabulary is inconsistent")
        self._ids = {token: index for index, token in enumerate(tokens)}
        self._ranks: dict[tuple[str, str], int] = {}
        for rank, merge in enumerate(merges):
            left, _, right = merge.partition(" ")
            if not left or not right:
                raise ValueError("malformed GGUF merge")
            self._ranks.setdefault((left, right), rank)
        atomic = sorted(
            (t for t, k in zip(tokens, token_type) if k in ATOMIC_TOKEN_TYPES),
            key=lambda t: (-len(t), t),
        )
        self._atomic = regex.compile("|".join(map(regex.escape, atomic))) if atomic else None
        self._symbols = _byte_symbols()
        self._pieces: dict[str, tuple[int, ...]] = {}
        self.chat_template: str = metadata["tokenizer.chat_template"]
        self._template = jinja2.Environment(trim_blocks=False, lstrip_blocks=False).from_string(
            self.chat_template
        )
        self.identity = {
            "gguf_sha256": gguf_sha256,
            "chat_template_sha256": hashlib.sha256(self.chat_template.encode("utf-8")).hexdigest(),
            "vocabulary_digest": digest(
                {"tokens": tokens, "token_type": token_type, "merges": merges}
            ),
        }

    def encode(self, text: str, *, parse_special: bool = False) -> list[int]:
        """Token IDs of raw text. Control and user-defined tokens are atomic only when parsed."""
        if not parse_special or self._atomic is None:
            return self._ordinary(text)
        ids, position = [], 0
        for match in self._atomic.finditer(text):
            ids += self._ordinary(text[position : match.start()])
            ids.append(self._ids[match.group()])
            position = match.end()
        return ids + self._ordinary(text[position:])

    def count_tokens(self, text: str, *, parse_special: bool = False) -> int:
        return len(self.encode(text, parse_special=parse_special))

    def render(self, messages: list[dict]) -> str:
        """The GGUF chat template applied to wire messages, with the generation prompt."""
        return self._template.render(messages=messages, add_generation_prompt=True, tools=None)

    def _ordinary(self, text: str) -> list[int]:
        ids: list[int] = []
        for piece in PRETOKENIZER.findall(unicodedata.normalize("NFC", text)):
            ids += self._piece(piece)
        return ids

    def _piece(self, piece: str) -> tuple[int, ...]:
        ids = self._pieces.get(piece)
        if ids is None:
            parts = [self._symbols[byte] for byte in piece.encode("utf-8")]
            while len(parts) > 1:
                # The lowest-ranked adjacent pair merges first; the leftmost wins a tie.
                rank, index = min(
                    (self._ranks.get(pair, _UNMERGED), i)
                    for i, pair in enumerate(zip(parts, parts[1:]))
                )
                if rank == _UNMERGED:
                    break
                parts[index : index + 2] = [parts[index] + parts[index + 1]]
            try:
                ids = tuple(self._ids[part] for part in parts)
            except KeyError:
                raise ValueError("BPE produced a symbol outside the GGUF vocabulary") from None
            self._pieces[piece] = ids
        return ids


def load_tokenizer(
    path=GGUF_PATH,
    *,
    expected_sha256: str = GGUF_SHA256,
    expected_template_sha256: str = CHAT_TEMPLATE_SHA256,
) -> QwenTokenizer:
    """Verify the whole GGUF and its chat template against the pins, then build the tokenizer."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"refusing symlinked GGUF {path}")
    actual = file_sha256(path)
    if actual != expected_sha256:
        raise ValueError(f"GGUF sha256 {actual} differs from the pin {expected_sha256}")
    tokenizer = QwenTokenizer(read_gguf_metadata(path), actual)
    if tokenizer.identity["chat_template_sha256"] != expected_template_sha256:
        raise ValueError("GGUF chat template sha256 differs from the pin")
    return tokenizer


@contextmanager
def _no_log_fallback(name: str):
    """Keep the expected capture-failure log off stderr; configured handlers still see it."""
    handler = logging.NullHandler()
    logging.getLogger(name).addHandler(handler)
    try:
        yield
    finally:
        logging.getLogger(name).removeHandler(handler)


def capture_request(messages: list[dict], *, model: str = SERVED_MODEL) -> dict:
    """The JSON body the locked Instructor JSON-mode client would send. The mock answers 400."""
    captured = []

    def capture(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(400, json={"error": {"message": "offline wire capture"}})

    with (
        _no_log_fallback("instructor"),
        InstructorClient(
            base_url="http://127.0.0.1:1/v1",
            model=model,
            api_key="offline-placeholder",
            mode="json",
            temperature=0.6,
            timeout_seconds=120,
            max_tokens=4096,
            _transport=httpx.MockTransport(capture),
        ) as client,
    ):
        client.generate(messages)
    if len(captured) != 1:
        raise ValueError("expected exactly one captured Instructor request")
    return captured[0]


def wire_messages(messages: list[dict], *, model: str = SERVED_MODEL) -> list[dict]:
    return capture_request(messages, model=model)["messages"]


def prompt_tokens(
    tokenizer: QwenTokenizer, messages: list[dict], *, model: str = SERVED_MODEL
) -> int:
    """The prompt tokens llama-server counts for a request: rendered wire, special tokens parsed."""
    return tokenizer.count_tokens(
        tokenizer.render(wire_messages(messages, model=model)), parse_special=True
    )


def _parity_fields(line: str, where: str) -> tuple[list, int]:
    """Only the two G3 fields of one attempt record; nothing else is kept or reported."""
    record = json.loads(line)
    response = record.get("raw_response")
    usage = response.get("usage") if isinstance(response, dict) else None
    recorded = usage.get("prompt_tokens") if isinstance(usage, dict) else None
    messages = record.get("input")
    if type(recorded) is not int or not isinstance(messages, list):
        raise ValueError(f"{where} lacks raw_response.usage.prompt_tokens or input")
    return messages, recorded


def parity(tokenizer: QwenTokenizer, evidence=EVID) -> dict:
    """Gate G3: recompute every recorded prompt count. The result holds counts and hashes only."""
    differences: Counter[int] = Counter()
    ledgers = []
    for relative in PARITY_LEDGERS:
        raw = (Path(evidence) / relative).read_bytes()
        attempts = matched = 0
        for number, line in enumerate(raw.decode("utf-8").split("\n"), 1):
            if line.strip():
                messages, recorded = _parity_fields(line, f"{relative} line {number}")
                difference = prompt_tokens(tokenizer, messages) - recorded
                differences[difference] += 1
                attempts += 1
                matched += difference == 0
        ledgers.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "attempts": attempts,
                "matched": matched,
            }
        )
    attempts = sum(ledger["attempts"] for ledger in ledgers)
    matched = sum(ledger["matched"] for ledger in ledgers)
    return {
        "gate": "G3",
        "status": "pass" if attempts == matched == PARITY_EXPECTED else "fail",
        "expected_attempts": PARITY_EXPECTED,
        "attempts": attempts,
        "matched": matched,
        "difference_distribution": {
            str(value): differences[value] for value in sorted(differences)
        },
        "fields_read": PARITY_FIELDS,
        "ledgers": ledgers,
        "tokenizer": tokenizer.identity,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline Qwen3 tokenizer port (AEC-RAG-PACK §9 G3)."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser(
        "parity", help="recompute the 450 recorded prompt counts; counts only"
    )
    check.add_argument("--gguf", type=Path, default=GGUF_PATH)
    check.add_argument("--evidence", type=Path, default=EVID)
    check.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError(f"output exists: {args.output}")
        if args.output.resolve().is_relative_to(REPOSITORY):
            raise ValueError("output must be outside the repository")
        result = parity(load_tokenizer(args.gguf), args.evidence)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(
                json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False, sort_keys=True)
                + "\n"
            )
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        f"tokenizer parity: matched {result['matched']} of {result['attempts']} recorded prompt counts ({result['status']})"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
