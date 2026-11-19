import sys
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from aec_online_docs import PAGES, Lookup, PageRequest, open_page
from screen_aec_online_docs import read_pages


def test_lookup_reads_requested_publisher_passage_and_replays_offline(monkeypatch, tmp_path):
    url = PAGES["gis_scripting"]["SearchCursor"]
    calls = []
    body = (
        "<script>irrelevant hidden text</script><p>"
        + "intro " * 580
        + "</p><p>field order follows the caller</p>"
    )

    @contextmanager
    def fetch(method, target, **options):
        assert method == "GET" and target == url
        assert options["follow_redirects"] is False
        calls.append(target)
        yield httpx.Response(
            200,
            text=body,
            headers={"Content-Type": "text/html"},
            request=httpx.Request(method, target),
        )

    monkeypatch.setattr("aec_online_docs.httpx.stream", fetch)
    lookup = Lookup(
        pages=[
            PageRequest(page="SearchCursor", find="field order", claim="Check the cursor order.")
        ]
    )
    (tmp_path / "protocol.json").write_text("{}")
    opened = read_pages(tmp_path, "case", "gis_scripting", lookup, False)
    assert opened[0]["find_matched"] and opened[0]["start"] > 0
    assert "field order follows the caller" in opened[0]["text"]
    assert "hidden text" not in opened[0]["text"]
    assert read_pages(tmp_path, "case", "gis_scripting", lookup, True) == opened
    assert calls == [url]
    lookup.pages[0].find = "different term"
    with pytest.raises(ValueError, match="history differs"):
        read_pages(tmp_path, "case", "gis_scripting", lookup, True)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/manual",
        "https://pro.arcgis.com/en/pro-app/3.5/arcpy/data-access/searchcursor-class.htm",
        "https://pro.arcgis.com/en/pro-app/3.6/../3.5/page.htm",
        "https://pro.arcgis.com/en/pro-app/3.6/arcpy/?q=anything",
        "https://pro.arcgis.com/en/pro-app/3.6/%2e%2e/private",
    ],
)
def test_out_of_scope_requests_stay_local(monkeypatch, url):
    monkeypatch.setattr(
        "aec_online_docs.httpx.stream", lambda *a, **k: pytest.fail("Unexpected HTTP request")
    )
    response = open_page("gis_scripting", PageRequest(page=url, find="", claim="Look up an API"))
    assert "error" in response and "text" not in response
