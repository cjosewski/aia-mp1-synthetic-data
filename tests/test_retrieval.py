"""Pure retrieval library: normalization, live code, windows, BM25, selection, metrics."""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from aia_mp1 import retrieval as r

REPO = Path(__file__).resolve().parents[1]


def words(text):
    return len(text.split())


def chunk(
    key,
    *,
    file_index=0,
    start=1,
    end=1,
    tokens=10,
    text=None,
    category="gis_scripting",
    file_key=None,
    removed=(),
):
    return r.Chunk(
        chunk_key=key,
        category=category,
        file_key=file_key or f"f{file_index}",
        file_index=file_index,
        start=start,
        end=end,
        text=text if text is not None else key,
        qwen_tokens=tokens,
        removed_within=tuple(removed),
    )


# ---------------------------------------------------------------- N1


def test_n1_line_endings_bom_and_appended_newline():
    assert r.n1(b"a\r\nb\rc") == "a\nb\nc\n"
    assert r.n1(b"\xef\xbb\xbfx") == "x\n"
    assert r.n1(b"\xef\xbb\xbf\xef\xbb\xbfx") == "\ufeffx\n"
    assert r.n1(b"x\n") == "x\n\n"
    assert r.n1(b"") == "\n"
    with pytest.raises(UnicodeDecodeError):
        r.n1(b"caf\xe9")


def test_n1_keeps_line_numbering():
    raw = b"one\r\n\r\nthree\rfour\nfive"
    assert r.split_lines(r.n1(raw)) == raw.decode().splitlines()
    assert r.split_lines(r.n1(b"a\n")) == ["a", ""]


def test_git_blob_id_matches_git():
    assert r.git_blob_id(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    assert r.git_blob_id(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


# ---------------------------------------------------------------- §6.1 terms


def test_golden_terms():
    assert r.terms("arcpy.da.SearchCursor(fc, ['OID@', 'SHAPE@XY'])") == [
        "arcpy",
        "arcpy.da.searchcursor",
        "cursor",
        "da",
        "da.searchcursor",
        "search",
        "searchcursor",
        "fc",
        "oid",
        "oid@",
        "shape",
        "shape@xy",
        "xy",
    ]
    volume = r.candidate_terms("self.doc.Box1.Shape.Volume")
    assert {"shape.volume", "box1"} <= volume
    assert r.terms("1e-6 and 3.5.1.3 net8.0-windows") == [
        "1e-6",
        "3.5.1.3",
        "net",
        "net8",
        "windows",
    ]


def test_stopwords_short_terms_and_no_stemming():
    assert r.terms("the and of x9") == ["x9"]
    assert r.terms("a b c d1") == ["d1"]
    assert r.terms("walls wall walling") == ["walls", "wall", "walling"]
    assert r.terms("Part::Cone") == ["cone", "part", "part::cone"]
    assert r.terms("HOST_AREA_COMPUTED") == ["area", "computed", "host", "host_area_computed"]


# ---------------------------------------------------------------- §6.2 BM25


def test_golden_bm25():
    corpus = ["alpha beta", "alpha gamma gamma", "delta"]
    assert r.bm25_scores(corpus, "gamma") == [0.0, 1.18236951, 0.0]
    assert r.bm25_scores(corpus, "alpha gamma") == [0.470003629, 1.572561203, 0.0]


HASH_SEED_SCRIPT = textwrap.dedent(
    """
    import json
    from aia_mp1 import retrieval as r
    texts = [
        "Part::Box Length Width Height shape volume",
        "Part::Cone Radius1 Radius2 shape volume shape",
        "doc.recompute() Shape.Volume Part::Box Part::Cone",
        "Radius10 Radius1 Radius2 cone box cylinder",
        "unrelated words only here",
        "Shape.Volume Shape.Area Shape.BoundBox",
    ] * 3
    chunks = [
        r.Chunk(f"f{i}#L1-L1", "cad_apis", f"f{i}", i, 1, 1, t, 100 + i)
        for i, t in enumerate(texts)
    ]
    retriever = r.CategoryRetriever(chunks, {"f2": [1]})
    result = retriever.retrieve("Use Part::Cone with Radius1 and read Shape.Volume of a box.")
    print(json.dumps({
        "terms": result.query_terms,
        "ranking": [[c.chunk.chunk_key, c.r_raw, c.r_final, c.m, c.decision]
                    for c in result.ranking],
        "metrics": r.holdout_line_test(chunks),
    }))
    """
)


def run_with_seed(script, seed):
    env = {k: v for k, v in os.environ.items() if k != "AIA_MP1_DOMAIN"}
    env["PYTHONHASHSEED"] = str(seed)
    completed = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True, text=True, check=True
    )
    return completed.stdout


def test_ranking_is_identical_under_hash_seeds_0_and_1():
    first = run_with_seed(HASH_SEED_SCRIPT, 0)
    assert first == run_with_seed(HASH_SEED_SCRIPT, 1)
    assert json.loads(first)["ranking"]


# ---------------------------------------------------------------- §6.3 identifiers


def test_identifier_example_and_exclusions():
    brief = (
        "Use Part::Cone with Radius1, read Shape.Volume and OID@ via SearchCursor; "
        "avoid get_BoundingBox(null)."
    )
    assert r.brief_identifiers(brief) == [
        "Part::Cone",
        "Radius1",
        "Shape.Volume",
        "OID@",
        "SearchCursor",
        "get_BoundingBox",
    ]
    text = "In ArcPy use arcpy.env with FreeCAD, NumPy and OpenSeesPy; ArcPy again."
    assert r.brief_identifiers(text) == ["arcpy.env"]
    assert r.code_like_tokens(text) == ["ArcPy", "arcpy.env", "FreeCAD", "NumPy", "OpenSeesPy"]
    assert not r.is_code_like("3.5.1.3")
    assert r.is_code_like("e.g")
    assert r.is_code_like("y0")
    assert not r.is_code_like("Revit")


def test_identifier_exact_match_boundaries_and_case():
    assert not r.identifier_in("SHAPE@", "row = ['SHAPE@XY']")
    assert r.identifier_in("SHAPE@", "row = ['SHAPE@']")
    assert not r.identifier_in("Radius1", "cone.Radius10 = 2")
    assert r.identifier_in("Radius1", "cone.Radius1 = 2")
    assert r.identifier_in("Shape.Volume", "v = self.doc.Box1.Shape.Volume")
    assert not r.identifier_in("Shape.Volume", "xShape.Volume")
    assert not r.identifier_in("shape.volume", "self.doc.Box1.Shape.Volume")


def test_bonus_is_half_top_raw_per_distinct_identifier_capped_at_two():
    c = chunk("c")
    assert r.score_chunk(c, 2.0, 0, 4.0).r_final == 2.0
    assert r.score_chunk(c, 2.0, 1, 4.0).r_final == 4.0
    assert r.score_chunk(c, 2.0, 2, 4.0).r_final == 6.0
    assert r.score_chunk(c, 2.0, 5, 4.0).r_final == 6.0
    chunks = [
        chunk("once", file_index=0, text="FooBar FooBar FooBar alpha"),
        chunk("both", file_index=1, text="FooBar BazQux"),
        chunk("none", file_index=2, text="nothing relevant"),
    ]
    result = r.CategoryRetriever(chunks).retrieve("Join FooBar with BazQux.")
    by_key = {c.chunk.chunk_key: c for c in result.ranking}
    assert by_key["once"].m == 1 and by_key["both"].m == 2 and by_key["none"].m == 0
    assert result.identifier_chunks == {"FooBar": 2, "BazQux": 1}
    for candidate in result.ranking:
        bonus = 0.5 * result.top_raw * min(candidate.m, 2)
        assert abs(candidate.r_final - (candidate.r_raw + bonus)) < 2e-9


# ---------------------------------------------------------------- §6.4 selection


def ranked(*items):
    return [r.Scored(c, raw, final, m) for c, raw, final, m in items]


def test_budget_skips_without_truncating():
    a, b, c, d, e = (
        chunk(k, file_index=i, tokens=t)
        for i, (k, t) in enumerate([("A", 600), ("B", 700), ("C", 500), ("D", 200), ("E", 100)])
    )
    rows = ranked((a, 5, 5, 0), (b, 4, 4, 0), (c, 3, 3, 0), (d, 2, 2, 0), (e, 1, 1, 0))
    selected, decisions, floor = r.select_ranked(rows)
    assert [x.chunk_key for x in selected] == ["A", "B", "D", "E"]
    assert [x.decision for x in decisions] == [
        "selected",
        "selected",
        "budget",
        "selected",
        "selected",
    ]
    assert floor == 1.0
    assert all(x.text == x.chunk_key for x in selected)


def test_floor_k_and_zero_scores():
    items = [chunk(str(i), file_index=i) for i in range(7)]
    rows = ranked(*[(c, s, s, 0) for c, s in zip(items, [10, 9, 8, 7, 6, 1.9, 0], strict=True)])
    selected, decisions, floor = r.select_ranked(rows)
    assert floor == 2.0
    assert [x.decision for x in decisions] == ["selected"] * 4 + [
        "k_reached",
        "below_floor",
        "below_floor",
    ]
    zero = ranked((chunk("z"), 0.0, 0.0, 0))
    assert r.select_ranked(zero)[0] == [] and r.select_ranked(zero)[1][0].decision == "below_floor"


def test_overlap_with_selected_and_environment_lines():
    a = chunk("a", file_key="f", start=1, end=30)
    b = chunk("b", file_key="f", start=16, end=45)
    c = chunk("c", file_key="f", start=31, end=60)
    rows = ranked((a, 3, 3, 0), (b, 2, 2, 0), (c, 1, 1, 0))
    assert [x.decision for x in r.select_ranked(rows)[1]] == ["selected", "overlap", "selected"]
    env = chunk("env", file_key="g", start=20, end=40)
    free = chunk("free", file_key="g", start=1, end=22)
    rows = ranked((env, 2, 2, 0), (free, 1, 1, 0))
    selected, decisions, _ = r.select_ranked(rows, {"g": [23]})
    assert [x.decision for x in decisions] == ["overlap", "selected"]
    assert [x.chunk_key for x in selected] == ["free"]


def test_every_tie_break_level():
    base = dict(file_index=5, start=10, end=20)
    expected = [
        r.Scored(chunk("final", **base), 1.0, 3.0, 0),
        r.Scored(chunk("m", **base), 1.0, 2.0, 2),
        r.Scored(chunk("raw", **base), 2.0, 2.0, 1),
        r.Scored(chunk("file", **base), 1.0, 2.0, 1),
        r.Scored(chunk("start", file_index=6, start=1, end=20), 1.0, 2.0, 1),
        r.Scored(chunk("end", file_index=6, start=2, end=3), 1.0, 2.0, 1),
        r.Scored(chunk("key-a", file_index=6, start=2, end=4), 1.0, 2.0, 1),
        r.Scored(chunk("key-b", file_index=6, start=2, end=4), 1.0, 2.0, 1),
    ]
    assert r.rank(reversed(expected)) == expected


def test_scores_1e12_apart_tie_after_rounding():
    low = r.score_chunk(chunk("low", file_index=1), 1.0 + 1e-12, 0, 1.0)
    high = r.score_chunk(chunk("high", file_index=0), 1.0, 0, 1.0)
    assert low.r_raw == high.r_raw and low.r_final == high.r_final
    assert [x.chunk.chunk_key for x in r.rank([low, high])] == ["high", "low"]


# ---------------------------------------------------------------- §5.2 live-code rules


def removals(text, family, **kwargs):
    return r.live_code(text, family, **kwargs)


def test_cs2_region_header_and_leading_comment_banner():
    text = textwrap.dedent(
        """\
        #region Header
        //
        // Sample.cs - synthetic sample
        //
        // Copyright (C) 2020 by Synthetic Author,
        // Example Inc. All rights reserved.
        //
        #endregion // Header

        using System;
        """
    )
    live = removals(text, "cs")
    assert live.removed == ((1, 8, "license_banner"),)
    assert r.file_header(r.split_lines(text), live.removed) == (
        "Copyright (C) 2020 by Synthetic Author, Example Inc. All rights reserved."
    )
    plain = "// Copyright 2020 Synthetic\n// Licensed under MIT\n\nusing System;\n"
    assert removals(plain, "cs").removed == ((1, 2, "license_banner"),)
    prose = "// Synthetic header\n// only prose here\n\nusing System;\n"
    assert removals(prose, "cs").removed == ()


def test_cs1_commented_out_code():
    text = textwrap.dedent(
        """\
        using System;
        class A
        {
            //foo();
            // prose is kept
            //  continued code
            //\ttabbed code
            /// <summary>doc</summary>
            //
            int x = 1; // trailing
            string s = "//not a comment";
        }
        """
    )
    assert removals(text, "cs").removed == (
        (4, 4, "commented_out_code"),
        (6, 7, "commented_out_code"),
    )


def test_bc1_banner_doc_comment_block_comment_and_bc2():
    text = textwrap.dedent(
        """\
        /***************************************************************************
         *   Copyright (c) 2020 Synthetic Author                                   *
         *                                                                         *
         ***************************************************************************/

        #include "A.h"

        /** Doc comment kept.
         *  Interior line.
         */
        int a = 1;
        /* Copyright notice after code
        int b = 2;
        */
        int c = 3; /* trailing
           interior
           end */ int d = 4;
        /*! Qt-style doc
            interior
        */
        const char* s = "/* not a comment */";
        """
    )
    live = removals(text, "c")
    assert live.removed == ((1, 4, "license_banner"), (12, 14, "block_comment"))
    assert live.no_boundary == ((8, 10), (16, 16), (18, 20))
    assert r.file_header(r.split_lines(text), live.removed) == "Copyright (c) 2020 Synthetic Author"


def test_py1_greedy_prose_kept_and_strings_untouched():
    text = textwrap.dedent(
        '''\
        import os

        # Arrange
        box = 1
        # self.box = Part.makeBox(1, 2, 2)
        # self.assertEqual(
        #     a, b)

        # This is prose, not code.
        x = "# not a comment"
        s = """
        # inside a string
        """
        # total = compute()
        # total
        '''
    )
    assert removals(text, "python").removed == (
        (5, 7, "commented_out_code"),
        (14, 15, "commented_out_code"),
    )


def test_py2_banner_after_shebang_and_cookie():
    text = textwrap.dedent(
        """\
        #!/usr/bin/env python3
        # -*- coding: utf-8 -*-
        # Copyright 2020 Synthetic
        # Licensed under the MIT license.

        import os
        """
    )
    assert removals(text, "python").removed == ((3, 4, "license_banner"),)


def test_py3_module_level_license_strings():
    text = textwrap.dedent(
        '''\
        """Synthetic module.

        Copyright 2020 Synthetic. This file is under a license.
        """
        import os
        """Licensed under the Apache License."""
        x = 1
        """Just a note."""
        '''
    )
    assert removals(text, "python").removed == ((1, 4, "license_banner"), (6, 6, "license_banner"))


def test_python_that_does_not_parse_is_not_python3():
    with pytest.raises(r.NotPython3):
        r.live_code("print 'python 2'\n", "python")


def test_xml1_banner_and_comments():
    text = textwrap.dedent(
        """\
        <?xml version="1.0" encoding="UTF-8"?>
        <!-- Copyright (c) 2020 Synthetic
             Licensed under LGPL -->
        <Root>
          <!-- a plain comment -->
          <Child/> <!-- trailing -->
          <!-- multi
               line -->
        </Root>
        """
    )
    assert removals(text, "xml").removed == (
        (2, 3, "license_banner"),
        (5, 5, "xml_comment"),
        (7, 8, "xml_comment"),
    )


def test_txt1_notice_block_and_assertion():
    text = (
        "line one\nCopyright © 2025 Synthetic. All rights reserved.\nmore notice\n"
        "other marks belong to their respective mark owners.\nafter\n"
    )
    assert removals(text, "cheat_sheet", notice_lines=(2, 4)).removed == ((2, 4, "notice_block"),)
    with pytest.raises(ValueError, match="expected"):
        r.live_code(text, "cheat_sheet", notice_lines=(290, 293))
    assert r.notice_text(r.split_lines(text), (2, 4)).startswith("Copyright © 2025 Synthetic.")


# ---------------------------------------------------------------- §5.4 windows


def test_window_worked_example():
    live = [(n, f"w{n}") for n in range(1, 51)]
    spans, oversize = r.windows(live, set(), words)
    assert spans == [(1, 30), (16, 45), (31, 50)]
    assert oversize == []


def test_windows_limits_edges_coverage_and_oversize():
    lines = []
    for n in range(1, 81):
        if n % 9 == 0:
            lines.append("")
        elif n == 40:
            lines.append(" ".join(["big"] * 500))
        else:
            lines.append(" ".join([f"t{n}"] * 40))
    no_boundary = {12, 13}
    live = list(enumerate(lines, 1))
    spans, oversize = r.windows(live, no_boundary, words)
    assert oversize == [40]
    text_of = dict(live)
    covered = set()
    for a, b in spans:
        body = [text_of[n] for n in range(a, b + 1)]
        assert len(body) <= 30
        assert words("\n".join(body)) <= 480
        assert text_of[a].strip() and text_of[b].strip()
        assert a not in no_boundary and b not in no_boundary
        covered.update(range(a, b + 1))
    eligible = {n for n, t in live if t.strip() and n not in no_boundary}
    assert eligible - covered == {40}


def test_chunk_segments_respect_boundaries_and_reslice_verbatim():
    lines = [f"line {n} code" for n in range(1, 41)]
    lines[4] = "//removed();"
    text = "\n".join(lines) + "\n"
    live = r.live_code(text, "cs")
    segments = [r.Segment(1, 20, "first"), r.Segment(21, 40, "second")]
    rows, oversize = r.chunk_segments(text, segments, live, words)
    assert oversize == []
    assert [(x["start"], x["end"], x["segment_label"]) for x in rows] == [
        (1, 20, "first"),
        (21, 40, "second"),
    ]
    first = rows[0]
    assert "//removed();" not in first["text"]
    assert first["removed_within"] == [[5, 5, "commented_out_code"]]
    assert r.reslice(text, 1, 20, first["removed_within"]) == first["text"]
    assert first["qwen_tokens"] == words(first["text"])


def test_finalize_drops_duplicates_collapses_text_and_drops_termless():
    def row(category, file_key, file_index, start, end, text):
        return {
            "category": category,
            "file_key": file_key,
            "file_index": file_index,
            "start": start,
            "end": end,
            "text": text,
            "segment_label": None,
            "removed_within": [],
            "qwen_tokens": 3,
        }

    rows = [
        row("cad_apis", "b", 1, 1, 2, "same text here"),
        row("cad_apis", "a", 0, 1, 2, "same text here"),
        row("cad_apis", "a", 0, 1, 2, "same text here"),
        row("simulation", "c", 2, 1, 2, "same text here"),
        row("cad_apis", "a", 0, 5, 6, "== ++ --"),
    ]
    kept, record = r.finalize_chunks(rows)
    assert [x["chunk_key"] for x in kept] == ["a#L1-L2", "c#L1-L2"]
    assert record == {
        "duplicate_spans": ["a#L1-L2"],
        "collapsed": [{"chunk_key": "b#L1-L2", "kept": "a#L1-L2"}],
        "no_terms": ["a#L5-L6"],
    }
    assert kept[0]["content_sha256"] == r.digest("same text here")
    assert kept[0]["n_terms"] == 3


# ---------------------------------------------------------------- §5.3 segment modes

PYXML = textwrap.dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <GenerateModel xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
      <PythonExport
          Father="PrimitivePy"
          Name="ConePy"
          PythonName="Part.Cone"
          Namespace="Part">
        <Documentation>
          <UserDocu>A cone.</UserDocu>
        </Documentation>
        <Methode Name="isValid">
          <Documentation><UserDocu>Check.</UserDocu></Documentation>
        </Methode>
        <Attribute Name="Radius1" ReadOnly="false">
          <Documentation><UserDocu>Radius.</UserDocu></Documentation>
          <Parameter Name="Radius1" Type="Float"/>
        </Attribute>
        <CustomAttributes />
      </PythonExport>
    </GenerateModel>
    """
)


def test_freecad_pyxml_segments():
    assert r.segments_freecad_pyxml(PYXML) == [
        r.Segment(3, 10, "Part.Cone class"),
        r.Segment(11, 13, "Part.Cone method isValid"),
        r.Segment(14, 17, "Part.Cone attribute Radius1"),
    ]
    document = (
        PYXML.replace('PythonName="Part.Cone"', "")
        .replace('Name="ConePy"', 'Name="DocumentPy"')
        .replace('Namespace="Part"', 'Namespace="App"')
    )
    assert r.segments_freecad_pyxml(document)[0].label == "App.Document class"


def test_freecad_cpp_segments():
    cpp = [
        '#include "A.h"',
        "",
        "PROPERTY_SOURCE(Part::Box, Part::Primitive)",
        "",
        "Box::Box() {}",
        "PROPERTY_SOURCE_WITH_EXTENSIONS(Part::Cut, Part::Boolean)",
        "Cut::Cut() {}",
    ]
    assert r.segments_freecad_cpp(cpp, "src/A.cpp") == [
        r.Segment(3, 5, "Part::Box implementation"),
        r.Segment(6, 7, "Part::Cut implementation"),
    ]
    header = [
        "#pragma once",
        "class Foo;",
        "class PartExport Box : public Primitive",
        "{",
        "public:",
        "    Box();",
        "};",
        "",
        "class Other",
        "{",
        "};",
    ]
    assert r.segments_freecad_cpp(header, "src/A.h") == [
        r.Segment(3, 7, "Box declaration"),
        r.Segment(9, 11, "Other declaration"),
    ]
    with pytest.raises(ValueError):
        r.segments_freecad_cpp(["class Open", "{"], "src/B.h")


def test_python_public_api_segments_exclude_private_names():
    source = textwrap.dedent(
        '''\
        import x

        @decorator
        def solve_ivp(fun, t_span):
            """Solve it.

            More.
            """
            return 1

        def _private():
            """Private."""

        class OdeSolver:
            x = 1
        '''
    )
    assert r.public_names(
        "from .ivp import solve_ivp\nfrom .base import OdeSolver, DenseOutput\n"
    ) == ["solve_ivp", "OdeSolver", "DenseOutput"]
    assert r.segments_python_public_api(source, ["solve_ivp", "OdeSolver"]) == [
        r.Segment(3, 8, "solve_ivp signature and docstring"),
        r.Segment(14, 14, "OdeSolver signature and docstring"),
    ]


def test_rst_sections_admit_scipy_integrate_headings_only():
    lines = [
        "Release notes",
        "=============",
        "",
        "Highlights",
        "----------",
        "Text.",
        "",
        "`scipy.integrate` improvements",
        "------------------------------",
        "- solve_ivp gained X.",
        "",
        "=====================",
        "scipy.integrate other",
        "=====================",
        "Body.",
        "",
        "Other",
        "-----",
        "Tail.",
    ]
    assert r.segments_rst_sections(lines) == [
        r.Segment(8, 11, "`scipy.integrate` improvements"),
        r.Segment(12, 16, "scipy.integrate other"),
    ]


SANDCASTLE = (
    "<html><head><title>Application.ActiveAddInId Property</title>"
    "<script>var x = 1;</script><style>p {}</style></head><body>"
    '<div id="PageHeader">Revit 2025 API</div>'
    '<h1><span id="PageTitle">Application<span data-languageSpecificText="cpp=::|nu=.">'
    "</span>ActiveAddInId Property</span></h1>"
    "<p>Gets the   active\nadd-in id.</p>"
    "<table><tr><th>Name</th><th>Description</th></tr><tr><td>Id</td><td>The id.</td></tr>"
    "</table>"
    '<div class="codeSnippetContainer" id="ID0E">'
    '<div class="codeSnippetContainerTabs"><div id="ID0E_tab1" class="tab"><a href="#">C#</a>'
    '</div><div id="ID0E_tab2"><a href="#">VB</a></div></div>'
    '<div class="codeSnippetToolBar"><a>Copy</a></div>'
    '<div class="codeSnippetContainerCode" id="ID0E_code_Div1"><pre>\n'
    "public AddInId ActiveAddInId { get; }   \n\n  // indented\n</pre></div>"
    '<div class="codeSnippetContainerCode" id="ID0E_code_Div2"><pre>Public ReadOnly</pre></div>'
    "</div>"
    '<div id="PageFooter">Footer text</div></body></html>'
)


def test_sandcastle_text_exact_output():
    text, title = r.sandcastle_extract(SANDCASTLE)
    assert text == (
        "Application.ActiveAddInId Property\n"
        "Gets the active add-in id.\n"
        "Name | Description\n"
        "Id | The id.\n"
        "public AddInId ActiveAddInId { get; }\n"
        "\n"
        "  // indented\n"
    )
    assert title == "Application.ActiveAddInId Property"


def test_sandcastle_refuses_a_first_tab_other_than_csharp():
    page = SANDCASTLE.replace('<a href="#">C#</a>', '<a href="#">VB</a>', 1)
    with pytest.raises(ValueError, match="C#"):
        r.sandcastle_text(page)


# ---------------------------------------------------------------- §6.5 environment passages


def test_environment_text_and_ranges():
    assert r.format_ranges([2862, 2867, 2869, 2870, 3026, 3073]) == "2862,2867,2869-2870,3026,3073"
    assert r.parse_ranges("6,15,47-49,56-58") == [6, 15, 47, 48, 49, 56, 57, 58]
    with pytest.raises(ValueError):
        r.parse_ranges("5,3")
    conf = r.environment_block(
        owner="owner",
        repo="repo",
        commit="0123456789abcdef",
        path="conf.txt",
        derived=False,
        text="one\n  two\nthree\nfour\nfive\n",
        lines=[2, 4, 5],
    )
    pdf = r.environment_block(
        owner="owner",
        repo="repo",
        commit="0123456789abcdef",
        path="doc.pdf",
        derived=True,
        text="first\nsecond\n",
        lines=[1],
    )
    text, tokens = r.environment_passage("Synthetic 1.0", [conf, pdf], words)
    assert text == (
        "Environment passage v1 for Synthetic 1.0. Each block below is verbatim from the named "
        "pinned file; nothing here was executed.\n"
        "[owner/repo@0123456789ab conf.txt lines 2,4-5]\n"
        "  two\nfour\nfive\n"
        "[owner/repo@0123456789ab doc.pdf (text extraction) lines 1]\n"
        "first"
    )
    assert tokens == words(text)
    with pytest.raises(ValueError, match="600"):
        r.environment_passage("Synthetic 1.0", [conf], lambda s: 601)


# ---------------------------------------------------------------- §9 G7 metrics


def test_holdout_line_test_hand_computed():
    gis = [
        chunk("g1", file_index=0, start=1, end=2, text="alpha beta\nalpha gamma"),
        chunk("g2", file_index=1, start=1, end=2, text="delta\nepsilon"),
        chunk("g3", file_index=2, start=1, end=1, text="zeta eta"),
    ]
    # g1 holds out line 1 (tie) and still matches "alpha"; g2 and g3 cannot match themselves.
    assert r.holdout_line_test(gis) == {
        "n": 3,
        "hits": 1,
        "hit_at_3": 0.333333333,
        "mrr": 0.333333333,
    }
    aec = [
        chunk(
            "c", file_index=0, start=1, end=2, text="kappa\nkappa lam", category="aec_automation"
        ),
        chunk("d1", file_index=1, text="kappa lam", category="aec_automation"),
        chunk("d2", file_index=2, text="kappa lam", category="aec_automation"),
        chunk("d3", file_index=3, text="kappa lam", category="aec_automation"),
    ]
    # c holds out "kappa lam" and ranks fourth behind d1-d3; the single-line chunks miss.
    assert r.holdout_line_test(aec) == {"n": 4, "hits": 0, "hit_at_3": 0.0, "mrr": 0.0625}


def test_overlapping_windows_lose_the_held_out_line_too():
    shared = [
        chunk("c", file_key="f", file_index=0, start=1, end=2, text="alpha\nalpha b1 b2 b3 b4"),
        chunk("w", file_key="f", file_index=0, start=2, end=3, text="alpha b1 b2 b3 b4\nzed"),
    ]
    # c holds out line 2, which w shares. Removed from both, w keeps only "zed", so c ranks
    # first (RR 1); had w kept line 2, c would rank second. w misses its own test.
    assert r.holdout_line_test(shared) == {"n": 2, "hits": 1, "hit_at_3": 0.5, "mrr": 0.5}


def test_gain_pairs_follow_the_published_gis_order():
    ids = [f"gis_scripting-{n:02d}" for n in range(1, 11)]
    pairs = {k[-2:]: v[-2:] for k, v in r.gain_pairs(ids).items()}
    assert pairs == {
        "01": "10",
        "02": "07",
        "03": "09",
        "04": "06",
        "05": "08",
        "06": "02",
        "07": "03",
        "08": "04",
        "09": "01",
        "10": "05",
    }


def test_gain_and_stability_hand_computed_on_two_categories():
    foo = chunk("foo", file_index=0, text="FooBar alpha", tokens=5)
    baz = chunk("baz", file_index=1, text="BazQux beta", tokens=5)
    cad = chunk("cad", file_index=2, text="Part::Box volume", tokens=5, category="cad_apis")
    tasks = [
        {
            "id": "gis_scripting-01",
            "category": "gis_scripting",
            "brief": "Use FooBar here. Then BazQux there.",
        },
        {"id": "gis_scripting-02", "category": "gis_scripting", "brief": "Find BazQux."},
        {"id": "cad_apis-01", "category": "cad_apis", "brief": "Build a Part::Box. Read volume."},
    ]
    selections = {"gis_scripting-01": [foo, baz], "gis_scripting-02": [], "cad_apis-01": [cad]}
    metrics = r.retrieval_metrics(
        tasks, {"gis_scripting": [foo, baz], "cad_apis": [cad]}, {}, selections
    )
    gis = metrics["per_category"]["gis_scripting"]
    # 01: recall 1 own, 0 for partner 02 -> 1; 02: 0 own, 1 from 01's passages -> -1.
    assert gis["gain"] == 0.0
    rows = {row["task_id"]: row for row in metrics["tasks"]}
    assert rows["gis_scripting-01"]["gain"] == 1.0 and rows["gis_scripting-02"]["gain"] == -1.0
    # Dropping either sentence keeps one of the two passages: J = 1/2 twice.
    assert rows["gis_scripting-01"]["stability"] == 0.5
    assert rows["gis_scripting-02"]["stability"] is None
    assert gis["stability"] == 0.5 and gis["stability_left_out"] == ["gis_scripting-02"]
    cad_row = rows["cad_apis-01"]
    # Each one-sentence query still selects the only cad chunk: J = 1.
    assert cad_row["stability"] == 1.0 and cad_row["gain"] == 0.0
    assert metrics["per_category"]["cad_apis"]["corpus_recall"] == 1.0
    assert metrics["combined_index"]["per_category"]["cad_apis"] == 1.0
    assert metrics["uneven_treatment"]["empty_indexes"] == [
        "aec_automation",
        "structural_analysis",
        "simulation",
    ]
    assert not metrics["uneven_treatment"]["pass"]


def test_g5_tokens_and_ngrams():
    assert r.g5_tokens("Use Part::Box, e.g. 3.5!") == ["use", "part", "box", "e", "g", "3", "5"]
    assert r.ngrams(["a", "b", "c"], 2) == {("a", "b"), ("b", "c")}
    assert r.ngrams(["a"], 8) == set()


def test_a_passage_never_starts_on_a_doc_comment_closer_or_ends_on_its_opener():
    lines = [f"int v{n} = {n};" for n in range(1, 61)]
    for first in (14, 30):
        lines[first - 1], lines[first], lines[first + 1] = "/** Doc comment opens", " * body", " */"
    text = "\n".join(lines) + "\n"
    live = r.live_code(text, "c")
    assert {14, 15, 16, 30, 31, 32} <= {n for a, b in live.no_boundary for n in range(a, b + 1)}
    rows, _ = r.chunk_segments(text, [r.Segment(1, 60, "file")], live, lambda t: 10)
    assert len(rows) > 1
    for row in rows:
        shown = row["text"].split("\n")
        assert not shown[0].strip().startswith("*/") and not shown[-1].strip().startswith("/**")
        assert not (row["start"] in (16, 32) or row["end"] in (14, 30))


def test_header_stops_at_region_directives_and_strips_module_string_quotes():
    cs = textwrap.dedent(
        """\
        #region Header
        // Copyright (C) 2010-2021 by Synthetic Author, Example Inc. All rights reserved.
        #endregion // Header
        using System;
        """
    )
    live = r.live_code(cs, "cs")
    assert (
        r.file_header(r.split_lines(cs), live.removed)
        == "Copyright (C) 2010-2021 by Synthetic Author, Example Inc. All rights reserved."
    )
    py = (
        '"""Copyright 2023 Synthetic Co.\n\nLicensed under the Apache License, Version 2.0 '
        '(the "License");\nyou may not use this file except in compliance with the License.\n"""\n'
        "import os\n"
    )
    # Treat the module string as the banner, as PY-3 does for a license banner.
    lines = r.split_lines(py)
    header = r.file_header(lines, [(1, 5, "license_banner")])
    assert header == "Copyright 2023 Synthetic Co."


def test_header_from_multiline_module_string_without_blank_line_drops_license_body():
    py = (
        '"""Copyright 2023 Synthetic Co.\n'
        'Licensed under the Apache License, Version 2.0 (the "License");\n'
        'you may not use\n"""\nimport os\n'
    )
    header = r.file_header(r.split_lines(py), [(1, 4, "license_banner")])
    assert header == "Copyright 2023 Synthetic Co."


@pytest.mark.parametrize("quote", ['"""', "'''"])
def test_header_from_module_string_with_opener_on_its_own_line_drops_license_body(quote):
    py = (
        f"{quote}\n"
        "Copyright 2023 Synthetic Co.\n"
        'Licensed under the Apache License, Version 2.0 (the "License");\n'
        f"you may not use\n{quote}\nimport os\n"
    )
    live = r.live_code(py, "python")
    assert r.file_header(r.split_lines(py), live.removed) == "Copyright 2023 Synthetic Co."


def test_sandcastle_collapses_whitespace_across_inline_tags_and_breaks_lines_in_pre():
    assert r.sandcastle_text("<p>Gets the active <b> add-in </b> identifier.</p>") == (
        "Gets the active add-in identifier.\n"
    )
    assert r.sandcastle_text("<pre>a<div>b</div>c</pre>") == "a\nb\nc\n"


# --------------------------------------------- hold-out test against a from-scratch oracle


def holdout_oracle(chunks):
    """§9 G7 step by step, rebuilding the whole BM25 index from scratch for every hold-out."""
    n = len(chunks)
    base = r.BM25Index([r.terms(c.text) for c in chunks])
    lines = [dict(zip(c.live_line_numbers(), c.text.split("\n"), strict=True)) for c in chunks]
    hits, reciprocal = 0, []
    for i, c in enumerate(chunks):
        best = None
        for number in sorted(lines[i]):
            distinct = sorted(set(r.terms(lines[i][number])))
            if not distinct:
                continue
            weight = round(sum(base.idf(t) for t in distinct), r.SCORE_DECIMALS)
            if best is None or weight > best[0]:  # a tie goes to the lower line number
                best = (weight, number, distinct)
        if best is None:
            reciprocal.append(0.0)
            continue
        _, number, query = best
        documents = []
        for j, other in enumerate(chunks):
            if other.file_key == c.file_key and number in lines[j]:
                kept = [t for k, t in sorted(lines[j].items()) if k != number]
                documents.append(r.terms("\n".join(kept)))
            else:
                documents.append(r.terms(other.text))
        scores = r.BM25Index(documents).scores(query)

        def key(j, scores=scores):
            o = chunks[j]
            return (-round(scores[j], r.SCORE_DECIMALS), o.file_index, o.start, o.end, o.chunk_key)

        if round(scores[i], r.SCORE_DECIMALS) <= 0:
            reciprocal.append(0.0)
            continue
        rank = 1 + sum(1 for j in range(n) if j != i and key(j) < key(i))
        hits += rank <= 3
        reciprocal.append(1.0 / rank)
    return {
        "n": n,
        "hits": hits,
        "hit_at_3": round(hits / n, r.SCORE_DECIMALS),
        "mrr": round(sum(reciprocal) / n, r.SCORE_DECIMALS),
    }


def random_corpus(seed):
    import random

    rng = random.Random(seed)
    vocabulary = ["alpha", "beta", "gamma", "delta", "kappa", "sigma", "omega", "zeta"]
    files = {
        f"f{k}": [" ".join(rng.choices(vocabulary, k=rng.randint(1, 3))) for _ in range(6)]
        for k in range(rng.randint(1, 3))
    }
    chunks = []
    for index, (key, file_lines) in enumerate(sorted(files.items())):
        for _ in range(rng.randint(2, 4)):
            start = rng.randint(1, 6)
            end = rng.randint(start, min(6, start + 2))
            text = "\n".join(file_lines[start - 1 : end])
            chunks.append(
                chunk(
                    f"{key}#{start}-{end}-{len(chunks)}",
                    file_key=key,
                    file_index=index,
                    start=start,
                    end=end,
                    text=text,
                )
            )
    return chunks


def test_holdout_line_test_equals_a_from_scratch_oracle_on_random_corpora():
    seen = set()
    for seed in range(1500):
        corpus = random_corpus(seed)
        got = r.holdout_line_test(corpus)
        assert got == holdout_oracle(corpus), seed
        seen.add((got["hits"] > 0, 0 < got["hit_at_3"] < 1))
    assert len(seen) >= 3  # hits and misses both occur


def test_a_chunk_that_ranks_exactly_third_is_a_hit_at_3():
    def aec(key, index, text, start=1, end=1):
        return chunk(
            key, file_index=index, start=start, end=end, text=text, category="aec_automation"
        )

    chunks = [
        aec("c", 0, "kappa\nkappa lam", end=2),
        aec("d1", 1, "kappa lam"),
        aec("d2", 2, "kappa lam"),
        aec("e1", 3, "unrelated one"),
        aec("e2", 4, "unrelated two"),
    ]
    # c holds out "kappa lam" and keeps "kappa": it ranks third behind d1 and d2.
    assert r.holdout_line_test(chunks) == {
        "n": 5,
        "hits": 1,
        "hit_at_3": 0.2,
        "mrr": 0.066666667,
    }


def test_top_raw_is_the_maximum_raw_score_and_the_bonus_can_reorder_the_ranking():
    chunks = [
        chunk("api", file_index=0, text="Radius1 attribute of the cone"),
        chunk(
            "noise",
            file_index=1,
            text="cone radius height value attribute cone cone value height radius attribute",
        ),
        chunk("other", file_index=2, text="unrelated material about nothing"),
    ]
    brief = "Set the Radius1 value of the cone attribute height"
    result = r.CategoryRetriever(chunks).retrieve(brief)
    raw = r.bm25_scores([c.text for c in chunks], brief)
    assert result.top_raw == max(raw) == raw[1] > raw[0]  # the top raw score is not the first row
    assert [c.chunk.chunk_key for c in result.ranking] == ["api", "noise", "other"]
    assert result.ranking[0].r_final == round(
        raw[0] + 0.5 * max(raw), 9
    )  # lower raw, wins on bonus
    assert result.ranking[0].r_raw < result.ranking[1].r_raw


def test_the_floor_is_a_fifth_of_the_top_final_score_not_the_raw_score():
    top, weak = chunk("top", file_index=0), chunk("weak", file_index=1)
    rows = ranked((top, 5.0, 10.0, 2), (weak, 1.5, 1.5, 0))
    selected, decisions, floor = r.select_ranked(rows)
    assert floor == 2.0
    assert [x.chunk_key for x in selected] == ["top"]
    assert [x.decision for x in decisions] == ["selected", "below_floor"]


def test_overlap_is_decided_on_the_end_line_too():
    early = chunk("early", file_key="f", file_index=0, start=1, end=16)
    late = chunk("late", file_key="f", file_index=0, start=16, end=31)
    for order in ((early, late), (late, early)):
        rows = ranked((order[0], 3, 3, 0), (order[1], 2, 2, 0))
        assert [x.decision for x in r.select_ranked(rows)[1]] == ["selected", "overlap"]
    ends_on_environment = chunk("e", file_key="g", file_index=1, start=1, end=23)
    rows = ranked((ends_on_environment, 1, 1, 0))
    assert [x.decision for x in r.select_ranked(rows, {"g": [23]})[1]] == ["overlap"]


def test_stability_of_two_empty_selections_is_one():
    unrelated = chunk("u", file_index=0, text="zzz yyy xxx vvv")
    task = {
        "id": "gis_scripting-01",
        "category": "gis_scripting",
        "brief": "Qqq one here. Www two there.",
    }
    metrics = r.retrieval_metrics([task], {"gis_scripting": [unrelated]}, {}, {task["id"]: []})
    assert metrics["per_category"]["gis_scripting"]["stability"] == 1.0


def _hhk_with_pages(count):
    pages = "\n".join(
        f'  <param name="Local" value="html/{n:08x}-0000-0000-0000-000000000000.htm">'
        for n in range(count)
    )
    return (
        '<HTML><BODY><UL><LI> <OBJECT type="text/sitemap">\n'
        '  <param name="Name" value="FooBar class">\n'
        f"{pages}\n  </OBJECT></UL></BODY></HTML>\n"
    )


def test_the_inclusive_caps_accept_exactly_the_limit():
    block = r.environment_block(
        owner="o", repo="r", commit="0" * 16, path="p.txt", derived=False, text="a\n", lines=[1]
    )
    assert r.environment_passage("T 1", [block], lambda s: 600)[1] == 600
    briefs = ["Use FooBar here."]
    assert len(r.adn_select(_hhk_with_pages(60), briefs)["pages"]) == 60
    with pytest.raises(ValueError, match="OP-5"):
        r.adn_select(_hhk_with_pages(61), briefs)


def test_an_underscore_is_an_identifier_character_and_stability_listing_is_strict():
    assert r.identifier_in("Radius1", "set Radius1 now") and not r.identifier_in(
        "Radius1", "set _Radius1 now"
    )
    assert r.STABILITY_LIST_BELOW == 0.34
    assert r.is_unstable(0.3399) and not r.is_unstable(0.34) and not r.is_unstable(0.5)


@pytest.mark.parametrize(
    "parts, evidence_relative, expected",
    [
        (("aec-course", "reviews", "note.md"), None, "forbidden path segment 'reviews'"),
        (("x", "human-review-reports", "a.md"), None, "forbidden path segment"),
        (("x", "human-adjudication-1", "a.md"), None, "forbidden path segment"),
        (("x", "human-amendments-2", "a.md"), None, "forbidden path segment"),
        (("x", ".rag-generator-design-20261120", "a.md"), None, "forbidden design directory"),
        (("x", ".rubric-v2-review-20261120", "a.md"), None, "forbidden design directory"),
        (("analysis", "x.json"), "analysis/x.json", "forbidden evidence area analysis/"),
        (("x", "data.jsonl"), None, "forbidden file name"),
        (("references", "engineering-v1.json"), "references/engineering-v1.json", None),
    ],
)
def test_the_section_1_4_deny_list_has_every_element(parts, evidence_relative, expected):
    reason = r.forbidden_path_reason(parts, evidence_relative)
    assert (reason is None) if expected is None else (reason and expected in reason)
