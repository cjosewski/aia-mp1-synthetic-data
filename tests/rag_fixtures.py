"""Entirely synthetic retrieval-pack inputs, built only in temporary test directories.

``make_world`` writes a miniature evidence tree (tier-1 snapshots, source verification,
provenance, cheat-sheet extraction and a base pack), a repository root holding a synthetic
admission table, and a tier-2 fetch directory with its receipt. Nothing here is upstream
text; every name, notice and license line is invented for tests.
"""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from aia_mp1 import retrieval as r

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "tools") not in sys.path:
    sys.path.insert(0, str(REPO / "tools"))

TOKENIZER = {
    "gguf_sha256": "0" * 64,
    "chat_template_sha256": "1" * 64,
    "vocabulary_digest": "2" * 64,
    "synthetic": True,
}
FETCHED_AT = "2026-11-21T00:00:00+00:00"
PREPARED_AT = "2026-11-10T00:00:00+00:00"
TBC_ALIAS = "c" * 40
PAGE_1 = "html/11111111-1111-1111-1111-111111111111.htm"
PAGE_2 = "html/22222222-2222-2222-2222-222222222222.htm"
PAGE_3 = "html/33333333-3333-3333-3333-333333333333.htm"


def words(text: str) -> int:
    return len(text.split())


def _commit(n: int) -> str:
    return f"{n:x}" * 40


def _lines(*lines: str) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


CHEAT_SHEET = _lines(
    "ArcPy Cheat Sheet (synthetic)",
    "Cursors",
    "Use arcpy.da.SearchCursor(fc, ['OID@', 'SHAPE@XY']) to read rows.",
    "Close the cursor with a with block.",
    "Installing ArcPy The ArcPy package ships with the synthetic desktop.",
    "import arcpy",
    "Copyright © 2025 Synthetic Mapping Co. All rights reserved.",
    "Other marks belong to their respective mark owners.",
    "Geometry",
    "arcpy.Polyline(arcpy.Array([arcpy.Point(0, 0), arcpy.Point(1, 1)]), sr)",
)

SANDCASTLE_PAGE = (
    "<html><head><title>{title}</title></head><body>"
    '<div id="PageHeader">Synthetic API</div>'
    "<h1>{title}</h1><p>{summary}</p>"
    '<div class="codeSnippetContainerTabs"><div id="X_tab1"><a href="#">C#</a></div></div>'
    '<div class="codeSnippetContainerCode" id="X_code_Div1"><pre>{code}</pre></div>'
    '<div id="PageFooter">Synthetic footer</div></body></html>'
)

HHK = """<HTML><BODY>
<UL>
<LI> <OBJECT type="text/sitemap">
  <param name="Name" value="FilteredElementCollector class">
  <param name="Local" value="{p1}">
  </OBJECT>
<LI> <OBJECT type="text/sitemap">
  <param name="Name" value="GetElement method">
  </OBJECT>
  <UL>
  <LI> <OBJECT type="text/sitemap">
    <param name="Name" value="Document.GetElement Method (ElementId)">
    <param name="Local" value="{p2}">
    </OBJECT>
  <LI> <OBJECT type="text/sitemap">
    <param name="Name" value="Other.GetElement Method">
    <param name="Local" value="{p3}">
    </OBJECT>
  </UL>
</UL>
</BODY></HTML>
""".format(p1=PAGE_1, p2=PAGE_2, p3=PAGE_3)

REGENTS_HTML = (
    "<html><body><pre><span></span>Copyright @ 1999-2020 The Regents of the University of "
    "California (The Regents).\nAll Rights Reserved.\nThe above copyright notice must appear in\n"
    "all copies of the synthetic documentation.\nSYNTHETIC CLOSING LINE TO BENEFIT THE END USER.\n"
    "Trailing text that is not part of the notice.\n</pre></body></html>\n"
)


def _spec(path, roles, tier, decision, content, **extra):
    return {
        "path": path,
        "roles": roles,
        "tier": tier,
        "decision_id": decision,
        "_content": content,
        **extra,
    }


def _repositories() -> list[dict]:
    arcpy = {
        "repo_key": "arcpy",
        "owner": "synthetic-esri",
        "repo": "arcpy",
        "commit": _commit(1),
        "ref": {"kind": "head"},
        "category": "gis_scripting",
        "tiers": ["T1", "T2"],
        "decision_ids": ["G1"],
        "license_expression": "Apache-2.0",
        "version_scope": "Synthetic desktop 3.6",
        "attribution": {
            "passage": "Synthetic Mapping Co. (Apache-2.0). Cheat sheet notice: {NOTICE}",
            "environment": "Synthetic Mapping Co. environment. Cheat sheet notice: {NOTICE}",
        },
        "files": [
            _spec(
                "LICENSE.txt",
                ["license"],
                "T1",
                "G1",
                _lines("Apache License", "Version 2.0, synthetic copy"),
            ),
            _spec(
                "docs/ArcPy-Cheatsheet.pdf",
                ["passage"],
                "T1",
                "G1",
                b"%PDF-1.4\n% synthetic cheat sheet bytes\n",
                mode="lines",
                derived="pdf_text",
                notice_block_lines=[7, 8],
            ),
            _spec(
                "docs/arcgis-dist.json",
                ["environment"],
                "T2",
                "G1",
                _lines(
                    "{",
                    '  "3.6": {',
                    '    "arcgispro": "3.6",',
                    '    "arcpy": "3.6",',
                    '    "python": "3.13.7"',
                    "  }",
                    "}",
                ),
            ),
        ],
        "globs": [],
    }
    route_tools = _lines(
        "# Copyright 2024 Synthetic Mapping Co.",
        "# Licensed under the Apache License, Version 2.0",
        "",
        "import arcpy",
        "",
        "",
        "def list_routes(workspace):",
        '    """Return route feature classes from arcpy.ListFeatureClasses in a workspace."""',
        "    arcpy.env.workspace = workspace",
        "    # arcpy.env.overwriteOutput = True",
        '    return arcpy.ListFeatureClasses("route*")',
    )
    ptt = {
        "repo_key": "ptt",
        "owner": "synthetic-esri",
        "repo": "transit-tools",
        "commit": _commit(2),
        "ref": {"kind": "head", "recorded_branch": "main"},
        "category": "gis_scripting",
        "tiers": ["T2"],
        "decision_ids": ["G2"],
        "license_expression": "Apache-2.0",
        "version_scope": "Synthetic samples, unpinned",
        "attribution": {"passage": "Synthetic, {owner}/{repo} (Apache-2.0).{HEADER}"},
        "files": [
            _spec("License.txt", ["license"], "T2", "G2", _lines("Apache License 2.0 synthetic")),
            _spec("README.md", ["evidence"], "T2", "G2", _lines("# Synthetic transit tools")),
        ],
        "globs": [
            {
                "patterns": ["*.py", "*.pyt"],
                "any_depth": True,
                "roles": ["passage"],
                "mode": "lines",
                "tier": "T2",
                "decision_id": "G2",
                "rules": ["AR-3", "AR-4"],
                "listed_count": 6,
                "_files": {
                    "transit/route_tools.py": route_tools,
                    "legacy/old_tool.py": _lines("print 'python 2 only'"),
                    "legacy/map_tool.py": _lines("import arcpy.mapping", "x = 1"),
                    "unittests/portal_credentials.py": _lines("USER = 'synthetic'"),
                    "RevitSdkSamples/sample.py": _lines("x = 1"),
                    "tools/convert.pyt": _lines(
                        "import arcpy",
                        "",
                        "",
                        "class Toolbox:",
                        '    """A synthetic toolbox that reads OID@ with SearchCursor."""',
                        "    label = 'Convert'",
                    ),
                },
            }
        ],
    }
    walls = _lines(
        "#region Header",
        "//",
        "// CmdListWalls.cs - list walls (synthetic)",
        "//",
        "// Copyright (C) 2009-2021 by Synthetic Tammik,",
        "// Example Inc. All rights reserved.",
        "//",
        "#endregion // Header",
        "",
        "using Autodesk.Revit.DB;",
        "",
        "namespace BuildingCoder",
        "{",
        "    class CmdListWalls : IExternalCommand",
        "    {",
        "        public Result Execute(ExternalCommandData data)",
        "        {",
        "            var doc = data.Application.ActiveUIDocument.Document;",
        "            var walls = new FilteredElementCollector(doc).OfClass(typeof(Wall));",
        "            //var old = doc.Elements;",
        "            foreach (Wall w in walls) { Debug.Print(w.Name); }",
        "            return Result.Succeeded;",
        "        }",
        "    }",
        "}",
    )
    bbox = _lines(
        "using Autodesk.Revit.DB;",
        "",
        "namespace BuildingCoder",
        "{",
        "    /* Old approach:",
        "    var b = e.BoundingBox[null];",
        "    */",
        "    class CmdBoundingBox : IExternalCommand",
        "    {",
        "        BoundingBoxXYZ Get(Element e, View v) { return e.get_BoundingBox(v); }",
        "    }",
        "}",
    )
    csproj = (
        '<Project Sdk="Microsoft.NET.Sdk">\r\n  <PropertyGroup>\r\n'
        "    <TargetFramework>net8.0-windows</TargetFramework>\r\n  </PropertyGroup>\r\n"
        '  <ItemGroup>\r\n    <Compile Remove="CmdRemoved.cs" />\r\n'
        '    <Compile Update="Properties\\Settings.Designer.cs" />\r\n  </ItemGroup>\r\n'
        "</Project>\r\n"
    ).encode("utf-8")
    tbc = {
        "repo_key": "tbc2025",
        "owner": "synthetic-tammik",
        "repo": "building-coder",
        "commit": _commit(3),
        "ref": {"kind": "tag", "name": "2025.0.1", "annotated": False},
        "category": "aec_automation",
        "tiers": ["T1", "T2"],
        "decision_ids": ["A1"],
        "license_expression": "MIT",
        "version_scope": "Synthetic Revit 2025 samples",
        "attribution": {"passage": "Synthetic Tammik samples (MIT).{HEADER}"},
        "files": [
            _spec(
                "License.md",
                ["license"],
                "T1",
                "A1",
                _lines("MIT License", "Copyright (c) 2013 Synthetic Tammik"),
            ),
            _spec(
                "Readme.md",
                ["environment"],
                "T1",
                "A1",
                _lines("# Building Coder (synthetic)", "Revit API 2025", "Windows .NET 8"),
            ),
            _spec(
                "BuildingCoder/BuildingCoder.csproj", ["environment", "index"], "T2", "A1", csproj
            ),
            _spec(
                "BuildingCoder/TheBuildingCoderSingleSample.addin",
                ["environment"],
                "T2",
                "A1",
                '﻿<?xml version="1.0" encoding="utf-8"?>\n<RevitAddIns>\n'
                '  <AddIn Type="Command" />\n</RevitAddIns>\n'.encode("utf-8"),
            ),
            _spec("BuildingCoder/CmdListWalls.cs", ["passage"], "T1", "A1", walls, mode="lines"),
        ],
        "globs": [
            {
                "patterns": ["BuildingCoder/*.cs"],
                "any_depth": False,
                "roles": ["passage"],
                "mode": "lines",
                "tier": "T2",
                "decision_id": "A1",
                "rules": ["AR-5"],
                "listed_count": 3,
                "_files": {
                    "BuildingCoder/CmdBoundingBox.cs": bbox,
                    "BuildingCoder/CmdRemoved.cs": _lines("class CmdRemoved {}"),
                },
            }
        ],
    }
    page_1 = SANDCASTLE_PAGE.format(
        title="FilteredElementCollector Class",
        summary="This class is used to search, filter and iterate a set of elements.",
        code="public class FilteredElementCollector : IEnumerable&lt;Element&gt;",
    )
    page_2 = SANDCASTLE_PAGE.format(
        title="Document.GetElement Method (ElementId)",
        summary="Gets the Element referenced by the input ElementId.",
        code="public Element GetElement(ElementId id)",
    )
    adn = {
        "repo_key": "adn2025",
        "owner": "synthetic-adn",
        "repo": "api-help",
        "commit": _commit(4),
        "ref": {"kind": "head"},
        "category": "aec_automation",
        "tiers": ["T2"],
        "decision_ids": ["A2"],
        "license_expression": "MIT",
        "version_scope": "Synthetic Revit 2025 API reference",
        "attribution": {"passage": "Synthetic API reference pages (MIT)."},
        "license_judgment": {
            "by": "Synthetic owner",
            "date": "2026-11-20",
            "statement": "synthetic judgment",
            "caveat": "synthetic caveat",
        },
        "files": [
            _spec("LICENSE", ["license"], "T2", "A2", _lines("MIT License", "Copyright (c) 2021")),
            _spec("README.md", ["evidence"], "T2", "A2", _lines("Synthetic help files.")),
            _spec("html/2025/RevitAPI.hhk", ["index"], "T2", "A2", HHK.encode("utf-8")),
        ],
        "globs": [
            {
                "patterns": ["html/2025/html/*.htm"],
                "any_depth": False,
                "selection": "adn-1",
                "roles": ["passage"],
                "mode": "lines",
                "derived": "sandcastle_text",
                "tier": "T2",
                "decision_id": "A2",
                "_files": {
                    f"html/2025/{PAGE_1}": page_1.encode("utf-8"),
                    f"html/2025/{PAGE_2}": page_2.encode("utf-8"),
                },
            }
        ],
    }
    truss = _lines(
        "from openseespy.opensees import *",
        "",
        "wipe()",
        "model('basic', '-ndm', 2, '-ndf', 2)",
        "node(1, 0.0, 0.0)",
        "fix(1, 1, 1)",
        "# node(9, 1.0, 1.0)",
        "print(nodeDisp(1, 1))",
    )
    ospdoc = {
        "repo_key": "ospdoc",
        "owner": "synthetic-ops",
        "repo": "ops-doc",
        "commit": _commit(5),
        "ref": {"kind": "head"},
        "category": "structural_analysis",
        "tiers": ["T1", "T2"],
        "decision_ids": ["S1", "S2"],
        "license_expression": "LicenseRef-Synthetic",
        "version_scope": "Synthetic OpenSeesPy 3.5.1.3",
        "attribution": {
            "passage": "Synthetic OpenSeesPy docs. Full Regents notice: str-env-v1 attribution.",
            "environment": "Synthetic OpenSeesPy docs. Regents notice, verbatim:\n{REGENTS_NOTICE}",
        },
        "regents_notice": {
            "snapshot": "upstream/regents-license.html",
            "sha256": None,
            "url": "https://opensees.github.io/OpenSeesDocumentation/developer/license.html",
            "roles": ["license"],
            "tier": "T1",
            "starts_with": "Copyright @ 1999-2020 The Regents of the University of California",
            "contains": "must appear in all copies",
            "last_line_suffix": "TO BENEFIT THE END USER.",
            "line_count": 5,
        },
        "files": [
            _spec(
                "LICENSE",
                ["license"],
                "T1",
                "S1",
                b"OpenSeesPy is free for research, education, and internal use.",
            ),
            _spec(
                "conf.py",
                ["environment"],
                "T1",
                "S1",
                _lines("project = 'OpenSeesPy'", "version = '3.5.1.3'", "release = '3.5.1.3'"),
            ),
            _spec("pyExamples/ElasticTruss.py", ["passage"], "T1", "S1", truss, mode="lines"),
            _spec(
                "src/node.rst",
                ["passage"],
                "T1",
                "S1",
                _lines(
                    ".. function:: node(nodeTag, *crds)",
                    "",
                    "   Create a node with nodeTag and coordinates.",
                ),
                mode="lines",
            ),
            _spec(
                "src/wipe.rst",
                ["passage"],
                "T2",
                "S2",
                _lines(".. function:: wipe()", "", "   Clear the model before a new truss."),
                mode="lines",
            ),
            _spec(
                "src/pypilinux.rst",
                ["environment"],
                "T2",
                "S2",
                _lines("Linux", "=====", "", "pip install openseespy"),
            ),
        ],
        "globs": [],
    }
    objects = _lines(
        "# ***************************************************************************",
        "# *   (c) 2020 Synthetic Castillo <synthetic@example.invalid>               *",
        "# *                                                                         *",
        "# *   This program is free software under the LGPL.                         *",
        "# ***************************************************************************",
        '"""Create a synthetic standard test document for Part objects."""',
        "",
        "import FreeCAD as App",
        "import Part",
        "",
        "",
        "def create_test_file():",
        "    doc = App.newDocument()",
        '    box = doc.addObject("Part::Box", "Box")',
        "    box.Length = 10",
        "    # box.Width = 5",
        "    doc.recompute()",
        "    return box.Shape.Volume",
    )
    cone_xml = _lines(
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!-- Copyright (c) 2020 Synthetic; licensed under the LGPL -->",
        "<GenerateModel>",
        "  <PythonExport",
        '      Name="ConePy"',
        '      PythonName="Part.Cone"',
        '      Namespace="Part">',
        "    <Documentation>",
        "      <UserDocu>Describes a cone with Radius1 and Radius2.</UserDocu>",
        "    </Documentation>",
        "    <!-- internal note -->",
        '    <Attribute Name="Radius1" ReadOnly="false">',
        "      <Documentation><UserDocu>Radius1 of the cone.</UserDocu></Documentation>",
        "    </Attribute>",
        "  </PythonExport>",
        "</GenerateModel>",
    )
    primitive_cpp = (
        "/***************************************************************************\r\n"
        " *   Copyright (c) 2002 Synthetic Riegel <synthetic@example.invalid>       *\r\n"
        " *   This file is part of a synthetic CAx system (LGPL).                   *\r\n"
        " ***************************************************************************/\r\n"
        '\r\n#include "PrimitiveFeature.h"\r\n\r\nPROPERTY_SOURCE(Part::Cone, Part::Primitive)\r\n'
        "\r\nCone::Cone()\r\n{\r\n"
        '    ADD_PROPERTY_TYPE(Radius1, (2.0), "Cone", App::Prop_None, "The cone radius.");\r\n'
        "}\r\n"
    ).encode("utf-8")
    freecad = {
        "repo_key": "freecad102",
        "owner": "synthetic-cad",
        "repo": "cad",
        "commit": _commit(6),
        "ref": {"kind": "tag", "name": "1.0.2", "annotated": False},
        "category": "cad_apis",
        "tiers": ["T1", "T2"],
        "decision_ids": ["C1"],
        "license_expression": "LGPL-2.0-or-later",
        "version_scope": "Synthetic CAD 1.0.2",
        "attribution": {"passage": "Synthetic CAD contributors (LGPL-2.0-or-later).{HEADER}"},
        "files": [
            _spec(
                "LICENSE",
                ["license"],
                "T1",
                "C1",
                b"GNU LIBRARY GENERAL PUBLIC LICENSE\r\nVersion 2, synthetic\r\n",
            ),
            _spec(
                "src/Mod/Part/parttests/part_test_objects.py",
                ["passage", "environment"],
                "T1",
                "C1",
                objects,
                mode="lines",
            ),
            _spec(
                "src/Mod/Part/App/PrimitiveFeature.cpp",
                ["passage"],
                "T2",
                "C1",
                primitive_cpp,
                mode="freecad_cpp",
            ),
            _spec(
                "src/Mod/Part/App/PrimitiveFeature.h",
                ["passage"],
                "T2",
                "C1",
                _lines(
                    "#include <App/PropertyUnits.h>",
                    "class Primitive;",
                    "class PartExport Cone : public Primitive",
                    "{",
                    "public:",
                    "    App::PropertyLength Radius1;",
                    "};",
                ),
                mode="freecad_cpp",
            ),
            _spec(
                "CMakeLists.txt",
                ["environment"],
                "T2",
                "C1",
                _lines(
                    "project(SyntheticCAD)",
                    'set(PACKAGE_VERSION_MAJOR "1")',
                    'set(PACKAGE_VERSION_MINOR "0")',
                    'set(PACKAGE_VERSION_PATCH "2")',
                ),
            ),
            _spec(
                "src/Mod/Part/App/FeaturePartBox.cpp",
                ["passage"],
                "T2",
                "C1",
                _lines(
                    '#include "FeaturePartBox.h"',
                    "",
                    "PROPERTY_SOURCE(Part::Box, Part::Primitive)",
                    "",
                    "Box::Box()",
                    "{",
                    '    ADD_PROPERTY_TYPE(Length, (10.0f), "Box", App::Prop_None, '
                    '"The length of the Part::Box");',
                    "}",
                ),
                mode="freecad_cpp",
                decision_basis="op2",
            ),
        ],
        "globs": [
            {
                "patterns": ["src/Mod/Part/App/*Py.xml"],
                "any_depth": False,
                "roles": ["passage"],
                "mode": "freecad_pyxml",
                "tier": "T2",
                "decision_id": "C1",
                "listed_count": 1,
                "_files": {"src/Mod/Part/App/ConePy.xml": cone_xml},
            }
        ],
    }
    ivp = _lines(
        "import numpy as np",
        "",
        "",
        "def _private(x):",
        "    return x",
        "",
        "",
        "def solve_ivp(fun, t_span, y0, method='RK45', t_eval=None):",
        '    """Solve an initial value problem for a system of ODEs.',
        "",
        "    Parameters",
        "    ----------",
        "    fun : callable",
        "        Right-hand side of the system: fun(t, y).",
        "    t_span : 2-member sequence",
        "        Interval of integration (t0, tf).",
        "    y0 : array_like, shape (n,)",
        "        Initial state.",
        '    """',
        "    return None",
    )
    notes = _lines(
        "SciPy 1.16.0 Release Notes",
        "==========================",
        "",
        "Highlights",
        "----------",
        "Faster things.",
        "",
        "`scipy.integrate` improvements",
        "------------------------------",
        "- solve_ivp gained a synthetic decay option.",
        "",
        "`scipy.linalg` improvements",
        "---------------------------",
        "- unrelated.",
    )
    scipy = {
        "repo_key": "scipy1161",
        "owner": "synthetic-sci",
        "repo": "sci",
        "commit": _commit(7),
        "ref": {"kind": "tag", "name": "v1.16.1", "annotated": True, "tag_object": _commit(8)},
        "category": "simulation",
        "tiers": ["T1", "T2"],
        "decision_ids": ["M1"],
        "license_expression": "BSD-3-Clause",
        "version_scope": "Synthetic SciPy 1.16.1",
        "attribution": {"passage": "Synthetic SciPy (BSD-3-Clause)."},
        "public_names": {
            "index": "scipy/integrate/_ivp/__init__.py",
            "names": ["solve_ivp", "RK45"],
        },
        "files": [
            _spec(
                "LICENSE.txt",
                ["license"],
                "T1",
                "M1",
                _lines("Copyright (c) 2001-2002 Synthetic Enthought, Inc.", "BSD-3-Clause"),
            ),
            _spec(
                "scipy/integrate/_ivp/ivp.py",
                ["passage"],
                "T1",
                "M1",
                ivp,
                mode="python_public_api",
            ),
            _spec(
                "scipy/integrate/_ivp/__init__.py",
                ["index"],
                "T2",
                "M1",
                _lines("from .ivp import solve_ivp", "from .rk import RK45"),
            ),
            _spec(
                "scipy/integrate/_ivp/rk.py",
                ["passage"],
                "T2",
                "M1",
                _lines(
                    "class RK45:",
                    '    """Explicit Runge-Kutta method of order 5(4)."""',
                    "",
                    "    order = 5",
                ),
                mode="python_public_api",
            ),
            _spec(
                "doc/source/release/1.16.0-notes.rst",
                ["passage"],
                "T2",
                "M1",
                notes,
                mode="rst_sections",
            ),
            _spec(
                "pyproject.toml",
                ["environment"],
                "T2",
                "M1",
                _lines(
                    "[project]",
                    'name = "scipy"',
                    'requires-python = ">=3.11"',
                    'dependencies = ["numpy>=1.25.2,<2.6"]',
                ),
            ),
        ],
        "globs": [],
    }
    return [arcpy, ptt, tbc, adn, ospdoc, freecad, scipy]


ENVIRONMENT = [
    {
        "id": "gis-env-v1",
        "category": "gis_scripting",
        "repo_key": "arcpy",
        "target": "Synthetic desktop 3.6 (ArcPy)",
        "blocks": [
            {"file_key": "arcpy/docs/arcgis-dist.json", "lines": "2-5"},
            {"file_key": "arcpy/docs/ArcPy-Cheatsheet.pdf!text", "lines": "5-6"},
        ],
    },
    {
        "id": "aec-env-v1",
        "category": "aec_automation",
        "repo_key": "tbc2025",
        "target": "Synthetic Revit 2025 (.NET 8)",
        "blocks": [
            {"file_key": "tbc2025/BuildingCoder/BuildingCoder.csproj", "lines": "3"},
            {
                "file_key": "tbc2025/BuildingCoder/TheBuildingCoderSingleSample.addin",
                "lines": "1-4",
            },
            {"file_key": "tbc2025/Readme.md", "lines": "2-3"},
        ],
    },
    {
        "id": "str-env-v1",
        "category": "structural_analysis",
        "repo_key": "ospdoc",
        "target": "Synthetic OpenSeesPy 3.5.1.3",
        "blocks": [
            {"file_key": "ospdoc/conf.py", "lines": "2"},
            {"file_key": "ospdoc/src/pypilinux.rst", "lines": "1-4"},
        ],
    },
    {
        "id": "cad-env-v1",
        "category": "cad_apis",
        "repo_key": "freecad102",
        "target": "Synthetic CAD 1.0.2",
        "blocks": [
            {"file_key": "freecad102/CMakeLists.txt", "lines": "2-4"},
            {
                "file_key": "freecad102/src/Mod/Part/parttests/part_test_objects.py",
                "lines": "6,8-9",
            },
        ],
    },
    {
        "id": "sim-env-v1",
        "category": "simulation",
        "repo_key": "scipy1161",
        "target": "Synthetic SciPy 1.16.1",
        "blocks": [{"file_key": "scipy1161/pyproject.toml", "lines": "3-4"}],
    },
]

BRIEFS = {
    "gis_scripting": "Read OID@ and SHAPE@XY with a SearchCursor on scratch table {n}. "
    "List routes with arcpy.ListFeatureClasses first.",
    "aec_automation": "List walls with a FilteredElementCollector in synthetic add-in {n}. "
    "Use Document.GetElement for lookups.",
    "structural_analysis": "Create node {n} and fix it in a two-dimensional truss. "
    "Report nodeDisp for the node after wipe.",
    "cad_apis": "Create a Part::Box named Box{n} and read its Shape.Volume. "
    "Compare it with a Part::Cone of Radius1.",
    "simulation": "Integrate synthetic decay model {n} with solve_ivp over t_span. "
    "Explain the y0 shape and RK45.",
}


def base_pack() -> dict:
    sources = []
    for category in r.CATEGORIES:
        text = f"Synthetic static reference summary for {category}; not upstream text."
        sources.append(
            {
                "id": f"{r.CATEGORY_CODES[category]}-static",
                "url": "https://example.invalid/static",
                "version": "synthetic-1",
                "retrieved_at": PREPARED_AT,
                "license": "synthetic",
                "license_evidence": "synthetic",
                "attribution": "Synthetic fixture",
                "installation": "Synthetic installation note.",
                "text": text,
                "content_sha256": r.digest(text),
                "allowed_uses": list(r.ALLOWED_USES),
                "export_permission": "local_only",
            }
        )
    tasks = [
        {
            "id": f"{category}-{n:02d}",
            "brief": BRIEFS[category].format(n=n),
            "category": category,
            "source_refs": [f"{r.CATEGORY_CODES[category]}-static"],
        }
        for category in r.CATEGORIES
        for n in range(1, 11)
    ]
    return {
        "schema_version": "1",
        "pack_id": "engineering-v1",
        "version": "1.0",
        "approved_by": "Synthetic owner",
        "approved_at": "2026-11-10",
        "approval_basis": "Synthetic approval for tests only",
        "permission_status": "approved_for_assessed_generation",
        "sources": sources,
        "tasks": tasks,
    }


def _never_stored(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return "RevitSdkSamples" in path.split("/") or any(
        word in name.lower() for word in ("credential", "secret", "password", "token")
    )


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@dataclass
class World:
    root: Path
    evidence: Path
    repository: Path
    config_path: Path
    tier2: Path
    corpus: Path
    pack_dir: Path
    config: dict
    receipt: dict
    stored: dict = field(default_factory=dict)

    def corpus_args(self, **extra) -> dict:
        return {
            "config": self.config_path,
            "tier2": self.tier2,
            "output": self.corpus,
            "evidence": self.evidence,
            "repository": self.repository,
            "count_tokens": words,
            "tokenizer": dict(TOKENIZER),
            **extra,
        }

    def pack_args(self, **extra) -> dict:
        return {
            "corpus": self.corpus,
            "output": self.pack_dir,
            "evidence": self.evidence,
            "repository": self.repository,
            "count_tokens": words,
            "tokenizer": dict(TOKENIZER),
            **extra,
        }


def make_world(
    tmp_path: Path,
    *,
    config_hook=None,
    receipt_hook=None,
    verification_hook=None,
    extraction_hook=None,
    repositories_hook=None,
) -> World:
    """Write the synthetic inputs; hooks mutate a record before its pins are taken."""
    root = tmp_path / "world"
    evidence = root / "evidence" / "P1-03"
    repository = root / "repo"
    tier2 = evidence / "aec-course" / "rag" / "tier2-v1"
    snapshot_dir = "references/preparation-20261110"
    repositories = _repositories()
    if repositories_hook:
        repositories_hook(repositories)
    pack = base_pack()
    pack_bytes = r.pack_json(pack).encode("utf-8")
    _write(evidence / "references/engineering-v1.json", pack_bytes)
    approval = _write(
        evidence / "references/engineering-v1-approval.json", b'{"synthetic": "approval"}\n'
    ).read_bytes()
    extractor = _write(
        repository / "tools/extract_reference_pdf.py", b"# synthetic extractor\n"
    ).read_bytes()
    cheat = _write(
        evidence / "qualification/m4-recovery-contract-followup-20261117/"
        "packet-final/sources/ArcPy-Cheatsheet.txt",
        CHEAT_SHEET,
    ).read_bytes()

    upstream: dict[str, str] = {}
    provenance_items = []
    receipt_repos = []
    stored = {}
    for repo in repositories:
        files = []
        all_files = [(s["path"], s.pop("_content"), s) for s in repo["files"]]
        for glob in repo["globs"]:
            all_files += [(p, c, None) for p, c in glob.pop("_files").items()]
        for path, content, spec in sorted(all_files, key=lambda x: x[0]):
            blob = r.git_blob_id(content)
            if _never_stored(path):
                # Like the fetch: deny-listed and credential-like paths are listed, not stored.
                files.append(
                    {
                        "path": path,
                        "mode": "100644",
                        "blob": blob,
                        "size": None,
                        "raw_sha256": None,
                        "stored": None,
                    }
                )
                continue
            relative = f"files/{repo['repo_key']}/{path}"
            stored[(repo["repo_key"], path)] = _write(tier2 / relative, content)
            files.append(
                {
                    "path": path,
                    "mode": "100644",
                    "blob": blob,
                    "size": len(content),
                    "raw_sha256": r.sha256_hex(content),
                    "stored": relative,
                }
            )
            if spec is not None:
                spec["blob"] = blob
            if spec is not None and spec["tier"] == "T1":
                commit = TBC_ALIAS if repo["repo_key"] == "tbc2025" else repo["commit"]
                if spec.get("derived") == "pdf_text":
                    name = "ArcPy-Cheatsheet.pdf"
                    _write(evidence / snapshot_dir / name, content)
                    url = (
                        f"https://raw.githubusercontent.com/{repo['owner']}/{repo['repo']}/"
                        f"{commit}/{path}"
                    )
                    digest = r.sha256_hex(content)
                else:
                    name = f"upstream/{repo['repo_key']}_{path.replace('/', '_')}"
                    snapshot = r.n1(content).encode("utf-8")
                    _write(evidence / snapshot_dir / name, snapshot)
                    url = f"https://github.com/{repo['owner']}/{repo['repo']}/blob/{commit}/{path}"
                    digest = r.sha256_hex(snapshot)
                upstream[name] = digest
                provenance_items.append({"path": name, "url": url, "sha256": digest})
        notice = repo.get("regents_notice")
        if notice:
            data = REGENTS_HTML.encode("utf-8")
            _write(evidence / snapshot_dir / notice["snapshot"], data)
            notice["sha256"] = r.sha256_hex(data)
            upstream[notice["snapshot"]] = notice["sha256"]
            provenance_items.append(
                {"path": notice["snapshot"], "url": notice["url"], "sha256": notice["sha256"]}
            )
        repo["url"] = f"https://github.com/{repo['owner']}/{repo['repo']}.git"
        receipt_repos.append(
            {
                "repo_key": repo["repo_key"],
                "url": repo["url"],
                "commit": repo["commit"],
                "tag": repo["ref"].get("name") if repo["ref"]["kind"] == "tag" else None,
                "ls_remote": {},
                "fetched_at": FETCHED_AT,
                "commands": [],
                "files": files,
            }
        )

    aec_briefs = [t["brief"] for t in pack["tasks"] if t["category"] == "aec_automation"]
    adn_files = next(x for x in receipt_repos if x["repo_key"] == "adn2025")["files"]
    hhk_blob = next(f["blob"] for f in adn_files if f["path"].endswith(".hhk"))
    receipt = {
        "schema_version": "rag-fetch-v1",
        "tool": {"path": "synthetic", "sha256": "0" * 64},
        "git_version": "synthetic",
        "hosts_contacted": ["github.com"],
        "repositories": receipt_repos,
        "adn_selection": {**r.adn_select(HHK + "\n", aec_briefs), "hhk_blob": hhk_blob},
    }

    provenance = {"prepared_at": PREPARED_AT, "upstream": provenance_items}
    provenance_bytes = _write(
        evidence / snapshot_dir / "provenance.json", r.record_json(provenance).encode("utf-8")
    ).read_bytes()
    verification = {
        "approved_pack_file_sha256": r.sha256_hex(pack_bytes),
        "approval_receipt_sha256": r.sha256_hex(approval),
        "upstream_files_sha256": dict(sorted(upstream.items())),
        "source_hashes": {s["id"]: s["content_sha256"] for s in pack["sources"]},
    }
    if verification_hook:
        verification_hook(verification)
    verification_bytes = _write(
        evidence / "aec-course/analysis/source-verification.json",
        r.record_json(verification).encode("utf-8"),
    ).read_bytes()
    extraction = {
        "original_sha256": upstream["ArcPy-Cheatsheet.pdf"],
        "extractor_sha256": r.sha256_hex(extractor),
        "output_sha256": r.sha256_hex(cheat),
    }
    if extraction_hook:
        extraction_hook(extraction)
    extraction_path = (
        "qualification/m4-recovery-contract-followup-20261117/packet-final/"
        "sources/arcpy-extraction.json"
    )
    extraction_bytes = _write(
        evidence / extraction_path, r.record_json(extraction).encode("utf-8")
    ).read_bytes()

    config_repos = copy.deepcopy(repositories)
    config = {
        "schema_version": "rag-sources-v1",
        "corpus_id": "engineering-v1-rag-corpus-v1",
        "pack_id": r.PACK_ID,
        "allowed_uses": list(r.ALLOWED_USES),
        "export_permission": "local_only",
        "decision_record": {"path": "ITERATION_LOG.md", "entry": "Synthetic decisions"},
        "decision_basis": {"default": "synthetic default basis", "op2": "synthetic OP-2 basis"},
        "decisions": [
            {"id": d, "scope": f"synthetic {d}", "tier": "T1 + T2", "owner_record": "synthetic"}
            for d in ("G1", "G2", "A1", "A2", "S1", "S2", "C1", "M1")
        ],
        "deny_lists": json.loads(
            (REPO / "config/aec-course/rag-sources-v1.json").read_text(encoding="utf-8")
        )["deny_lists"],
        "tier1": {
            "source_verification": {
                "path": "aec-course/analysis/source-verification.json",
                "sha256": r.sha256_hex(verification_bytes),
            },
            "engineering_v1": {
                "path": "references/engineering-v1.json",
                "sha256": r.sha256_hex(pack_bytes),
                "digest": r.digest(pack),
            },
            "approval": {
                "path": "references/engineering-v1-approval.json",
                "sha256": r.sha256_hex(approval),
            },
            "provenance": {
                "path": f"{snapshot_dir}/provenance.json",
                "sha256": r.sha256_hex(provenance_bytes),
            },
            "snapshot_dir": snapshot_dir,
            "pdf": {
                "path": f"{snapshot_dir}/ArcPy-Cheatsheet.pdf",
                "sha256": upstream["ArcPy-Cheatsheet.pdf"],
            },
            "cheat_sheet_text": {
                "path": "qualification/m4-recovery-contract-followup-20261117/packet-final/"
                "sources/ArcPy-Cheatsheet.txt",
                "sha256": r.sha256_hex(cheat),
            },
            "extraction_receipt": {
                "path": extraction_path,
                "sha256": r.sha256_hex(extraction_bytes),
            },
            "extractor": {
                "path": "tools/extract_reference_pdf.py",
                "sha256": r.sha256_hex(extractor),
                "version": "synthetic 1",
            },
            "prepared_at": PREPARED_AT,
            "commit_aliases": [{"repo_key": "tbc2025", "commit": TBC_ALIAS}],
        },
        "repositories": config_repos,
        "rst_section_filter": "scipy.integrate",
        "environment_passages": copy.deepcopy(ENVIRONMENT),
    }
    if config_hook:
        config_hook(config)
    config_path = _write(
        repository / "config/aec-course/rag-sources-v1.json", r.record_json(config).encode("utf-8")
    )
    receipt["inputs"] = [
        {
            "root": "repository",
            "path": "config/aec-course/rag-sources-v1.json",
            "role": "sources_config",
            "sha256": r.sha256_hex(config_path.read_bytes()),
            "bytes": config_path.stat().st_size,
        }
    ]
    if receipt_hook:
        receipt_hook(receipt)
    _write(tier2 / "fetch-receipt.json", r.record_json(receipt).encode("utf-8"))
    return World(
        root=root,
        evidence=evidence,
        repository=repository,
        config_path=config_path,
        tier2=tier2,
        corpus=evidence / "aec-course/rag/corpus-v1",
        pack_dir=evidence / "aec-course/rag/engineering-v1-rag-bm25-v1",
        config=config,
        receipt=receipt,
        stored=stored,
    )


def repository(config: dict, key: str) -> dict:
    return next(x for x in config["repositories"] if x["repo_key"] == key)


def file_spec(config: dict, key: str, path: str) -> dict:
    return next(f for f in repository(config, key)["files"] if f["path"] == path)


def output_files(directory: Path) -> dict[str, bytes]:
    """Every file except run.json, by relative path."""
    return {
        p.relative_to(directory).as_posix(): p.read_bytes()
        for p in sorted(directory.rglob("*"))
        if p.is_file() and p.name != "run.json"
    }
