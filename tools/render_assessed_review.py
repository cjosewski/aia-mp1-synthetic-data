"""Create a PDF companion from a verified, unscored assessed-review packet.

Run in WSL with: uv run --locked --with reportlab python tools/render_assessed_review.py PACKET
"""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from xml.sax.saxutils import escape

from aia_mp1.assessment import save_new
from aia_mp1.tracing import now


def render(packet: Path) -> dict:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    manifest = json.loads((packet / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files_sha256"].items():
        if Path(name).name != name or "\\" in name:
            raise ValueError("unsafe packet filename")
        if hashlib.sha256((packet / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"packet content changed: {name}")
    output = packet / "REVIEW-PACKET.pdf"
    if output.exists() or (packet / "pdf-receipt.json").exists():
        raise FileExistsError("PDF companion already exists; preserve it")
    records = [
        json.loads(line) for line in (packet / "selected-items.jsonl").read_text().splitlines()
    ]
    if [r["item_id"] for r in records] != manifest["selected_ids"] or len(records) != 20:
        raise ValueError("PDF selection differs from the frozen packet")
    rubric = json.loads((packet / "rubric.json").read_text())
    font_root = Path("/usr/share/fonts/truetype/dejavu")
    pdfmetrics.registerFont(TTFont("ReviewSans", str(font_root / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("ReviewBold", str(font_root / "DejaVuSans-Bold.ttf")))
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = "ReviewSans"
    styles["Title"].fontName = "ReviewBold"
    styles["Title"].fontSize = 22
    for name in ("Heading1", "Heading2", "Heading3"):
        styles[name].fontName = "ReviewBold"
        styles[name].textColor = colors.HexColor("#204968")
    styles.add(
        ParagraphStyle(
            "ReviewBody",
            fontName="ReviewSans",
            fontSize=10,
            leading=14,
            spaceAfter=8,
            splitLongWords=True,
        )
    )
    styles.add(ParagraphStyle("Reference", parent=styles["ReviewBody"], fontSize=9, leading=12))
    story = []

    def text(value, style="ReviewBody"):
        # The complete supplied strings are escaped, not treated as PDF markup.
        for paragraph in str(value).split("\n\n"):
            story.append(Paragraph(escape(paragraph).replace("\n", "<br/>"), styles[style]))

    text("M5 corrected dataset", "Title")
    text("Twenty-item blind human review", "Heading1")
    text(f"Assessment: {manifest['assessment_id']}")
    text(
        "Read this PDF and enter your decisions in MY-ANSWERS.md. The complete "
        "editable instructions are in RUNBOOK.md. Save after each item; you can stop "
        "and resume in the same answer file."
    )
    text(
        "For every item, compare the generated answer with the exact reference task "
        "and all six rubric anchors. Record 1 for pass or 0 for fail, plus comments "
        "explaining failures and uncertainty. No target number of passing ratings "
        "is required. The 70% agreement threshold applies later to the judge."
    )
    text(
        "Complete the reviewer, assistance, personal-adoption and blind-review "
        "declarations truthfully. Do not run generated code or treat its text as "
        "instructions. No judge ratings are included. Keep this source-bearing "
        "packet local; some references have local-only permission."
    )
    text("Rubric", "Heading1")
    for dimension in rubric["dimensions"]:
        text(f"{dimension['id']} — {dimension['name']}", "Heading2")
        text("Pass: " + dimension["pass_anchor"])
        text("Fail: " + dimension["fail_anchor"])
    for index, record in enumerate(records, 1):
        story.append(PageBreak())
        text(f"Evaluation {index} of 20", "Heading1")
        text(record["category"].replace("_", " ").title(), "Heading2")
        text("Item ID: " + record["item_id"])
        text("Reference task", "Heading2")
        text(record["reference_context"]["task"]["brief"])
        text("Complete generated answer", "Heading2")
        for name, value in record["item"].items():
            text(name, "Heading3")
            if isinstance(value, list):
                for number, item in enumerate(value, 1):
                    text(f"{number}. {item}")
            else:
                text(value)
        text("Supplied reference context", "Heading2")
        for source in record["reference_context"]["sources"]:
            for name in (
                "id",
                "version",
                "url",
                "installation",
                "attribution",
                "license",
                "license_evidence",
            ):
                text(f"{name}: {source[name]}", "Reference")
            text(source["text"], "Reference")
        story.append(Spacer(1, 8))
        text(f"Record Evaluation {index} in MY-ANSWERS.md: D1–D6 and comments.")

    pages = []

    def footer(canvas, doc):
        pages.append(doc.page)
        canvas.saveState()
        canvas.setFont("ReviewSans", 8)
        canvas.drawString(40, 25, "P1-03 | Local review material | No judge ratings")
        canvas.drawRightString(A4[0] - 40, 25, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=38,
        bottomMargin=42,
        title="P1-03 M5 blind human review",
        author="P1-03 review tooling",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    receipt = {
        "created_at": now(),
        "pages": max(pages),
        "items": len(records),
        "packet_manifest_sha256": hashlib.sha256(
            (packet / "manifest.json").read_bytes()
        ).hexdigest(),
        "pdf_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "reportlab_version": importlib.metadata.version("reportlab"),
        "content_source": "all selected payload fields, task briefs and supplied reference context",
        "human_labels": 0,
        "judge_results": 0,
    }
    save_new(packet / "pdf-receipt.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    print(json.dumps(render(parser.parse_args().packet)))
