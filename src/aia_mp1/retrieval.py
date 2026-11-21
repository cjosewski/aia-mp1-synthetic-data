"""Deterministic BM25 retrieval over pinned, licensed passages (docs/AEC-RAG-PACK.md).

Pure functions: N1 normalization and the derived-text extractors, the live-code rule,
segments and windows, BM25 terms and Okapi BM25, brief identifiers and the bonus,
selection, environment passages, entry and pack assembly, re-slicing and the G7
retrieval metrics. Token counts arrive as an injected ``count_tokens(text) -> int``.
The only I/O is ``write_new``, an exclusive-create writer. Standard library only.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import html.parser
import io
import json
import math
import re
import textwrap
import tokenize
import warnings
import xml.parsers.expat
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from .tracing import digest

# ------------------------------------------------------------------ §2 constants

PACK_ID = "engineering-v1-rag-bm25-v1"
PROMPT_VARIANT = "assessed-rag-bm25-v1"
CATEGORIES = ("gis_scripting", "aec_automation", "structural_analysis", "cad_apis", "simulation")
CATEGORY_CODES = {
    "gis_scripting": "gis",
    "aec_automation": "aec",
    "structural_analysis": "str",
    "cad_apis": "cad",
    "simulation": "sim",
}
NORMALIZATION = "n1"
CHUNK_MAX_LINES = 30
CHUNK_STRIDE_LINES = 15
CHUNK_MAX_TOKENS = 480
MIN_TERM_LENGTH = 2
BM25_K1 = 1.2
BM25_B = 0.75
IDENT_BONUS_FRACTION = 0.5
IDENT_BONUS_MAX_MATCHES = 2
SCORE_FLOOR_FRACTION = 0.2
SELECT_MAX_PASSAGES = 4
SELECT_MAX_TOKENS = 1600
SCORE_DECIMALS = 9
ENV_MAX_TOKENS = 600
ADN_MAX_PAGES = 60
PROMPT_TOKEN_CAP = 8192
PREFLIGHT_ENUMERATION = {"batches": 5, "slots": 50, "attempts": 2}
GUIDANCE_MAX_TOKENS = 320
LEAKAGE_N = 8
METRIC_FLOORS = {"holdout_hit_at_3": 0.60, "gain": 0.15, "stability": 0.50}
STABILITY_LIST_BELOW = 0.34
CLAUSE_SHA256 = "e904e0b346291ae98206f8ddc31895700571a6a8529c817201cf46cfd1773d28"
CLAUSE_BYTES = 699
ALLOWED_USES = ("assessed_generation", "human_review", "judge_context", "local_evidence")
EXPORT_PERMISSION = "local_only"
GAIN_SHUFFLE_SALT = "rag-gain-shuffle-v1:"
STOPWORDS = frozenset(
    "a an and are as at be been but by can do does for from has have how if in into is it "
    "its no not of on or so such than that the their then there these this those to too was "
    "were what when where which while who why will with within without you your".split()
)
IDENT_EXCLUDE = frozenset("ArcGIS ArcPy FreeCAD NumPy OpenSees OpenSeesPy Revit SciPy".split())

# §7.1 pack top level; the approval basis is one line in the file.
PACK_VERSION = "1.0"
PACK_APPROVED_BY = "Chad Josewski"
PACK_APPROVED_AT = "2026-11-20"
PERMISSION_STATUS = "approved_for_assessed_generation"
APPROVAL_BASIS_TEMPLATE = (
    'Owner source-use decisions of 2026-11-20 (ITERATION_LOG.md, "Corrected-generator '
    'decisions (owner, November 20)"): tier 1 admits the five engineering-v1 sources within '
    "their own terms and notices, local only; tier 2 admits same-pin additions, Esri Pro-era "
    "Apache-2.0 samples (not pinned to ArcGIS Pro 3.6) and ADN-DevTech Revit 2025 member pages "
    "(the owner judges that the MIT grant covers them; the README traces them to the Revit "
    "SDK). Static entries are engineering-v1 unchanged (file "
    "878854bc28a977256d203b16966ce5c1b334ba655622b0c7a5ddceb77be6e341, approved 2026-11-10). "
    "Corpus manifest sha256 {corpus_manifest_sha256}. Uses: local noncommercial coursework "
    "generation, human review, local judge context and local evidence; export local_only; no "
    "excerpt is sent to a hosted service."
)
SOURCE_FIELDS = (
    "id",
    "url",
    "version",
    "retrieved_at",
    "license",
    "license_evidence",
    "attribution",
    "installation",
    "text",
    "content_sha256",
    "allowed_uses",
    "export_permission",
)
ENVIRONMENT_HEADER = (
    "Environment passage v1 for {TARGET}. Each block below is verbatim from the named pinned "
    "file; nothing here was executed."
)


def constants() -> dict:
    """Every §2 constant, as copied into each receipt."""
    return {
        "PACK_ID": PACK_ID,
        "PROMPT_VARIANT": PROMPT_VARIANT,
        "CATEGORY_CODES": dict(CATEGORY_CODES),
        "NORMALIZATION": NORMALIZATION,
        "CHUNK_MAX_LINES": CHUNK_MAX_LINES,
        "CHUNK_STRIDE_LINES": CHUNK_STRIDE_LINES,
        "CHUNK_MAX_TOKENS": CHUNK_MAX_TOKENS,
        "MIN_TERM_LENGTH": MIN_TERM_LENGTH,
        "BM25_K1": BM25_K1,
        "BM25_B": BM25_B,
        "IDENT_BONUS_FRACTION": IDENT_BONUS_FRACTION,
        "IDENT_BONUS_MAX_MATCHES": IDENT_BONUS_MAX_MATCHES,
        "SCORE_FLOOR_FRACTION": SCORE_FLOOR_FRACTION,
        "SELECT_MAX_PASSAGES": SELECT_MAX_PASSAGES,
        "SELECT_MAX_TOKENS": SELECT_MAX_TOKENS,
        "SCORE_DECIMALS": SCORE_DECIMALS,
        "ENV_MAX_TOKENS": ENV_MAX_TOKENS,
        "ADN_MAX_PAGES": ADN_MAX_PAGES,
        "PROMPT_TOKEN_CAP": PROMPT_TOKEN_CAP,
        "PREFLIGHT_ENUMERATION": dict(PREFLIGHT_ENUMERATION),
        "GUIDANCE_MAX_TOKENS": GUIDANCE_MAX_TOKENS,
        "LEAKAGE_N": LEAKAGE_N,
        "METRIC_FLOORS": dict(METRIC_FLOORS),
        "CLAUSE_SHA256": CLAUSE_SHA256,
        "STOPWORDS": sorted(STOPWORDS),
        "IDENT_EXCLUDE": sorted(IDENT_EXCLUDE),
    }


# ------------------------------------------------------------------ §1.3 serializers


def pack_json(pack: Mapping) -> str:
    """The pack serializer; it reproduces engineering-v1.json byte for byte."""
    return json.dumps(pack, indent=2, ensure_ascii=False) + "\n"


def record_json(value) -> str:
    """Manifests, receipts, reports and gates."""
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n"


def jsonl_line(row: Mapping) -> str:
    """One ``chunks.jsonl`` row, without its LF."""
    return json.dumps(row, ensure_ascii=False, allow_nan=False, sort_keys=True)


def write_new(path: Path, text: str) -> str:
    """Write UTF-8 text with LF untouched by exclusive create; return its sha256."""
    data = text.encode("utf-8")
    with open(path, "xb") as stream:
        stream.write(data)
    return hashlib.sha256(data).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------ §3.6 and §5.1 text model


JSONL_SEPARATORS = ("\x85", "\u2028", "\u2029")


def separator_location(text: str) -> tuple[int, str] | None:
    """First line number and character that ``str.splitlines`` would split on besides LF.

    ``json.dumps(ensure_ascii=False)`` leaves these raw, and the pinned
    ``tracing.read_records`` splits ledgers with ``splitlines()``, so admitted text
    holding one could never be read back from a ledger.
    """
    line = 1
    for char in text:
        if char == "\n":
            line += 1
        elif char in JSONL_SEPARATORS:
            return line, f"U+{ord(char):04X}"
    return None


def n1(raw: bytes) -> str:
    """N1: strict UTF-8, one leading BOM removed, CRLF then CR to LF, one LF appended."""
    text = raw.decode("utf-8")
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n") + "\n"


def git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()


def split_lines(text: str) -> list[str]:
    """§5.1: split on LF; a final empty element after a trailing LF is dropped."""
    lines = text.split("\n")
    if text.endswith("\n"):
        lines.pop()
    return lines


def reslice(text: str, start: int, end: int, removed_within: Iterable[Sequence]) -> str:
    """Lines ``start..end`` of a normalized or derived text minus the recorded removals."""
    lines = split_lines(text)
    if start < 1 or end < start or end > len(lines):
        raise ValueError(f"line span {start}-{end} is outside the text")
    removed: set[int] = set()
    for item in removed_within:
        removed.update(range(int(item[0]), int(item[1]) + 1))
    return "\n".join(lines[n - 1] for n in range(start, end + 1) if n not in removed)


def parse_ranges(spec: str) -> list[int]:
    """``"6,15,47-49"`` -> ``[6, 15, 47, 48, 49]``; ascending, no duplicates."""
    lines: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not re.fullmatch(r"\d+(?:-\d+)?", part):
            raise ValueError(f"invalid line range {part!r}")
        first, _, last = part.partition("-")
        a, b = int(first), int(last or first)
        if a < 1 or b < a:
            raise ValueError(f"invalid line range {part!r}")
        lines.extend(range(a, b + 1))
    if lines != sorted(set(lines)):
        raise ValueError("line ranges must be ascending without overlap")
    return lines


def format_ranges(lines: Iterable[int]) -> str:
    """Ascending runs as ``a-b`` and single lines as ``a``, comma-separated, no spaces."""
    values = sorted(set(lines))
    runs: list[list[int]] = []
    for n in values:
        if runs and n == runs[-1][1] + 1:
            runs[-1][1] = n
        else:
            runs.append([n, n])
    return ",".join(str(a) if a == b else f"{a}-{b}" for a, b in runs)


def _runs(lines: Iterable[int]) -> list[tuple[int, int]]:
    values = sorted(set(lines))
    runs: list[list[int]] = []
    for n in values:
        if runs and n == runs[-1][1] + 1:
            runs[-1][1] = n
        else:
            runs.append([n, n])
    return [(a, b) for a, b in runs]


# ------------------------------------------------------------------ AR-2 and file metadata


def glob_match(pattern: str, path: str, any_depth: bool = False) -> bool:
    """AR-2: ``*`` matches any characters except ``/``; any depth matches the file name."""
    regex = "".join("[^/]*" if ch == "*" else re.escape(ch) for ch in pattern)
    target = path.rsplit("/", 1)[-1] if any_depth else path
    return re.fullmatch(regex, target) is not None


_LANGUAGES = {
    ".cs": "csharp",
    ".cpp": "cpp",
    ".h": "cpp",
    ".py": "python",
    ".pyt": "python",
    ".xml": "xml",
    ".addin": "xml",
    ".csproj": "msbuild",
    ".rst": "rst",
    ".md": "markdown",
    ".json": "json",
    ".htm": "html",
    ".html": "html",
    ".hhk": "html",
}


def file_language(path: str, derived: str | None = None) -> str:
    if derived == "pdf_text":
        return "text"
    name = path.rsplit("/", 1)[-1]
    suffix = name[name.rfind(".") :].lower() if "." in name else ""
    return _LANGUAGES.get(suffix, "text")


def rule_family(path: str, derived: str | None = None) -> str:
    """Which §5.2 rules apply: ``cs``, ``c``, ``python``, ``xml``, ``cheat_sheet`` or ``none``."""
    if derived == "pdf_text":
        return "cheat_sheet"
    if derived is not None:
        return "none"
    name = path.rsplit("/", 1)[-1].lower()
    if name.endswith(".cs"):
        return "cs"
    if name.endswith((".cpp", ".h")):
        return "c"
    if name.endswith((".py", ".pyt")):
        return "python"
    if name.endswith(".xml"):
        return "xml"
    return "none"


# ------------------------------------------------------------------ §5.2 live-code rule

LICENSE_KW = re.compile(r"(?i)copyright|licen[cs]e|\(c\)|©|lgpl|gpl|apache|\bmit\b|bsd")
HEADER_LINE = re.compile(r"(?i)copyright|\(c\)|©")
_STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\])*"')
_COOKIE = re.compile(r"^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)")
_PY_SIGNAL = (
    ast.Call,
    ast.Assign,
    ast.AugAssign,
    ast.AnnAssign,
    ast.Import,
    ast.ImportFrom,
    ast.Return,
    ast.Raise,
    ast.Assert,
    ast.Delete,
    ast.Global,
    ast.Nonlocal,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.If,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.Lambda,
    ast.Attribute,
    ast.Subscript,
)


class NotPython3(ValueError):
    """The file does not tokenize or parse under the locked Python (``not_python3``)."""


@dataclass(frozen=True)
class LiveCode:
    """Removed line ranges ``(start, end, reason)`` and no-boundary ranges ``(start, end)``."""

    removed: tuple[tuple[int, int, str], ...]
    no_boundary: tuple[tuple[int, int], ...]

    def removed_lines(self) -> dict[int, str]:
        return {n: r for s, e, r in self.removed for n in range(s, e + 1)}

    def no_boundary_lines(self) -> frozenset[int]:
        return frozenset(n for s, e in self.no_boundary for n in range(s, e + 1))


def _removal_ranges(removed: Mapping[int, str]) -> tuple[tuple[int, int, str], ...]:
    """Maximal runs of consecutive removed lines that share one reason."""
    out: list[list] = []
    for n in sorted(removed):
        reason = removed[n]
        if out and out[-1][1] == n - 1 and out[-1][2] == reason:
            out[-1][1] = n
        else:
            out.append([n, n, reason])
    return tuple((a, b, r) for a, b, r in out)


def live_code(text: str, family: str, *, notice_lines: tuple[int, int] | None = None) -> LiveCode:
    """Apply the §5.2 rules of one family in their listed order."""
    lines = split_lines(text)
    removed: dict[int, str] = {}
    no_boundary: set[int] = set()
    if family in ("cs", "c"):
        blanked = [
            _STRING_LITERAL.sub(lambda m: '"' + " " * (len(m.group()) - 2) + '"', line)
            for line in lines
        ]
        if family == "cs":
            _cs2(blanked, removed)
        inside = _block_comments(blanked, removed, no_boundary)
        _cs1(blanked, removed, inside)
    elif family == "python":
        _py2(lines, removed)
        _py3(text, removed)
        _py1(text, removed)
    elif family == "xml":
        _xml1(text, lines, removed)
    elif family == "cheat_sheet":
        span = notice_block(lines)
        if span is None:
            raise ValueError("cheat-sheet notice block not found")
        if notice_lines is not None and span != tuple(notice_lines):
            raise ValueError(f"cheat-sheet notice block is lines {span}, expected {notice_lines}")
        for n in range(span[0], span[1] + 1):
            removed[n] = "notice_block"
    elif family != "none":
        raise ValueError(f"unknown live-code family {family!r}")
    no_boundary -= set(removed)
    return LiveCode(_removal_ranges(removed), tuple(_runs(no_boundary)))


def _cs2(blanked: Sequence[str], removed: dict[int, str]) -> None:
    """CS-2: the ``#region Header`` span, else the leading ``//`` run, when it is a license."""
    if not blanked:
        return
    span: list[int] = []
    if blanked[0].strip() == "#region Header":
        end = next(
            (
                n
                for n in range(2, min(40, len(blanked)) + 1)
                if blanked[n - 1].strip().startswith("#endregion")
            ),
            None,
        )
        if end is not None:
            span = list(range(1, end + 1))
            if any(LICENSE_KW.search(blanked[n - 1]) for n in span):
                for n in span:
                    removed[n] = "license_banner"
            return
    first = next((n for n, line in enumerate(blanked, 1) if line.strip()), None)
    if first is None:
        return
    n = first
    while n <= len(blanked) and blanked[n - 1].strip().startswith("//"):
        span.append(n)
        n += 1
    if span and any(LICENSE_KW.search(blanked[k - 1]) for k in span):
        for k in span:
            removed[k] = "license_banner"


def _block_comments(
    blanked: Sequence[str], removed: dict[int, str], no_boundary: set[int]
) -> set[int]:
    """BC-1 and BC-2 over a lexed view; returns every line inside a kept block comment."""
    comments: list[dict] = []
    code_lines: set[int] = set()
    current: dict | None = None
    for n, line in enumerate(blanked, 1):
        if n in removed:
            continue
        pos, code_seen, closed_here = 0, False, []
        while True:
            if current is not None:
                k = line.find("*/", pos)
                if k < 0:
                    break
                current["close"], current["after"] = n, False
                comments.append(current)
                closed_here.append(current)
                current, pos = None, k + 2
                continue
            starts = [(line.find(m, pos), m) for m in ("//", "/*")]
            starts = [(k, m) for k, m in starts if k >= 0]
            k, marker = min(starts) if starts else (len(line), "")
            if line[pos:k].strip():
                code_seen = True
                for comment in closed_here:
                    comment["after"] = True
            if marker != "/*":
                break
            doc = (line.startswith("/**", k) and not line.startswith("/***", k)) or line.startswith(
                "/*!", k
            )
            current = {"open": n, "before": code_seen, "doc": doc}
            pos = k + 2
        if code_seen:
            code_lines.add(n)
    if current is not None:
        current["close"], current["after"] = len(blanked), False
        comments.append(current)
    first_code = min(code_lines) if code_lines else None
    inside: set[int] = set()
    first_whole = True
    for comment in comments:
        o, c = comment["open"], comment["close"]
        inside.update(range(o, c + 1))
        if comment["before"] or comment["after"] or comment["doc"]:
            # A kept multi-line doc comment with no code on its delimiter lines is one
            # unit: no passage may start or end on its opener or closer (amendment
            # 2026-11-20 to §5.2 BC-1).
            whole = comment["doc"] and c > o and not comment["before"] and not comment["after"]
            no_boundary.update(range(o if whole else o + 1, c + 1 if whole else c))
            continue
        span = [x for x in range(o, c + 1) if x not in removed]
        banner = (
            first_whole
            and (first_code is None or o < first_code)
            and any(LICENSE_KW.search(blanked[x - 1]) for x in span)
        )
        first_whole = False
        for x in span:
            removed[x] = "license_banner" if banner else "block_comment"
    return inside


def _cs1(blanked: Sequence[str], removed: dict[int, str], inside: set[int]) -> None:
    """CS-1: ``//`` lines whose body does not start with exactly one space are code."""
    for n, line in enumerate(blanked, 1):
        if n in removed or n in inside:
            continue
        stripped = line.strip()
        if stripped.startswith("//") and not stripped.startswith("///"):
            body = stripped[2:]
            if body and (body[0] != " " or body.startswith("  ")):
                removed[n] = "commented_out_code"


def _py2(lines: Sequence[str], removed: dict[int, str]) -> None:
    """PY-2: the leading comment run, after a shebang and encoding cookie, when a license."""
    pos = 1 if lines and lines[0].startswith("#!") else 0
    if pos < min(2, len(lines)) and _COOKIE.match(lines[pos]):
        pos += 1
    while pos < len(lines) and not lines[pos].strip():
        pos += 1
    run = []
    while pos < len(lines) and lines[pos].lstrip().startswith("#"):
        run.append(pos + 1)
        pos += 1
    if run and any(LICENSE_KW.search(lines[n - 1]) for n in run):
        for n in run:
            removed[n] = "license_banner"


def _parse_python(text: str) -> ast.Module:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return ast.parse(text)
        except (SyntaxError, ValueError, RecursionError, MemoryError, OverflowError) as exc:
            raise NotPython3(f"not parseable as Python 3: {exc}") from exc


def _py3(text: str, removed: dict[int, str]) -> None:
    """PY-3: a module-level string statement that states a license is a banner."""
    for node in _parse_python(text).body:
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            value = node.value.value
            if re.search(r"(?i)licensed under", value) or (
                re.search(r"(?i)copyright", value) and re.search(r"(?i)licen[cs]e", value)
            ):
                for n in range(node.lineno, node.end_lineno + 1):
                    removed.setdefault(n, "license_banner")


def _comment_only_lines(text: str) -> dict[int, str]:
    """Lines whose only tokens are COMMENT, NL, NEWLINE, INDENT or DEDENT, with the comment."""
    comments: dict[int, str] = {}
    code: set[int] = set()
    ignored = {
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
        tokenize.ENCODING,
    }
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                comments[token.start[0]] = token.string
            elif token.type not in ignored:
                code.update(range(token.start[0], token.end[0] + 1))
    except (tokenize.TokenError, SyntaxError, ValueError) as exc:
        raise NotPython3(f"does not tokenize: {exc}") from exc
    return {n: s for n, s in comments.items() if n not in code}


def has_code_signal(source: str) -> bool:
    """PY-1: the source parses and contains a code-signal node."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError, RecursionError, MemoryError, OverflowError):
            return False
    for node in ast.walk(tree):
        if isinstance(node, _PY_SIGNAL):
            return True
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and node.elts:
            return True
        if isinstance(node, ast.Dict) and node.keys:
            return True
    return False


def _py1(text: str, removed: dict[int, str]) -> None:
    """PY-1: greedy removal of comment runs that parse as code."""
    comment_only = _comment_only_lines(text)
    rows = sorted(n for n in comment_only if n not in removed)
    runs: list[list[int]] = []
    for n in rows:
        if runs and runs[-1][-1] == n - 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    for run in runs:
        bodies = []
        for n in run:
            body = comment_only[n].lstrip("#")
            bodies.append(body[1:] if body.startswith(" ") else body)
        i = 0
        while i < len(run):
            found = None
            for j in range(len(run) - 1, i - 1, -1):
                if has_code_signal(textwrap.dedent("\n".join(bodies[i : j + 1]))):
                    found = j
                    break
            if found is None:
                i += 1
                continue
            for n in run[i : found + 1]:
                removed[n] = "commented_out_code"
            i = found + 1


def _xml_root_line(text: str) -> int:
    parser = xml.parsers.expat.ParserCreate()
    root: list[int] = []

    def start(name, attrs):
        if not root:
            root.append(parser.CurrentLineNumber)

    parser.StartElementHandler = start
    try:
        parser.Parse(text, True)
    except xml.parsers.expat.ExpatError as exc:
        raise ValueError(f"XML is not well formed: {exc}") from exc
    if not root:
        raise ValueError("XML has no root element")
    return root[0]


def _xml1(text: str, lines: Sequence[str], removed: dict[int, str]) -> None:
    """XML-1: whole-line comments; a license comment before the root tag is a banner."""
    root_line = _xml_root_line(text)
    n = 1
    while n <= len(lines):
        line = lines[n - 1]
        if n not in removed and line.strip().startswith("<!--"):
            rest, k = line[line.index("<!--") + 4 :], n
            close = None
            while True:
                idx = rest.find("-->")
                if idx >= 0:
                    close, after = k, rest[idx + 3 :]
                    break
                k += 1
                if k > len(lines):
                    break
                rest = lines[k - 1]
            if close is not None and not after.strip():
                span = [x for x in range(n, close + 1) if x not in removed]
                banner = close < root_line and any(LICENSE_KW.search(lines[x - 1]) for x in span)
                for x in span:
                    removed[x] = "license_banner" if banner else "xml_comment"
                n = close + 1
                continue
        n += 1


def notice_block(lines: Sequence[str]) -> tuple[int, int] | None:
    """TXT-1: the first ``Copyright ©`` line through the first line ending ``mark owners.``."""
    start = next((n for n, line in enumerate(lines, 1) if line.startswith("Copyright ©")), None)
    if start is None:
        return None
    end = next(
        (n for n in range(start, len(lines) + 1) if lines[n - 1].rstrip().endswith("mark owners.")),
        None,
    )
    return None if end is None else (start, end)


def is_unstable(stability: float) -> bool:
    """Listed only strictly below the threshold; 0.34 itself is not listed."""
    return stability < STABILITY_LIST_BELOW


def notice_text(lines: Sequence[str], span: tuple[int, int]) -> str:
    """``{NOTICE}``: the notice lines, each stripped, joined with one space."""
    return " ".join(lines[n - 1].strip() for n in range(span[0], span[1] + 1))


PY_LICENSE_START = re.compile(r"(?i)\blicen[cs]ed? under\b")


def _strip_comment_markers(line: str) -> str:
    text = line.strip()
    while True:
        before = text
        for marker in ("//", "/*", "#"):
            if text.startswith(marker):
                text = text[len(marker) :]
        if text.endswith("*/"):
            text = text[:-2]
        text = text.strip().strip("*").strip()
        if text == before:
            break
    return " ".join(text.split())


def file_header(lines: Sequence[str], removed: Iterable[Sequence]) -> str | None:
    """§3.8 ``{HEADER}`` text from the removed license banner, or None."""
    banner = sorted(
        n for item in removed if item[2] == "license_banner" for n in range(item[0], item[1] + 1)
    )
    members = set(banner)
    start = next((n for n in banner if HEADER_LINE.search(lines[n - 1])), None)
    if start is None:
        return None
    # An odd count of triple quotes before the copyright line means the walk starts in a quote.
    before = sum(lines[m - 1].count('"""') + lines[m - 1].count("'''") for m in banner if m < start)
    parts, n, in_quote = [], start, before % 2 == 1
    while n in members:
        raw = lines[n - 1]
        stripped = raw.strip()
        if stripped.startswith(("#region", "#endregion")):
            break  # a preprocessor directive, not a comment line
        marks = raw.count('"""') + raw.count("'''")
        quoted = in_quote or marks > 0
        if marks % 2:
            in_quote = not in_quote
        text = _strip_comment_markers(raw.replace('"""', " ").replace("'''", " "))
        if not text or (quoted and PY_LICENSE_START.search(text)):
            break  # a module-string banner keeps only the copyright text before the license
        parts.append(text)
        n += 1
    return " ".join(parts) or None


def fill_attribution(
    template: str,
    *,
    owner: str = "",
    repo: str = "",
    header: str | None = None,
    notice: str | None = None,
    regents_notice: str | None = None,
) -> str:
    """Expand a §3.8 template; an unexpanded placeholder is an error."""
    text = template.replace("{owner}", owner).replace("{repo}", repo)
    text = text.replace("{HEADER}", f" File header: {header}" if header else "")
    if "{NOTICE}" in text:
        if not notice:
            raise ValueError("attribution needs the cheat-sheet notice")
        text = text.replace("{NOTICE}", notice)
    if "{REGENTS_NOTICE}" in text:
        if not regents_notice:
            raise ValueError("attribution needs the Regents notice")
        text = text.replace("{REGENTS_NOTICE}", regents_notice)
    if re.search(r"\{[A-Za-z_]+\}", text):
        raise ValueError("attribution template has an unknown placeholder")
    return text


# ------------------------------------------------------------------ §5.3 segments


@dataclass(frozen=True)
class Segment:
    start: int
    end: int
    label: str | None = None


def segments_freecad_pyxml(text: str) -> list[Segment]:
    """``freecad_pyxml``: the PythonExport header and each Methode and Attribute child."""
    parser = xml.parsers.expat.ParserCreate()
    stack: list[dict] = []
    out: list[Segment] = []

    def start(name, attrs):
        stack.append({"name": name, "attrs": attrs, "line": parser.CurrentLineNumber})

    def end(name):
        element = stack.pop()
        element["end"] = parser.CurrentLineNumber
        parent = stack[-1] if stack else None
        if parent is not None and parent["name"] == "PythonExport":
            parent.setdefault("children", []).append(element)
        if name == "PythonExport":
            attrs = element["attrs"]
            pn = attrs.get("PythonName") or (
                f"{attrs.get('Namespace', '')}.{attrs.get('Name', '')}".removesuffix("Py")
            )
            children = element.get("children", [])
            doc = next((c for c in children if c["name"] == "Documentation"), None)
            if doc is not None:
                out.append(Segment(element["line"], doc["end"], f"{pn} class"))
            for child in children:
                if child["name"] == "Methode":
                    out.append(
                        Segment(
                            child["line"],
                            child["end"],
                            f"{pn} method {child['attrs'].get('Name', '')}",
                        )
                    )
                elif child["name"] == "Attribute":
                    out.append(
                        Segment(
                            child["line"],
                            child["end"],
                            f"{pn} attribute {child['attrs'].get('Name', '')}",
                        )
                    )

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    try:
        parser.Parse(text, True)
    except xml.parsers.expat.ExpatError as exc:
        raise ValueError(f"XML is not well formed: {exc}") from exc
    return out


_PROPERTY_SOURCE = re.compile(r"^PROPERTY_SOURCE\w*\(\s*([A-Za-z_][\w:]*)")
_CLASS_DECL = re.compile(r"^class\s+(?:[A-Za-z_]\w*Export\s+)?([A-Za-z_]\w*)\b")


def segments_freecad_cpp(lines: Sequence[str], path: str) -> list[Segment]:
    """``freecad_cpp``: PROPERTY_SOURCE blocks in ``.cpp``, class declarations in ``.h``."""
    out: list[Segment] = []
    if path.endswith(".cpp"):
        starts = [(n, m) for n, line in enumerate(lines, 1) if (m := _PROPERTY_SOURCE.match(line))]
        for index, (n, m) in enumerate(starts):
            end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
            out.append(Segment(n, end, f"{m.group(1)} implementation"))
        return out
    if not path.endswith(".h"):
        raise ValueError("freecad_cpp applies to .cpp and .h files")
    n = 1
    while n <= len(lines):
        m = _CLASS_DECL.match(lines[n - 1])
        if m and not lines[n - 1].rstrip().endswith(";"):
            end = next(
                (k for k in range(n + 1, len(lines) + 1) if lines[k - 1].startswith("};")), None
            )
            if end is None:
                raise ValueError(f"class declaration at line {n} has no closing '}};' line")
            out.append(Segment(n, end, f"{m.group(1)} declaration"))
            n = end + 1
            continue
        n += 1
    return out


def public_names(init_source: str) -> list[str]:
    """Names imported by an ``__init__.py`` (``from .x import a, b``), in source order."""
    names: list[str] = []
    for node in _parse_python(init_source).body:
        if isinstance(node, ast.ImportFrom):
            names.extend(alias.asname or alias.name for alias in node.names)
    return names


def segments_python_public_api(text: str, names: Iterable[str]) -> list[Segment]:
    """``python_public_api``: each public top-level def or class through its docstring."""
    public = set(names)
    out: list[Segment] = []
    for node in _parse_python(text).body:
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef)) or node.name not in public:
            continue
        start = node.decorator_list[0].lineno if node.decorator_list else node.lineno
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            end = first.end_lineno
        else:
            end = first.lineno - 1
        if end >= start:
            out.append(Segment(start, end, f"{node.name} signature and docstring"))
    return out


_RST_UNDERLINE = re.compile(r"""([=\-~^*#"'+])\1{3,}""")


def segments_rst_sections(lines: Sequence[str], needle: str = "scipy.integrate") -> list[Segment]:
    """``rst_sections``: sections whose heading, without backquotes, contains the needle."""
    headings: list[tuple[int, int]] = []
    for i in range(len(lines) - 1):
        heading, under = lines[i], lines[i + 1]
        if not heading.strip() or heading[0].isspace():
            continue
        if _RST_UNDERLINE.fullmatch(under) and len(under) >= len(heading.rstrip()):
            start = i - 1 if i > 0 and lines[i - 1] == under else i
            headings.append((start, i))
    out: list[Segment] = []
    for index, (start, i) in enumerate(headings):
        end = headings[index + 1][0] - 1 if index + 1 < len(headings) else len(lines) - 1
        if needle in lines[i].replace("`", ""):
            out.append(Segment(start + 1, end + 1, lines[i].strip()))
    return out


# ------------------------------------------------------------------ §5.3 D-HTML extractor

_SC_BLOCK = frozenset(
    {
        "div",
        "p",
        "br",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "pre",
        "table",
        "tr",
        "li",
        "ul",
        "ol",
        "dl",
        "dt",
        "dd",
    }
)
_SC_VOID = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


class _Sandcastle(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[dict] = []
        self.lines: list[str] = []
        self.current: list[str] = []
        self.pre: list[str] | None = None
        self.title: str | None = None
        self.title_parts: list[str] = []

    def _suppressed(self) -> bool:
        return any(e["skip"] or e["lang"] for e in self.stack)

    def _end_line(self) -> None:
        line = " ".join("".join(self.current).split())
        self.current = []
        if line:
            self.lines.append(line)

    def _emit(self, text: str) -> None:
        if self.pre is not None:
            self.pre.append(text)
        else:
            self.current.append(re.sub(r"\s+", " ", text))

    def handle_starttag(self, tag, attrs):
        values = {k: (v or "") for k, v in attrs}
        classes = values.get("class", "").split()
        ident = values.get("id", "")
        suppressed = self._suppressed()
        element = {
            "tag": tag,
            "skip": tag in ("head", "script", "style")
            or ident in ("PageHeader", "PageFooter")
            or "codeSnippetContainerTabs" in classes
            or "codeSnippetToolBar" in classes
            or (
                tag == "div"
                and "codeSnippetContainerCode" in classes
                and not ident.endswith("_code_Div1")
            ),
            "tabs": "codeSnippetContainerTabs" in classes,
            "tab1": ident.endswith("_tab1") and any(e["tabs"] for e in self.stack),
            "lang": tag == "span" and "data-languagespecifictext" in values,
            "title": tag == "title",
            "anchor": [],
            "tab1_texts": [],
        }
        if not suppressed:
            if tag in _SC_BLOCK:
                if self.pre is not None:
                    self.pre.append("\n")
                else:
                    self._end_line()
            if tag in ("td", "th") and "".join(self.current).strip():
                self.current.append(" | ")
            if element["lang"]:
                pairs = dict(
                    part.split("=", 1)
                    for part in values["data-languagespecifictext"].split("|")
                    if "=" in part
                )
                value = pairs.get("cs", pairs.get("nu"))
                if value:
                    self._emit(value)
            if tag == "pre" and self.pre is None:
                self.pre = []
        if tag not in _SC_VOID:
            self.stack.append(element)

    def handle_endtag(self, tag):
        index = next(
            (i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i]["tag"] == tag), None
        )
        if index is None:
            return
        while len(self.stack) > index:
            element = self.stack.pop()
            if element["tab1"]:
                block = next((e for e in reversed(self.stack) if e["tabs"]), None)
                if block is not None:
                    block["tab1_texts"].append(" ".join("".join(element["anchor"]).split()))
            if element["tabs"] and element["tab1_texts"][:1] != ["C#"]:
                raise ValueError("Sandcastle code tabs: the first tab is not C#")
            if element["title"]:
                self.title = " ".join("".join(self.title_parts).split()) or None
            if element["tag"] == "pre" and self.pre is not None and not self._suppressed():
                self._flush_pre()
        if not self._suppressed() and tag in _SC_BLOCK:
            if self.pre is None:
                self._end_line()
            else:
                self.pre.append("\n")

    def _flush_pre(self) -> None:
        block = [line.rstrip() for line in "".join(self.pre).split("\n")]
        while block and not block[0]:
            block.pop(0)
        while block and not block[-1]:
            block.pop()
        self._end_line()
        self.lines.extend(block)
        self.pre = None

    def handle_data(self, data):
        if any(e["title"] for e in self.stack):
            self.title_parts.append(data)
        tab1 = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i]["tab1"]), None)
        if tab1 is not None and any(e["tag"] == "a" for e in self.stack[tab1:]):
            self.stack[tab1]["anchor"].append(data)
        if not self._suppressed():
            self._emit(data)


def sandcastle_extract(document: str) -> tuple[str, str | None]:
    """D-HTML: the Sandcastle member page as text, and its ``<title>``."""
    parser = _Sandcastle()
    parser.feed(document)
    parser.close()
    if parser.pre is not None:
        parser._flush_pre()
    parser._end_line()
    return "\n".join(parser.lines) + "\n", parser.title


def sandcastle_text(document: str) -> str:
    return sandcastle_extract(document)[0]


class _PreBlocks(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.blocks: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            if self.depth == 0:
                self.blocks.append([])
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "pre" and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.blocks[-1].append(data)


def regents_notice(
    document: str, *, starts_with: str, contains: str, last_line_suffix: str, line_count: int
) -> str:
    """``{REGENTS_NOTICE}``: the page's single ``<pre>`` block, first line through the end line.

    ``contains`` is checked with whitespace collapsed, because the notice wraps lines.
    """
    parser = _PreBlocks()
    parser.feed(document)
    parser.close()
    if len(parser.blocks) != 1:
        raise ValueError(f"license page has {len(parser.blocks)} <pre> blocks, expected one")
    lines = "".join(parser.blocks[0]).split("\n")
    end = next(
        (k for k, line in enumerate(lines) if line.rstrip().endswith(last_line_suffix)), None
    )
    if end is None:
        raise ValueError("Regents notice end line not found")
    notice = lines[: end + 1]
    if not notice[0].startswith(starts_with):
        raise ValueError("Regents notice does not start with the expected copyright line")
    if contains not in " ".join("\n".join(notice).split()):
        raise ValueError("Regents notice lacks the copies requirement")
    if len(notice) != line_count:
        raise ValueError(f"Regents notice has {len(notice)} lines, expected {line_count}")
    return "\n".join(notice)


# ------------------------------------------------------------------ §5.4 windows


def windows(
    live: Sequence[tuple[int, str]],
    no_boundary: Iterable[int],
    count_tokens: Callable[[str], int],
    *,
    max_lines: int = CHUNK_MAX_LINES,
    stride: int = CHUNK_STRIDE_LINES,
    max_tokens: int = CHUNK_MAX_TOKENS,
) -> tuple[list[tuple[int, int]], list[int]]:
    """§5.4 window walk over one segment's live lines; returns spans and oversize lines."""
    nb = set(no_boundary)

    def eligible(k: int) -> bool:
        return live[k][1].strip() != "" and live[k][0] not in nb

    def text(a: int, b: int) -> str:
        return "\n".join(line for _, line in live[a:b])

    candidates = [k for k in range(len(live)) if eligible(k)]
    if not candidates:
        return [], []
    last = candidates[-1]
    spans: list[tuple[int, int]] = []
    oversize: list[int] = []
    i = 0
    while True:
        j = min(i + max_lines, len(live))
        a = i
        while a < j and not eligible(a):
            a += 1
        b = j
        while b > a and not eligible(b - 1):
            b -= 1
        while b > a and count_tokens(text(a, b)) > max_tokens:
            b -= 1
            while b > a and not eligible(b - 1):
                b -= 1
        if b > a:
            if (live[a][0], live[b - 1][0]) not in spans:
                spans.append((live[a][0], live[b - 1][0]))
        elif a < j and live[a][0] not in oversize:
            oversize.append(live[a][0])
        if a >= len(live) or (b > a and b - 1 >= last):
            break
        i = max(i + 1, min(i + stride, b))
    return spans, oversize


def chunk_text(lines: Sequence[str], start: int, end: int, removed: Mapping[int, str]) -> str:
    return "\n".join(lines[n - 1] for n in range(start, end + 1) if n not in removed)


def chunk_segments(
    text: str,
    segments: Sequence[Segment],
    live: LiveCode,
    count_tokens: Callable[[str], int],
) -> tuple[list[dict], list[int]]:
    """Window every segment of one file; rows carry span, label, text, tokens and removals."""
    lines = split_lines(text)
    removed = live.removed_lines()
    no_boundary = live.no_boundary_lines()
    memo: dict[str, int] = {}

    def count(value: str) -> int:
        if value not in memo:
            memo[value] = int(count_tokens(value))
        return memo[value]

    rows: list[dict] = []
    oversize: set[int] = set()
    for segment in segments:
        if segment.start < 1 or segment.end > len(lines) or segment.end < segment.start:
            raise ValueError(f"segment {segment} is outside the text")
        view = [
            (n, lines[n - 1]) for n in range(segment.start, segment.end + 1) if n not in removed
        ]
        spans, over = windows(view, no_boundary, count)
        oversize.update(over)
        for a, b in spans:
            body = chunk_text(lines, a, b, removed)
            rows.append(
                {
                    "start": a,
                    "end": b,
                    "segment_label": segment.label,
                    "text": body,
                    "qwen_tokens": count(body),
                    "removed_within": [[s, e, r] for s, e, r in live.removed if s <= b and e >= a],
                }
            )
    return rows, sorted(oversize)


def finalize_chunks(rows: Sequence[Mapping]) -> tuple[list[dict], dict]:
    """§5.5: drop duplicate spans, collapse identical text per category, drop term-less chunks.

    Each row needs ``category``, ``file_key``, ``file_index``, ``start``, ``end``, ``text``,
    ``segment_label``, ``removed_within`` and ``qwen_tokens``.
    """
    order = {c: i for i, c in enumerate(CATEGORIES)}
    ordered = sorted(
        rows, key=lambda r: (order[r["category"]], r["file_index"], r["start"], r["end"])
    )
    seen: set[tuple] = set()
    first_by_text: dict[tuple[str, str], str] = {}
    kept: list[dict] = []
    record = {"duplicate_spans": [], "collapsed": [], "no_terms": []}
    for row in ordered:
        key = f"{row['file_key']}#L{row['start']}-L{row['end']}"
        span = (row["file_key"], row["start"], row["end"])
        if span in seen:
            record["duplicate_spans"].append(key)
            continue
        seen.add(span)
        text_key = (row["category"], row["text"])
        if text_key in first_by_text:
            record["collapsed"].append({"chunk_key": key, "kept": first_by_text[text_key]})
            continue
        first_by_text[text_key] = key
        n_terms = len(terms(row["text"]))
        if n_terms == 0:
            record["no_terms"].append(key)
            continue
        kept.append(
            {
                "chunk_key": key,
                "category": row["category"],
                "file_key": row["file_key"],
                "file_index": row["file_index"],
                "start": row["start"],
                "end": row["end"],
                "segment_label": row["segment_label"],
                "removed_within": [list(r) for r in row["removed_within"]],
                "text": row["text"],
                "content_sha256": digest(row["text"]),
                "qwen_tokens": row["qwen_tokens"],
                "n_terms": n_terms,
            }
        )
    return kept, record


# ------------------------------------------------------------------ §6.1 terms

_IDENT = r"[A-Za-z_][A-Za-z0-9_]*(?:(?:\.|::)[A-Za-z_][A-Za-z0-9_]*)*(?:@[A-Za-z0-9_]*)?"
_NUMBER = r"\d+(?:\.\d+)*(?:[eE][-+]?\d+)?"
CANDIDATE_RE = re.compile(f"{_IDENT}|{_NUMBER}", re.ASCII)
_SUBWORD = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", re.ASCII)
_SEPARATORS = re.compile(r"(\.|::|@)")


def candidates(text: str) -> list[str]:
    """§6.1 CANDIDATE matches, left to right, with repeats."""
    return [m.group() for m in CANDIDATE_RE.finditer(text)]


def _is_number(candidate: str) -> bool:
    return candidate[:1].isdigit()


def candidate_terms(candidate: str) -> set[str]:
    """``terms(c)`` after lowercasing, the length floor and the stopwords."""
    if _is_number(candidate):
        found = {candidate}
    else:
        pieces = _SEPARATORS.split(candidate)
        parts = pieces[0::2]
        found = {candidate}
        found.update(p for p in parts if p)
        for k in range(2, len(parts) + 1):
            first = len(parts) - k
            if all(parts[first:]):
                found.add("".join(pieces[2 * first :]))
        for part in parts:
            subwords = [w for piece in part.split("_") for w in _SUBWORD.findall(piece)]
            if len(subwords) >= 2:
                found.update(subwords)
    lowered = {t.lower() for t in found}
    return {t for t in lowered if len(t) >= MIN_TERM_LENGTH and t not in STOPWORDS}


def terms(text: str) -> list[str]:
    """A text's BM25 term multiset: each candidate's distinct terms, once per occurrence."""
    out: list[str] = []
    for candidate in candidates(text):
        out.extend(sorted(candidate_terms(candidate)))
    return out


# ------------------------------------------------------------------ §6.3 identifiers


def is_code_like(candidate: str) -> bool:
    """§6.3: not a number, and dotted, scoped, ``@``, underscored, camel or letters+digits."""
    if not candidate or _is_number(candidate):
        return False
    return bool(
        re.search(r"\.|::|@|_", candidate)
        or re.search(r"[a-z][A-Z]", candidate)
        or re.fullmatch(r"[A-Za-z]+[0-9]+", candidate)
    )


def code_like_tokens(text: str) -> list[str]:
    """Code-like candidates in first-appearance order, deduplicated; no exclusions."""
    out: list[str] = []
    for candidate in candidates(text):
        if is_code_like(candidate) and candidate not in out:
            out.append(candidate)
    return out


def brief_identifiers(brief: str) -> list[str]:
    """``I(brief)``: code-like candidates not in ``IDENT_EXCLUDE``."""
    return [c for c in code_like_tokens(brief) if c not in IDENT_EXCLUDE]


def identifier_pattern(identifier: str) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(identifier) + r"(?![A-Za-z0-9_])")


def identifier_in(identifier: str, text: str) -> bool:
    """§6.3 exact, case-sensitive match on identifier boundaries."""
    return identifier_pattern(identifier).search(text) is not None


def brief_sentences(brief: str) -> list[str]:
    """G7 stability split."""
    return re.split(r"(?<=[.?!])\s+(?=[A-Z])", brief)


def prose_only(brief: str) -> str:
    """The brief with each occurrence of its identifiers blanked (report-only selection)."""
    identifiers = set(brief_identifiers(brief))
    pieces, pos = [], 0
    for m in CANDIDATE_RE.finditer(brief):
        if m.group() in identifiers:
            pieces.append(brief[pos : m.start()] + " ")
            pos = m.end()
    pieces.append(brief[pos:])
    return " ".join("".join(pieces).split())


def g5_tokens(text: str) -> list[str]:
    """G5 token stream."""
    return re.findall(r"[a-z0-9]+", text.lower())


def ngrams(tokens: Sequence[str], n: int = LEAKAGE_N) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


# ------------------------------------------------------------------ §6.2 Okapi BM25


class BM25Index:
    """Okapi BM25 over term lists; per-document sums run in sorted query-term order."""

    def __init__(
        self, documents: Sequence[Sequence[str]], *, k1: float = BM25_K1, b: float = BM25_B
    ):
        self.k1, self.b = k1, b
        self.tf = [Counter(doc) for doc in documents]
        self.length = [len(doc) for doc in documents]
        self.n = len(documents)
        self.avgdl = sum(self.length) / self.n if self.n else 0.0
        self.df: Counter = Counter()
        self.postings: dict[str, list[int]] = {}
        for index, counts in enumerate(self.tf):
            for term in sorted(counts):
                self.df[term] += 1
                self.postings.setdefault(term, []).append(index)

    def idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log((self.n - df + 0.5) / (df + 0.5) + 1)

    def scores(self, query_terms: Iterable[str]) -> list[float]:
        out = [0.0] * self.n
        if not self.n or not self.avgdl:
            return out
        k1, b = self.k1, self.b
        for term in sorted(set(query_terms)):
            postings = self.postings.get(term)
            if not postings:
                continue
            weight = self.idf(term)
            for index in postings:
                tf = self.tf[index][term]
                norm = k1 * (1 - b + b * self.length[index] / self.avgdl)
                out[index] += weight * tf * (k1 + 1) / (tf + norm)
        return out


def bm25_scores(documents: Sequence[str], query: str) -> list[float]:
    """Raw BM25 of a query text against document texts (§6.2), rounded to 9 decimals."""
    index = BM25Index([terms(d) for d in documents])
    return [round(s, SCORE_DECIMALS) for s in index.scores(terms(query))]


# ------------------------------------------------------------------ §6.4 ranking and selection


@dataclass(frozen=True)
class Chunk:
    chunk_key: str
    category: str
    file_key: str
    file_index: int
    start: int
    end: int
    text: str
    qwen_tokens: int
    removed_within: tuple[tuple[int, int, str], ...] = ()
    segment_label: str | None = None
    content_sha256: str = ""

    @classmethod
    def from_row(cls, row: Mapping) -> Chunk:
        return cls(
            chunk_key=row["chunk_key"],
            category=row["category"],
            file_key=row["file_key"],
            file_index=int(row["file_index"]),
            start=int(row["start"]),
            end=int(row["end"]),
            text=row["text"],
            qwen_tokens=int(row["qwen_tokens"]),
            removed_within=tuple((int(a), int(b), str(r)) for a, b, r in row["removed_within"]),
            segment_label=row.get("segment_label"),
            content_sha256=row.get("content_sha256") or digest(row["text"]),
        )

    def live_line_numbers(self) -> list[int]:
        removed = {n for a, b, _ in self.removed_within for n in range(a, b + 1)}
        return [n for n in range(self.start, self.end + 1) if n not in removed]


def passage_id(category: str, text: str) -> str:
    return f"{CATEGORY_CODES[category]}-p-{digest(text)[:12]}"


@dataclass(frozen=True)
class Scored:
    chunk: Chunk
    r_raw: float
    r_final: float
    m: int


def score_chunk(chunk: Chunk, raw: float, m: int, top_raw: float) -> Scored:
    """§6.3 final score; both scores rounded to ``SCORE_DECIMALS``."""
    final = raw + IDENT_BONUS_FRACTION * top_raw * min(m, IDENT_BONUS_MAX_MATCHES)
    return Scored(chunk, round(raw, SCORE_DECIMALS), round(final, SCORE_DECIMALS), m)


def rank_key(scored: Scored) -> tuple:
    c = scored.chunk
    return (-scored.r_final, -scored.m, -scored.r_raw, c.file_index, c.start, c.end, c.chunk_key)


def rank(scored: Iterable[Scored]) -> list[Scored]:
    """§6.4 step 2: a total order."""
    return sorted(scored, key=rank_key)


@dataclass(frozen=True)
class Candidate:
    chunk: Chunk
    r_raw: float
    r_final: float
    m: int
    decision: str


def select_ranked(
    ranked: Sequence[Scored],
    blocked: Mapping[str, Iterable[int]] | None = None,
    *,
    k: int = SELECT_MAX_PASSAGES,
    budget: int = SELECT_MAX_TOKENS,
) -> tuple[list[Chunk], list[Candidate], float]:
    """§6.4 steps 3-5: floor, then the walk with overlap and budget skips, stop after k."""
    floor = round(SCORE_FLOOR_FRACTION * ranked[0].r_final, SCORE_DECIMALS) if ranked else 0.0
    taken = {key: set(lines) for key, lines in (blocked or {}).items()}
    used, selected, decisions = 0, [], []
    for item in ranked:
        chunk = item.chunk
        if item.r_final <= 0 or item.r_final < floor:
            decision = "below_floor"
        elif len(selected) >= k:
            decision = "k_reached"
        elif chunk.file_key in taken and any(
            n in taken[chunk.file_key] for n in range(chunk.start, chunk.end + 1)
        ):
            decision = "overlap"
        elif used + chunk.qwen_tokens > budget:
            decision = "budget"
        else:
            decision = "selected"
            selected.append(chunk)
            used += chunk.qwen_tokens
            taken.setdefault(chunk.file_key, set()).update(range(chunk.start, chunk.end + 1))
        decisions.append(Candidate(chunk, item.r_raw, item.r_final, item.m, decision))
    return selected, decisions, floor


@dataclass(frozen=True)
class Retrieval:
    query_terms: list[str]
    identifiers: list[str]
    identifier_chunks: dict[str, int]
    top_raw: float
    floor: float
    ranking: list[Candidate]
    selected: list[Chunk]

    @property
    def selected_tokens(self) -> int:
        return sum(c.qwen_tokens for c in self.selected)


class CategoryRetriever:
    """One category index (§6), with the environment passage's lines blocked."""

    def __init__(self, chunks: Sequence[Chunk], blocked: Mapping[str, Iterable[int]] | None = None):
        self.chunks = list(chunks)
        self.index = BM25Index([terms(c.text) for c in self.chunks])
        self.blocked = {key: frozenset(lines) for key, lines in (blocked or {}).items()}

    def rank(self, query: str) -> tuple[list[Scored], list[str], list[str], dict, float]:
        """§6.2-§6.4 step 2: ranked scores, query terms, identifiers, their counts, top_raw."""
        query_terms = sorted(set(terms(query)))
        identifiers = brief_identifiers(query)
        raw = self.index.scores(query_terms)
        top_raw = max(raw) if raw else 0.0
        patterns = [identifier_pattern(x) for x in identifiers]
        identifier_chunks = dict.fromkeys(identifiers, 0)
        scored = []
        for index, chunk in enumerate(self.chunks):
            hits = [x for x, p in zip(identifiers, patterns, strict=True) if p.search(chunk.text)]
            for x in hits:
                identifier_chunks[x] += 1
            scored.append(score_chunk(chunk, raw[index], len(hits), top_raw))
        return rank(scored), query_terms, identifiers, identifier_chunks, top_raw

    def retrieve(
        self, query: str, *, k: int = SELECT_MAX_PASSAGES, budget: int = SELECT_MAX_TOKENS
    ) -> Retrieval:
        ranked, query_terms, identifiers, identifier_chunks, top_raw = self.rank(query)
        selected, ranking, floor = select_ranked(ranked, self.blocked, k=k, budget=budget)
        return Retrieval(
            query_terms=query_terms,
            identifiers=identifiers,
            identifier_chunks=identifier_chunks,
            top_raw=round(top_raw, SCORE_DECIMALS),
            floor=floor,
            ranking=ranking,
            selected=selected,
        )


# ------------------------------------------------------------------ §6.5 environment passages


@dataclass(frozen=True)
class EnvironmentBlock:
    owner: str
    repo: str
    commit: str
    path: str
    derived: bool
    lines: tuple[int, ...]
    texts: tuple[str, ...]

    @property
    def display_path(self) -> str:
        return self.path + (" (text extraction)" if self.derived else "")


def environment_block(
    *, owner: str, repo: str, commit: str, path: str, derived: bool, text: str, lines: Sequence[int]
) -> EnvironmentBlock:
    """Select verbatim normalized (or derived) lines of one pinned file."""
    all_lines = split_lines(text)
    if not lines or list(lines) != sorted(set(lines)):
        raise ValueError("environment lines must be ascending and unique")
    if lines[0] < 1 or lines[-1] > len(all_lines):
        raise ValueError(f"environment lines exceed {path}")
    return EnvironmentBlock(
        owner, repo, commit, path, derived, tuple(lines), tuple(all_lines[n - 1] for n in lines)
    )


def environment_text(target: str, blocks: Sequence[EnvironmentBlock]) -> str:
    """§6.5 exact text, joined with LF and without a trailing newline."""
    out = [ENVIRONMENT_HEADER.replace("{TARGET}", target)]
    for block in blocks:
        out.append(
            f"[{block.owner}/{block.repo}@{block.commit[:12]} {block.display_path} "
            f"lines {format_ranges(block.lines)}]"
        )
        out.extend(block.texts)
    return "\n".join(out)


def environment_passage(
    target: str, blocks: Sequence[EnvironmentBlock], count_tokens: Callable[[str], int]
) -> tuple[str, int]:
    """The environment text and its token count; above ``ENV_MAX_TOKENS`` is refused."""
    text = environment_text(target, blocks)
    tokens = int(count_tokens(text))
    if tokens > ENV_MAX_TOKENS:
        raise ValueError(
            f"environment passage for {target} has {tokens} tokens, above {ENV_MAX_TOKENS}"
        )
    return text, tokens


def latest_timestamp(values: Iterable[str]) -> str:
    items = list(values)
    if not items:
        raise ValueError("no timestamps")
    return max(items, key=lambda v: (datetime.fromisoformat(v), v))


# ------------------------------------------------------------------ §7 entries and pack


def passage_entry(
    *,
    category: str,
    text: str,
    owner: str,
    repo: str,
    commit: str,
    path: str,
    derived: bool,
    start: int,
    end: int,
    version_scope: str,
    label: str | None,
    retrieved_at: str,
    license_expression: str,
    license_evidence: str,
    attribution: str,
) -> dict:
    """A retrieved passage with the twelve source fields in engineering-v1's order."""
    code = CATEGORY_CODES[category]
    display = path + (" (text extraction)" if derived else "")
    url = f"https://github.com/{owner}/{repo}/blob/{commit}/{quote(path, safe='/')}"
    if not derived:
        url += f"#L{start}-L{end}"
    version = f"{version_scope}; {display} lines {start}-{end}"
    if label:
        version += f"; {label}"
    sha = digest(text)
    return dict(
        zip(
            SOURCE_FIELDS,
            (
                f"{code}-p-{sha[:12]}",
                url,
                version,
                retrieved_at,
                license_expression,
                license_evidence,
                attribution,
                f"See {code}-env-v1 for where and how to run, and installed versions.",
                text,
                sha,
                list(ALLOWED_USES),
                EXPORT_PERMISSION,
            ),
            strict=True,
        )
    )


def environment_entry(
    *,
    category: str,
    target: str,
    text: str,
    owner: str,
    repo: str,
    commit: str,
    version_scope: str,
    retrieved_at: str,
    license_expression: str,
    license_evidence: str,
    attribution: str,
) -> dict:
    code = CATEGORY_CODES[category]
    return dict(
        zip(
            SOURCE_FIELDS,
            (
                f"{code}-env-v1",
                f"https://github.com/{owner}/{repo}/tree/{commit}",
                f"{version_scope}; environment passage v1",
                retrieved_at,
                license_expression,
                license_evidence,
                attribution,
                f"This entry is the environment passage for {target}.",
                text,
                digest(text),
                list(ALLOWED_USES),
                EXPORT_PERMISSION,
            ),
            strict=True,
        )
    )


def assemble_pack(
    base: Mapping,
    environment: Mapping[str, Mapping],
    passages: Sequence[tuple[tuple, Mapping]],
    task_passages: Mapping[str, Sequence[str]],
    corpus_manifest_sha256: str,
) -> dict:
    """§7: static entries unchanged, then environment, then retrieved passages; tasks re-ref'd.

    ``passages`` pairs each entry with its sort key (category order, file_index, start, end).
    ``task_passages`` maps a task ID to its retrieved passage IDs in rank order.
    """
    static = [copy.deepcopy(dict(s)) for s in base["sources"]]
    env = [dict(environment[c]) for c in CATEGORIES]
    retrieved: dict[str, tuple[tuple, dict]] = {}
    for key, entry in passages:
        current = retrieved.get(entry["id"])
        if current is not None and current[1] != dict(entry):
            raise ValueError(f"passage ID collision: {entry['id']}")
        retrieved.setdefault(entry["id"], (tuple(key), dict(entry)))
    ordered = [entry for _, entry in sorted(retrieved.values(), key=lambda item: item[0])]
    sources = static + env + ordered
    ids = [s["id"] for s in sources]
    if len(set(ids)) != len(ids):
        raise ValueError("pack source IDs are not unique")
    tasks = []
    for task in base["tasks"]:
        refs = list(task["source_refs"]) + [f"{CATEGORY_CODES[task['category']]}-env-v1"]
        refs += list(task_passages.get(task["id"], ()))
        if not set(refs) <= set(ids):
            raise ValueError(f"task {task['id']} references an unknown source")
        tasks.append(
            {
                "id": task["id"],
                "brief": task["brief"],
                "category": task["category"],
                "source_refs": refs,
            }
        )
    return {
        "schema_version": "1",
        "pack_id": PACK_ID,
        "version": PACK_VERSION,
        "approved_by": PACK_APPROVED_BY,
        "approved_at": PACK_APPROVED_AT,
        "approval_basis": APPROVAL_BASIS_TEMPLATE.replace(
            "{corpus_manifest_sha256}", corpus_manifest_sha256
        ),
        "permission_status": PERMISSION_STATUS,
        "sources": sources,
        "tasks": tasks,
    }


def static_source_spans(pack_text: str) -> list[str]:
    """Byte spans of the first-level ``sources`` entries under the pack serializer."""
    lines = pack_text.split("\n")
    try:
        begin = lines.index('  "sources": [')
    except ValueError as exc:
        raise ValueError("pack text has no sources array") from exc
    spans, current = [], None
    for line in lines[begin + 1 :]:
        if line in ("  ]", "  ],"):
            break
        if line == "    {":
            current = [line]
        elif current is not None:
            if line in ("    }", "    },"):
                current.append("    }")
                spans.append("\n".join(current))
                current = None
            else:
                current.append(line)
    return spans


# ------------------------------------------------------------------ §9 G7 retrieval metrics


def _mean(values: Sequence[float]) -> float | None:
    return round(sum(values) / len(values), SCORE_DECIMALS) if values else None


def recall(identifiers: Sequence[str], passages: Sequence[str]) -> float | None:
    """Share of identifiers that occur exactly in at least one passage text."""
    if not identifiers:
        return None
    found = sum(1 for x in identifiers if any(identifier_in(x, p) for p in passages))
    return found / len(identifiers)


def holdout_line_test(chunks: Sequence[Chunk]) -> dict:
    """Hold out each chunk's heaviest line, query with it, and score hit@3 and MRR."""
    n = len(chunks)
    if not n:
        return {"n": 0, "hits": 0, "hit_at_3": None, "mrr": None}
    base = BM25Index([terms(c.text) for c in chunks])
    k1, b = BM25_K1, BM25_B
    by_file: dict[str, list[int]] = {}
    line_terms: list[dict[int, list[str]]] = []
    for index, chunk in enumerate(chunks):
        by_file.setdefault(chunk.file_key, []).append(index)
        numbers = chunk.live_line_numbers()
        texts = chunk.text.split("\n")
        if len(numbers) != len(texts):
            raise ValueError(f"{chunk.chunk_key}: text lines differ from its live span")
        line_terms.append({k: terms(t) for k, t in zip(numbers, texts, strict=True)})
    total_length = sum(base.length)
    hits, reciprocal = 0, []
    for index, chunk in enumerate(chunks):
        best = None
        for number in sorted(line_terms[index]):
            distinct = sorted(set(line_terms[index][number]))
            if not distinct:
                continue
            weight = round(sum(base.idf(t) for t in distinct), SCORE_DECIMALS)
            if best is None or weight > best[0]:
                best = (weight, number, distinct)
        if best is None:
            reciprocal.append(0.0)
            continue
        _, number, query = best
        changed: dict[int, tuple[Counter, int]] = {}
        df_loss: Counter = Counter()
        for other in by_file[chunk.file_key]:
            if number in line_terms[other]:
                counts = Counter(
                    t for k, ts in sorted(line_terms[other].items()) if k != number for t in ts
                )
                changed[other] = (counts, sum(counts.values()))
                df_loss.update(t for t in base.tf[other] if t not in counts)
        avgdl = (total_length + sum(m - base.length[d] for d, (_, m) in changed.items())) / n
        scores: dict[int, float] = {}
        for term in query:
            dft = base.df.get(term, 0) - df_loss[term]
            if dft <= 0:
                continue
            weight = math.log((n - dft + 0.5) / (dft + 0.5) + 1)
            for doc in base.postings[term]:
                if doc in changed:
                    tf, length = changed[doc][0][term], changed[doc][1]
                else:
                    tf, length = base.tf[doc][term], base.length[doc]
                if not tf:
                    continue
                norm = k1 * (1 - b + b * length / avgdl)
                scores[doc] = scores.get(doc, 0.0) + weight * tf * (k1 + 1) / (tf + norm)
        own = round(scores.get(index, 0.0), SCORE_DECIMALS)
        if own <= 0:
            reciprocal.append(0.0)
            continue
        own_key = (-own, chunk.file_index, chunk.start, chunk.end, chunk.chunk_key)
        better = 0
        for doc, score in scores.items():
            other = chunks[doc]
            key = (
                -round(score, SCORE_DECIMALS),
                other.file_index,
                other.start,
                other.end,
                other.chunk_key,
            )
            better += doc != index and key < own_key
        rank = better + 1
        hits += rank <= 3
        reciprocal.append(1.0 / rank)
    return {
        "n": n,
        "hits": hits,
        "hit_at_3": round(hits / n, SCORE_DECIMALS),
        "mrr": _mean(reciprocal),
    }


def gain_pairs(task_ids: Sequence[str]) -> dict[str, str]:
    """Shuffle pairing within one category: next task in digest order, the last to the first."""
    order = sorted(task_ids, key=lambda t: (digest(GAIN_SHUFFLE_SALT + t), t))
    return {t: order[(i + 1) % len(order)] for i, t in enumerate(order)}


def retrieval_metrics(
    tasks: Sequence[Mapping],
    chunks_by_category: Mapping[str, Sequence[Chunk]],
    blocked_by_category: Mapping[str, Mapping[str, Iterable[int]]],
    selections: Mapping[str, Sequence[Chunk]],
) -> dict:
    """§9 G7: hold-out line test, gain, stability, corpus recall and the combined index.

    ``selections`` maps each task ID to its selected chunks, ``Sel(t)``, in rank order.
    """
    retrievers = {
        c: CategoryRetriever(chunks_by_category.get(c, ()), blocked_by_category.get(c, {}))
        for c in CATEGORIES
    }
    by_category = {c: [t for t in tasks if t["category"] == c] for c in CATEGORIES}
    per_category: dict[str, dict] = {}
    task_rows: dict[str, dict] = {}
    for category in CATEGORIES:
        chunks = list(chunks_by_category.get(category, ()))
        holdout = holdout_line_test(chunks)
        group = by_category[category]
        pairs = gain_pairs([t["id"] for t in group]) if group else {}
        gains, stabilities, recalls, left_out, unstable = [], [], [], [], []
        for task in sorted(group, key=lambda t: t["id"]):
            tid, brief = task["id"], task["brief"]
            own = [c.text for c in selections.get(tid, ())]
            partner = pairs.get(tid)
            identifiers = brief_identifiers(brief)
            row: dict = {"task_id": tid, "partner": partner, "identifiers": identifiers}
            if identifiers:
                partner_texts = [c.text for c in selections.get(partner, ())]
                own_recall = recall(identifiers, own)
                partner_recall = recall(identifiers, partner_texts)
                row.update(
                    recall_own=round(own_recall, SCORE_DECIMALS),
                    recall_partner=round(partner_recall, SCORE_DECIMALS),
                    gain=round(own_recall - partner_recall, SCORE_DECIMALS),
                )
                gains.append(own_recall - partner_recall)
            sentences = brief_sentences(brief)
            own_ids = {passage_id(category, c.text) for c in selections.get(tid, ())}
            if len(sentences) < 2:
                left_out.append(tid)
                row["stability"] = None
            else:
                values, dropped = [], []
                for j in range(len(sentences)):
                    query = " ".join(sentences[:j] + sentences[j + 1 :])
                    chosen = retrievers[category].retrieve(query).selected
                    ids = {passage_id(category, c.text) for c in chosen}
                    union = own_ids | ids
                    values.append(len(own_ids & ids) / len(union) if union else 1.0)
                    dropped.append(sorted(ids))
                stability = sum(values) / len(values)
                stabilities.append(stability)
                row["stability"] = round(stability, SCORE_DECIMALS)
                row["leave_one_sentence_out"] = dropped
                if is_unstable(stability):
                    unstable.append(tid)
            present = [x for x in identifiers if any(identifier_in(x, c.text) for c in chunks)]
            missing = [x for x in identifiers if x not in present]
            recalled = [x for x in present if any(identifier_in(x, p) for p in own)]
            row["corpus_identifiers"] = present
            row["missing_from_corpus"] = missing
            row["present_not_recalled"] = [x for x in present if x not in recalled]
            if present:
                value = len(recalled) / len(present)
                row["corpus_recall"] = round(value, SCORE_DECIMALS)
                recalls.append(value)
            row["passages"] = len(selections.get(tid, ()))
            row["tokens"] = sum(c.qwen_tokens for c in selections.get(tid, ()))
            task_rows[tid] = row
        per_category[category] = {
            "holdout": holdout,
            "gain": _mean(gains),
            "gain_tasks": len(gains),
            "stability": _mean(stabilities),
            "stability_left_out": left_out,
            "stability_below_0_34": unstable,
            "corpus_recall": _mean(recalls),
            "index_chunks": len(chunks),
            "tasks_with_passages": sum(1 for t in group if selections.get(t["id"])),
        }
    combined = _combined_index_check(tasks, chunks_by_category)
    floors = {}
    for category in CATEGORIES:
        values = per_category[category]
        floors[category] = {
            "holdout_hit_at_3": _meets(
                values["holdout"]["hit_at_3"], METRIC_FLOORS["holdout_hit_at_3"]
            ),
            "gain": _meets(values["gain"], METRIC_FLOORS["gain"]),
            "stability": _meets(values["stability"], METRIC_FLOORS["stability"]),
        }
    uneven = {
        "empty_indexes": [c for c in CATEGORIES if not per_category[c]["index_chunks"]],
        "categories_without_passages": [
            c for c in CATEGORIES if not per_category[c]["tasks_with_passages"]
        ],
    }
    uneven["pass"] = not uneven["empty_indexes"] and not uneven["categories_without_passages"]
    return {
        "per_category": per_category,
        "tasks": [task_rows[t["id"]] for t in tasks if t["id"] in task_rows],
        "combined_index": combined,
        "floors": dict(METRIC_FLOORS),
        "floor_results": floors,
        "floors_pass": all(all(v.values()) for v in floors.values()),
        "uneven_treatment": uneven,
    }


def _meets(value: float | None, floor: float) -> bool:
    return value is not None and value >= floor


def _combined_index_check(
    tasks: Sequence[Mapping], chunks_by_category: Mapping[str, Sequence[Chunk]]
) -> dict:
    """Reported only: one index over every category; share of the top four from its own."""
    union = [c for category in CATEGORIES for c in chunks_by_category.get(category, ())]
    if not union:
        return {"per_category": dict.fromkeys(CATEGORIES), "overall": None, "left_out": []}
    retriever = CategoryRetriever(union)
    shares: dict[str, list[float]] = {c: [] for c in CATEGORIES}
    left_out = []
    for task in tasks:
        ranked = retriever.rank(task["brief"])[0]
        positive = [x.chunk for x in ranked if x.r_final > 0][:SELECT_MAX_PASSAGES]
        if not positive:
            left_out.append(task["id"])
            continue
        own = sum(1 for c in positive if c.category == task["category"])
        shares[task["category"]].append(own / len(positive))
    every = [v for c in CATEGORIES for v in shares[c]]
    return {
        "per_category": {c: _mean(shares[c]) for c in CATEGORIES},
        "overall": _mean(every),
        "left_out": left_out,
    }


def tier_shares(passage_tiers: Sequence[str]) -> dict:
    total = len(passage_tiers)
    t1 = sum(1 for t in passage_tiers if t == "T1")
    t2 = sum(1 for t in passage_tiers if t == "T2")
    return {
        "T1": t1,
        "T2": t2,
        "T1_share": round(t1 / total, SCORE_DECIMALS) if total else None,
        "T2_share": round(t2 / total, SCORE_DECIMALS) if total else None,
    }


# ------------------------------------------------------------------ §4.2 rule ADN-1

_ENUM_MEMBER = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+")
_ADN_PAGE = re.compile(r"html/[0-9a-f-]{36}\.htm")


def adn_identifiers(briefs: Sequence[str]) -> list[str]:
    out: list[str] = []
    for brief in briefs:
        for x in brief_identifiers(brief):
            if x not in out:
                out.append(x)
    return out


def adn_keys(identifier: str) -> list[tuple[str, str | None]]:
    """ADN-1 keys for one identifier, each with its dotted-owner filter (or None)."""
    x = identifier
    if _ENUM_MEMBER.fullmatch(x) or x.startswith("OST_"):
        return [(f"{x} enumeration member", None)]
    if x.startswith("get_"):
        return [(f"{x[4:]} property", None)]
    if "." in x:
        member = x.rsplit(".", 1)[1]
        return [(f"{member} method", x), (f"{member} property", x)]
    return [
        (f"{x} {kind}", None)
        for kind in ("class", "interface", "enumeration", "structure", "method", "property")
    ]


class _HHK(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.entries: list[dict] = []
        self.current: dict | None = None

    def handle_starttag(self, tag, attrs):
        values = {k: (v or "") for k, v in attrs}
        if tag == "ul":
            self.depth += 1
        elif tag == "object" and values.get("type", "").lower() == "text/sitemap":
            self.current = {"names": [], "locals": [], "see_also": [], "depth": self.depth}
        elif tag == "param" and self.current is not None:
            name = values.get("name", "").strip().lower()
            if name == "name":
                self.current["names"].append(values.get("value", ""))
            elif name == "local":
                self.current["locals"].append(values.get("value", ""))
            elif name == "see also":
                self.current["see_also"].append(values.get("value", ""))

    def handle_endtag(self, tag):
        if tag == "ul":
            self.depth -= 1
        elif tag == "object" and self.current is not None:
            entry = self.current
            self.current = None
            entry["name"] = entry["names"][0] if entry["names"] else ""
            if entry["depth"] == 1:
                entry["subs"] = []
                self.entries.append(entry)
            elif entry["depth"] == 2 and self.entries:
                self.entries[-1]["subs"].append(entry)


def parse_hhk(text: str) -> list[dict]:
    """Top-level index entries ``{name, locals, see_also, subs}`` of an HTML Help index."""
    parser = _HHK()
    parser.feed(text)
    parser.close()
    return parser.entries


def adn_select(hhk_text: str, briefs: Sequence[str], *, enforce_limits: bool = True) -> dict:
    """ADN-1 member-page selection from the aec_automation briefs and the pinned index."""
    identifiers = adn_identifiers(briefs)
    keys = [key for x in identifiers for key in adn_keys(x)]
    by_name: dict[str, list[dict]] = {}
    for entry in parse_hhk(hhk_text):
        by_name.setdefault(entry["name"].strip().casefold(), []).append(entry)
    pages: set[str] = set()
    unmatched: list[str] = []
    for key, owner in keys:
        matched = by_name.get(key.casefold(), [])
        if not matched:
            unmatched.append(key)
            continue
        for entry in matched:
            locals_ = list(entry["locals"])
            for sub in entry["subs"]:
                if owner is None or sub["name"].startswith(owner + " "):
                    locals_.extend(sub["locals"])
            pages.update("html/2025/" + v for v in locals_ if _ADN_PAGE.fullmatch(v))
    result = {
        "rule": "adn-1",
        "identifiers": identifiers,
        "keys": [key for key, _ in keys],
        "unmatched_keys": unmatched,
        "pages": sorted(pages),
    }
    if enforce_limits and (not pages or len(pages) > ADN_MAX_PAGES):
        raise ValueError(f"ADN-1 selected {len(pages)} pages; an owner decision is needed (OP-5)")
    return result


# ------------------------------------------------------------------ §1.4 input allowlist

TOKENIZER_GGUF = "/home/chadjosewski/models/unsloth__Qwen3-30B-A3B-GGUF/Qwen3-30B-A3B-Q4_K_M.gguf"
TOKENIZER_GGUF_SHA256 = "9f1a24700a339b09c06009b729b5c809e0b64c213b8af5b711b3dbdfd0c5ba48"
_PACKET = "qualification/m4-recovery-contract-followup-20261117/packet-final/sources/"
EVIDENCE_INPUTS = frozenset(
    {
        "aec-course/analysis/source-verification.json",
        "references/engineering-v1.json",
        "references/engineering-v1-approval.json",
        "references/preparation-20261110/provenance.json",
        "references/preparation-20261110/ArcPy-Cheatsheet.pdf",
        _PACKET + "ArcPy-Cheatsheet.txt",
        _PACKET + "arcpy-extraction.json",
    }
)
RUBRIC_V2_SHA256 = "c366ecace6fd663405d8831019d7806b47f27b5ebd71a3d38eb15d2e323b078f"
UPSTREAM_PREFIX = "references/preparation-20261110/upstream/"
REPOSITORY_INPUTS = frozenset(
    {
        "config/aec-course/rag-sources-v1.json",
        "prompts/generator-assessed-v1.md",
        "tools/extract_reference_pdf.py",
    }
)
_REPOSITORY_V3 = re.compile(r"prompts/generator-assessed-v3[^/]*\.md")
CORPUS_FILES = frozenset({"corpus-manifest.json", "chunks.jsonl", "corpus-receipt.json"})
FORBIDDEN_SEGMENTS = frozenset({"assessments", "reviews", "human-review-reports", "labels"})
FORBIDDEN_SEGMENT_PREFIXES = ("human-adjudication", "human-amendments")
FORBIDDEN_NAMES = frozenset(
    {
        "data.jsonl",
        "attempts.jsonl",
        "events.jsonl",
        "gate-items.jsonl",
        "human-labels.jsonl",
        "task-cards.json",
        "task-catalog.json",
    }
)
FORBIDDEN_DIRECTORIES = frozenset({".rag-generator-design-20261120", ".rubric-v2-review-20261120"})


def forbidden_path_reason(parts: Sequence[str], evidence_relative: str | None = None) -> str | None:
    """The §1.4 second guard over path segments, plus the EVID prefixes when under EVID."""
    for part in parts:
        if part in FORBIDDEN_SEGMENTS or part.startswith(FORBIDDEN_SEGMENT_PREFIXES):
            return f"forbidden path segment {part!r}"
        if part in FORBIDDEN_DIRECTORIES:
            return f"forbidden design directory {part!r}"
    if parts and parts[-1] in FORBIDDEN_NAMES:
        return f"forbidden file name {parts[-1]!r}"
    rel = evidence_relative
    if rel is not None:
        head = rel.split("/")
        if len(head) >= 2 and head[0] == "aec-course" and head[1].startswith("api-"):
            return "forbidden evidence area aec-course/api-*"
        if head[0] == "analysis":
            return "forbidden evidence area analysis/"
        if (
            rel.startswith("aec-course/analysis/")
            and rel != "aec-course/analysis/source-verification.json"
        ):
            return "forbidden evidence area aec-course/analysis/"
        if rel.startswith("qualification/") and rel not in EVIDENCE_INPUTS:
            return "forbidden evidence area qualification/"
    return None


def input_path_problem(root: str, path: str) -> str | None:
    """Why a recorded ``{root, path}`` input is not allowed (§1.4), or None."""
    if root == "tokenizer":
        if path != TOKENIZER_GGUF:
            return "tokenizer input is not the pinned GGUF"
        return forbidden_path_reason(path.strip("/").split("/"))
    parts = path.split("/")
    if not path or path.startswith("/") or any(p in ("", ".", "..") for p in parts):
        return f"input path {path!r} is not a clean relative path"
    reason = forbidden_path_reason(parts, path if root == "evidence" else None)
    if reason:
        return reason
    if root == "evidence":
        if path in EVIDENCE_INPUTS:
            return None
        if path.startswith(UPSTREAM_PREFIX) and "/" not in path[len(UPSTREAM_PREFIX) :]:
            return None
        return f"evidence input {path!r} is not on the allowlist"
    if root == "repository":
        if path in REPOSITORY_INPUTS or _REPOSITORY_V3.fullmatch(path):
            return None
        return f"repository input {path!r} is not on the allowlist"
    if root == "tier2":
        if path == "fetch-receipt.json" or path.startswith("files/"):
            return None
        return f"tier-2 input {path!r} is not on the allowlist"
    if root == "corpus":
        if path in CORPUS_FILES:
            return None
        return f"corpus input {path!r} is not on the allowlist"
    return f"unknown input root {root!r}"
