"""Read individual publisher pages on demand for the AEC documentation comparison."""

import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field

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


class PageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: str = Field(min_length=1, max_length=700)
    find: str = Field(max_length=90)
    claim: str = Field(min_length=1, max_length=300)


class Lookup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pages: list[PageRequest] = Field(min_length=1, max_length=3)


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "noscript", "footer", "header"}:
            self.hidden += 1
        if tag in {"p", "div", "li", "dt", "dd", "h1", "h2", "h3", "tr", "pre", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "noscript", "footer", "header"}:
            self.hidden = max(0, self.hidden - 1)
        if tag in {"p", "li", "dt", "dd", "pre", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def open_page(category, request):
    url = PAGES[category].get(request.page, request.page)
    result = {"request": request.model_dump(), "url": url, "opened_at": now()}
    parts = urlsplit(url)
    if (
        not any(url.startswith(base) for base in ROOTS[category])
        or parts.query
        or parts.fragment
        or not re.fullmatch(r"[A-Za-z0-9/_.~()-]+", parts.path)
        or any(s in (".", "..") for s in parts.path.split("/"))
    ):
        return result | {"error": "Unknown page or outside the permitted documentation edition"}
    try:
        with httpx.stream(
            "GET",
            url,
            timeout=12,
            follow_redirects=False,
            headers={"User-Agent": "AEC-documentation-reader/1.0"},
        ) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 3_000_000:
                    raise ValueError("Page exceeds reader limit")
            text = body.decode(response.encoding or "utf-8", errors="replace")
            if "html" in response.headers.get("Content-Type", "").lower():
                reader = VisibleText()
                reader.feed(text)
                text = "".join(reader.parts)
        text = "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())
        if len(text) < 50:
            raise ValueError("Page has no readable documentation")
        pos = text.casefold().find(request.find.casefold()) if request.find else 0
        start = max(0, pos - 450)
        return result | {
            "http_status": 200,
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "find_matched": pos >= 0,
            "start": start,
            "text": text[start : start + 2300],
            "edition": "current manual, confirm version-specific claims with 1.0.2 source"
            if url.startswith(FC_MANUAL)
            else "target edition or pinned upstream revision",
        }
    except (httpx.HTTPError, ValueError) as error:
        return result | {"error": str(error)}
