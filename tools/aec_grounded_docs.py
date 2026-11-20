"""Bounded literal document lookup for a new development protocol.

Matches locate text; they do not verify claims. Offsets index normalized Python
strings, and only selected excerpts (never the full page) are returned.
"""

import hashlib
import re
import time
from html.parser import HTMLParser
from typing import Annotated
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from aia_mp1.tracing import now

ARCPY = "https://pro.arcgis.com/en/pro-app/3.6/arcpy/"
REVIT = "https://help.autodesk.com/cloudhelp/2025/ENU/Revit-API/"
BASIC = REVIT + "files/Revit_API_Developers_Guide/Basic_Interaction_with_Revit_Elements/"
GUIDE = "Revit_API_Revit_API_Developers_Guide_Basic_Interaction_with_Revit_Elements_"
SCIPY = "https://docs.scipy.org/doc/scipy-1.16.1/"
RAW = "https://raw.githubusercontent.com/"
FREECAD = RAW + "FreeCAD/FreeCAD/256fc7eff3379911ab5daf88e10182c509aa8052/"
FC_MANUAL = RAW + "FreeCAD/FreeCAD-documentation/main/wiki/"
OPENSEES = RAW + "zhuminjie/OpenSeesPyDoc/ce0d8f1ded3c722119c44d5b3a2073c9dce47828/src/"

PAGES = {
    "gis_scripting": {
        "SearchCursor": ARCPY + "data-access/searchcursor-class.htm",
        "InsertCursor": ARCPY + "data-access/insertcursor-class.htm",
        "SpatialReference": ARCPY + "classes/spatialreference.htm",
        "Describe": ARCPY + "functions/describe.htm",
        "CreateFeatureclass": "https://pro.arcgis.com/en/pro-app/3.6/tool-reference/data-management/create-feature-class.htm",
        "AddField": "https://pro.arcgis.com/en/pro-app/3.6/tool-reference/data-management/add-field.htm",
    },
    "aec_automation": {
        "Parameter storage and accessors": BASIC
        + "Parameters/"
        + GUIDE
        + "Parameters_Parameter_html.html",
        "Filtering": BASIC + GUIDE + "Filtering_html.html",
        "Applying filters": BASIC + "Filtering/" + GUIDE + "Filtering_Applying_Filters_html.html",
    },
    "structural_analysis": {
        name: OPENSEES + name + ".rst"
        for name in (
            "model",
            "node",
            "nodeDisp",
            "fix",
            "load",
            "timeSeries",
            "linearTs",
            "pattern",
            "plainPattern",
            "analyze",
        )
    },
    "cad_apis": {
        "Cone (project manual, current)": FC_MANUAL + "Part_Cone.md",
        "Box (project manual, current)": FC_MANUAL + "Part_Box.md",
        "Topological data scripting (project manual, current)": FC_MANUAL
        + "Topological_data_scripting.md",
        "Part object examples at 1.0.2": FREECAD + "src/Mod/Part/parttests/part_test_objects.py",
        "Shape examples at 1.0.2": FREECAD + "src/Mod/Part/parttests/TopoShapeTest.py",
    },
    "simulation": {
        "solve_ivp": SCIPY + "reference/generated/scipy.integrate.solve_ivp.html",
        "RK45": SCIPY + "reference/generated/scipy.integrate.RK45.html",
        "OdeSolver": SCIPY + "reference/generated/scipy.integrate.OdeSolver.html",
    },
}
ROOTS = {
    "gis_scripting": ("https://pro.arcgis.com/en/pro-app/3.6/",),
    "aec_automation": (
        REVIT,
        "https://help.autodesk.com/cloudhelp/2025/ENU/Revit-API-MainReference/",
    ),
    "simulation": (SCIPY,),
    "cad_apis": (FREECAD, FC_MANUAL),
    "structural_analysis": (OPENSEES,),
}

PAGES["aec_automation"]["Units"] = (
    REVIT
    + "files/Revit_API_Developers_Guide/Introduction/Application_and_Document/"
    + "Revit_API_Revit_API_Developers_Guide_Introduction_Application_and_Document_Units_html.html"
)
PAGES["cad_apis"]["Cone constructor at 1.0.2"] = FREECAD + "src/Mod/Part/App/ConePyImp.cpp"

MAX_BODY_BYTES = 3_000_000
MAX_EXCERPT_CHARS = 2300
REQUEST_TIMEOUT_SECONDS = 12
# Checked between transport chunks; an in-flight read can add one read timeout.
MAX_READ_SECONDS = 24
Anchor = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=90)]


class PageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: str = Field(min_length=1, max_length=700)
    anchors: list[Anchor] = Field(min_length=1, max_length=3)
    claim: str = Field(min_length=1, max_length=300)

    @field_validator("page", "claim")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Must not be blank")
        return value.strip()

    @field_validator("anchors")
    @classmethod
    def distinct_anchors(cls, value):
        if len({anchor.casefold() for anchor in value}) != len(value):
            raise ValueError("Search anchors must be distinct")
        return value


class Lookup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pages: list[PageRequest] = Field(min_length=1, max_length=3)

    @field_validator("pages")
    @classmethod
    def distinct_pages(cls, value):
        aliases = {name: url for menu in PAGES.values() for name, url in menu.items()}
        resolved = [aliases.get(request.page, request.page) for request in value]
        if len(set(resolved)) != len(resolved):
            raise ValueError("Use at most three anchors in one request per document")
        return value


class VisibleText(HTMLParser):
    """Strip markup and navigation; preserve code text as untrusted text."""

    hidden_tags = {"script", "style", "nav", "noscript", "footer", "header", "head"}
    block_tags = {"p", "div", "li", "dt", "dd", "h1", "h2", "h3", "tr", "pre", "br"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.hidden_tags:
            self.hidden += 1
        if not self.hidden and tag in self.block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.hidden_tags:
            self.hidden = max(0, self.hidden - 1)
        if not self.hidden and tag in self.block_tags:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _passages(text, anchors):
    searches = []
    for anchor in anchors:
        first = None
        count = 0
        # Regex offsets index the original string even for Unicode case mappings.
        for match in re.finditer(re.escape(anchor), text, flags=re.IGNORECASE):
            if first is None:
                first = match
            count += 1
        searches.append(
            {
                "anchor": anchor,
                "matched": first is not None,
                "match_start": first.start() if first else None,
                "match_end": first.end() if first else None,
                "occurrence_count": count,
                "excerpt_ids": [],
            }
        )
    found = [search for search in searches if search["matched"]]
    windows = []
    for index, search in enumerate(found):
        budget = MAX_EXCERPT_CHARS // len(found) + (index < MAX_EXCERPT_CHARS % len(found))
        start = max(0, search["match_start"] - min(450, budget // 3))
        end = min(len(text), start + budget)
        start = max(0, end - budget)
        windows.append((start, end))
    merged = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    excerpts = []
    for index, (start, end) in enumerate(merged, 1):
        excerpt_id = f"E{index}"
        covered = [
            search
            for search in found
            if start <= search["match_start"] and search["match_end"] <= end
        ]
        for search in covered:
            search["excerpt_ids"].append(excerpt_id)
        excerpts.append(
            {
                "id": excerpt_id,
                "start": start,
                "end": end,
                "text": text[start:end],
                "anchors": [search["anchor"] for search in covered],
            }
        )
    status = "matched" if len(found) == len(anchors) else "partial" if found else "unresolved"
    return {"search_results": searches, "excerpts": excerpts, "evidence_status": status}


def open_page(category, request):
    """Fetch one allowed edition once; record misses without substituting page heads."""
    url = PAGES.get(category, {}).get(request.page, request.page)
    result = {
        "request": request.model_dump(),
        "url": url,
        "opened_at": now(),
        "evidence_status": "error",
        "search_results": [],
        "excerpts": [],
    }
    try:
        parts = urlsplit(url)
        if (
            not any(url.startswith(base) for base in ROOTS.get(category, ()))
            or parts.query
            or parts.fragment
            or not re.fullmatch(r"[A-Za-z0-9/_.~()-]+", parts.path)
            or any(segment in (".", "..") for segment in parts.path.split("/"))
        ):
            raise ValueError("Unknown page or outside the permitted documentation edition")
        result["edition"] = (
            "current manual, confirm version-specific claims with 1.0.2 source"
            if url.startswith(FC_MANUAL)
            else "target edition or pinned upstream revision"
        )
        deadline = time.monotonic() + MAX_READ_SECONDS
        with httpx.stream(
            "GET",
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": "AEC-grounded-documentation-reader/1.0"},
        ) as response:
            result["http_status"] = response.status_code
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                if time.monotonic() > deadline:
                    raise ValueError("Page exceeded total reader time limit")
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    raise ValueError("Page exceeds reader byte limit")
                body.extend(chunk)
            text = body.decode(response.encoding or "utf-8", errors="replace")
            if "html" in response.headers.get("Content-Type", "").lower():
                reader = VisibleText()
                reader.feed(text)
                reader.close()
                text = "".join(reader.parts)
        text = "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())
        if len(text) < 50:
            raise ValueError("Page has no readable documentation")
        return result | {
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "normalized_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "normalized_text_chars": len(text),
            "search_strategy": "first case-insensitive literal occurrence per anchor",
            **_passages(text, request.anchors),
        }
    except (httpx.HTTPError, ValueError, LookupError) as error:
        return result | {"error": str(error)}
