"""Extract a retained PDF without rewriting text; record original/output/tool hashes.

Use the locked development environment. The receipt establishes extraction lineage,
not source permission or semantic correctness. Existing outputs are never replaced.
"""

import argparse
import hashlib
import json
from pathlib import Path

import pypdf


def extract(original: Path, output: Path, receipt: Path) -> None:
    if output.exists() or receipt.exists():
        raise ValueError("extraction outputs already exist")
    reader = pypdf.PdfReader(original)
    pages = [page.extract_text() for page in reader.pages]
    if not pages or any(not isinstance(page, str) or not page.strip() for page in pages):
        raise ValueError("PDF contains empty/unextractable pages; inspect before use")
    text = "\n".join(pages)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    value = {
        "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "extractor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "extractor_version": "pypdf " + pypdf.__version__,
        "method": "PdfReader; page.extract_text defaults; pages joined with LF; no rewriting",
        "pages": len(pages),
        "page_text_sha256": [hashlib.sha256(page.encode("utf-8")).hexdigest() for page in pages],
    }
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    extract(args.original, args.output, args.receipt)
