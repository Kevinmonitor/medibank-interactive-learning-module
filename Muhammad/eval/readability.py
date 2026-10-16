"""
Measure the reading grade of the real Medibank OSHC documents.

This is the proof behind the "Policy documents" figure on the insights page.
Anyone can re-run it and get the same numbers, which is what makes the claim
defensible.

    python eval/readability.py

It reads the published PDFs in data/, runs the Flesch-Kincaid grade formula via
the standard `textstat` library over the full extracted text of each, and
writes the result to data/readability.json so the app can show a measured
number without needing the PDFs at run time (they are not deployed).
"""
import json
import re
from pathlib import Path

import pdfplumber
import textstat

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def pdf_text(path):
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            out.append(page.extract_text() or "")
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def main():
    pdfs = sorted(DATA.glob("*.pdf"))
    if not pdfs:
        print("No PDFs in data/. Nothing to measure.")
        return

    per_doc, all_text = {}, []
    print(f"{'document':45}{'words':>8}{'FK grade':>10}{'ease':>8}")
    print("-" * 71)
    for p in pdfs:
        text = pdf_text(p)
        all_text.append(text)
        fk = round(textstat.flesch_kincaid_grade(text), 1)
        ease = round(textstat.flesch_reading_ease(text), 1)
        per_doc[p.name] = {"words": len(text.split()), "fk_grade": fk,
                           "reading_ease": ease}
        print(f"{p.name:45}{len(text.split()):>8}{fk:>10.1f}{ease:>8.1f}")

    combined = " ".join(all_text)
    doc_grade = round(textstat.flesch_kincaid_grade(combined), 1)
    ease = round(textstat.flesch_reading_ease(combined), 1)
    print("-" * 71)
    print(f"{'ALL THREE COMBINED':45}{len(combined.split()):>8}{doc_grade:>10.1f}{ease:>8.1f}")

    out = {
        "document_grade": doc_grade,
        "reading_ease": ease,
        "method": "Flesch-Kincaid grade via textstat, over the full extracted "
                  "text of the published Medibank OSHC PDFs",
        "per_document": per_doc,
    }
    (DATA / "readability.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {DATA / 'readability.json'}")


if __name__ == "__main__":
    main()
