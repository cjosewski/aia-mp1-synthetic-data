"""Synthetic publisher responses; no live network or model requests."""

import hashlib
import sys
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import aec_grounded_docs as reader
import aec_online_docs as legacy


def request(*anchors, page="SearchCursor"):
    return reader.PageRequest(page=page, anchors=list(anchors), claim="Synthetic API claim")


@pytest.fixture
def publisher(monkeypatch):
    calls = []

    def install(body, status=200, content_type="text/plain", error=None):
        @contextmanager
        def fetch(method, url, **options):
            assert method == "GET"
            assert options["follow_redirects"] is False
            assert options["trust_env"] is False
            assert options["timeout"] == 12
            calls.append(url)
            if error is not None:
                raise error
            yield httpx.Response(
                status,
                content=body.encode("utf-8"),
                headers={"Content-Type": content_type, "Location": "https://example.org/redirect"},
                request=httpx.Request(method, url),
            )

        monkeypatch.setattr(reader.httpx, "stream", fetch)
        return calls

    return install


def test_distant_matches_share_budget_and_reproduce_offsets(publisher):
    body = "ßİ " * 1500 + "FIRST_TOKEN " + "x " * 1600 + "SECOND_TOKEN " + "z " * 1500
    body += "THIRD_TOKEN end"
    calls = publisher(body)
    lookup = request("first_token", "second_token", "third_token")
    result = reader.open_page("gis_scripting", lookup)
    assert result["evidence_status"] == "matched"
    assert len(result["excerpts"]) == 3
    assert sum(len(e["text"]) for e in result["excerpts"]) <= 2300
    assert result["body_sha256"] == hashlib.sha256(body.encode()).hexdigest()
    assert result["normalized_text_sha256"] == hashlib.sha256(body.encode()).hexdigest()
    assert "text" not in result  # No full page or concatenation of noncontiguous passages.
    for search, excerpt in zip(result["search_results"], result["excerpts"], strict=True):
        assert body[search["match_start"] : search["match_end"]] == search["anchor"].upper()
        assert excerpt["text"] == body[excerpt["start"] : excerpt["end"]]
        assert search["excerpt_ids"] == [excerpt["id"]]
        assert search["anchor"].upper() in excerpt["text"]
    replay = reader.open_page("gis_scripting", lookup)
    for key in ("excerpts", "search_results", "body_sha256", "normalized_text_sha256"):
        assert replay[key] == result[key]
    assert len(calls) == 2  # One fetch per invocation, independent of anchor count.


def test_miss_is_unresolved_without_unrelated_page_head(publisher):
    body = "Unrelated publisher introduction. " * 200
    publisher(body)
    result = reader.open_page("gis_scripting", request("missing API", "also absent"))
    assert result["evidence_status"] == "unresolved"
    assert result["excerpts"] == []
    assert "text" not in result
    assert result["normalized_text_chars"] == len(body.rstrip())
    for search in result["search_results"]:
        assert search["matched"] is False
        assert search["match_start"] is search["match_end"] is None
        assert search["excerpt_ids"] == []
        assert search["occurrence_count"] == 0


def test_partial_match_records_each_miss_and_merges_overlap(publisher):
    publisher("intro " * 70 + "VALID_ONE paired VALID_TWO " + "tail " * 80)
    result = reader.open_page("gis_scripting", request("VALID_ONE", "MISSING", "VALID_TWO"))
    assert result["evidence_status"] == "partial"
    assert len(result["excerpts"]) == 1
    excerpt = result["excerpts"][0]
    assert excerpt["anchors"] == ["VALID_ONE", "VALID_TWO"]
    assert len(excerpt["text"]) <= 2300
    assert result["search_results"][1]["excerpt_ids"] == []
    assert result["search_results"][0]["excerpt_ids"] == ["E1"]
    assert result["search_results"][2]["excerpt_ids"] == ["E1"]


def test_literal_not_regex_and_long_anchor_at_document_end(publisher):
    long_anchor = "long" + "x" * 86
    body = "preamble " * 400 + "a.*b " + "tail " * 400 + long_anchor
    publisher(body)
    result = reader.open_page("gis_scripting", request("a.*b", long_anchor, "a.+b"))
    assert result["evidence_status"] == "partial"
    assert result["search_results"][2]["matched"] is False
    assert result["excerpts"][-1]["end"] == len(body)
    assert long_anchor in result["excerpts"][-1]["text"]


def test_repeated_anchor_discloses_first_occurrence_selection(publisher):
    publisher("first MATCH " + "intermediate " * 300 + "last MATCH")
    result = reader.open_page("gis_scripting", request("MATCH"))
    assert result["search_results"][0]["occurrence_count"] == 2
    assert result["search_results"][0]["match_start"] == 6
    assert "last MATCH" not in result["excerpts"][0]["text"]
    assert result["search_strategy"] == "first case-insensitive literal occurrence per anchor"


def test_html_hides_navigation_and_preserves_untrusted_code_as_text(publisher):
    body = (
        "<html><head><title>HIDDEN</title></head><body><nav>HIDDEN</nav>"
        "<script>HIDDEN; do_not_execute()</script><p>   visible   prose </p>"
        "<pre>dangerous_call(&quot;UNTRUSTED&quot;)</pre><p>"
        + "padding " * 20
        + "</p></body></html>"
    )
    publisher(body, content_type="text/html; charset=utf-8")
    result = reader.open_page("gis_scripting", request("HIDDEN", "UNTRUSTED"))
    assert result["evidence_status"] == "partial"
    text = result["excerpts"][0]["text"]
    assert text.startswith("visible prose\n")
    assert 'dangerous_call("UNTRUSTED")' in text
    assert "HIDDEN" not in text
    assert result["body_sha256"] != result["normalized_text_sha256"]


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/manual",
        "https://pro.arcgis.com/en/pro-app/3.5/arcpy/searchcursor.htm",
        "https://pro.arcgis.com/en/pro-app/3.6/../3.5/manual",
        "https://pro.arcgis.com/en/pro-app/3.6/%2e%2e/private",
        "https://pro.arcgis.com/en/pro-app/3.6/manual?q=secret",
        "https://pro.arcgis.com/en/pro-app/3.6/manual#fragment",
        "https://pro.arcgis.com@attacker.test/en/pro-app/3.6/manual",
        "https://pro.arcgis.com.evil.test/en/pro-app/3.6/manual",
        "https://pro.arcgis.com:8443/en/pro-app/3.6/manual",
        "http://pro.arcgis.com/en/pro-app/3.6/manual",
        "https://[invalid",
    ],
)
def test_disallowed_urls_never_fetch(monkeypatch, url):
    monkeypatch.setattr(reader.httpx, "stream", lambda *a, **k: pytest.fail("Unexpected fetch"))
    result = reader.open_page("gis_scripting", request("anchor", page=url))
    assert result["evidence_status"] == "error"
    assert result["excerpts"] == []
    assert result["search_results"] == []


def test_unknown_category_stays_local(monkeypatch):
    monkeypatch.setattr(reader.httpx, "stream", lambda *a, **k: pytest.fail("Unexpected fetch"))
    result = reader.open_page("unknown", request("anchor"))
    assert result["evidence_status"] == "error"


@pytest.mark.parametrize("status", [301, 302, 307, 404, 500])
def test_http_failures_and_redirects_return_no_passage(publisher, status):
    calls = publisher("anchor " * 100, status=status)
    result = reader.open_page("gis_scripting", request("anchor"))
    assert result["evidence_status"] == "error"
    assert result["http_status"] == status
    assert result["excerpts"] == []
    assert len(calls) == 1


def test_timeout_is_explicit_failure_without_excerpt(publisher):
    publisher("", error=httpx.ReadTimeout("Synthetic timeout"))
    result = reader.open_page("gis_scripting", request("anchor"))
    assert result["evidence_status"] == "error"
    assert "timeout" in result["error"]
    assert result["excerpts"] == []


def test_byte_bound_rejects_oversize_body(publisher):
    publisher("a" * 3_000_001)
    result = reader.open_page("gis_scripting", request("aaa"))
    assert result["evidence_status"] == "error"
    assert "byte limit" in result["error"]
    assert result["excerpts"] == []


def test_stream_total_time_bound(publisher, monkeypatch):
    publisher("anchor " * 100)
    clock = iter([0, 25])
    monkeypatch.setattr(reader.time, "monotonic", lambda: next(clock, 25))
    result = reader.open_page("gis_scripting", request("anchor"))
    assert "total reader time limit" in result["error"]
    assert result["excerpts"] == []


def test_elapsed_limit_checks_small_transport_chunks(monkeypatch):
    elapsed = [0]

    class SlowStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b"first chunk "
            elapsed[0] = 25
            yield b"second chunk "
            pytest.fail("Reader buffered small chunks past its elapsed-time check")

    @contextmanager
    def fetch(method, url, **options):
        response = httpx.Response(200, stream=SlowStream(), request=httpx.Request(method, url))
        try:
            yield response
        finally:
            response.close()

    monkeypatch.setattr(reader.httpx, "stream", fetch)
    monkeypatch.setattr(reader.time, "monotonic", lambda: elapsed[0])
    result = reader.open_page("gis_scripting", request("chunk"))
    assert "total reader time limit" in result["error"]
    assert result["excerpts"] == []


def test_unreadable_body_is_error_not_search_miss(publisher):
    publisher("short")
    result = reader.open_page("gis_scripting", request("short"))
    assert result["evidence_status"] == "error"
    assert result["search_results"] == []


@pytest.mark.parametrize("anchors", [[], [" "], ["x" * 91], ["x"] * 2, ["x", "X"], list("abcd")])
def test_anchor_limits(anchors):
    with pytest.raises(ValidationError):
        request(*anchors)


def test_lookup_limits_and_duplicate_document_alias():
    with pytest.raises(ValidationError):
        reader.Lookup(pages=[])
    with pytest.raises(ValidationError):
        reader.Lookup(pages=[request("anchor", page=str(i)) for i in range(4)])
    with pytest.raises(ValidationError, match="one request per document"):
        reader.Lookup(
            pages=[
                request("one"),
                request("two", page=reader.PAGES["gis_scripting"]["SearchCursor"]),
            ]
        )
    assert len(reader.Lookup(pages=[request("a"), request("b", page="Describe")]).pages) == 2


def test_new_catalog_is_independent_and_keeps_edition_labels(publisher):
    assert reader.PAGES is not legacy.PAGES
    assert reader.PAGES["cad_apis"] is not legacy.PAGES["cad_apis"]
    assert "Units" not in legacy.PAGES["aec_automation"]
    assert "Cone constructor at 1.0.2" not in legacy.PAGES["cad_apis"]
    publisher("synthetic constructor documentation " * 3)
    pinned = reader.open_page("cad_apis", request("constructor", page="Cone constructor at 1.0.2"))
    current = reader.open_page(
        "cad_apis", request("constructor", page="Cone (project manual, current)")
    )
    assert pinned["evidence_status"] == current["evidence_status"] == "matched"
    assert "pinned" in pinned["edition"]
    assert "current manual" in current["edition"]
