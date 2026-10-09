"""
Medication guide page (OSHC Compass)

Shows a student walking through getting medicine: doctor, pharmacy, pharmacist,
price, paying, and what Comprehensive OSHC and Extras pay. The animation lives in
a separate HTML file (same style as the hospital guide).

The brochure text in the guide is READ FROM THE PDF every time the PDF changes
(sentences, the $30 contribution, the annual limits, the Extras amounts, page numbers).
If a part can no longer be found in the PDF, the guide uses its saved text for that part
and this page shows a warning.

Folder layout:
    oshc_welcome.py                <- main page
    pages/Medication_Guide.py      <- this file
    medication_guide.html          <- the animation (main folder, or next to this file)
    OSHC_Brochure.pdf
"""

import json
import re
from pathlib import Path
from urllib.parse import quote

import pdfplumber
import streamlit as st
import streamlit.components.v1 as components

import auth


# ---------- Settings ----------

HOME_PAGE = "pages/1_Question.py"
ROOT = Path(__file__).parent.parent          # the main project folder
PDF_FILE = ROOT / "OSHC_Brochure.pdf"
GUIDE_HEIGHT = 900
SUPPORTED_LANGUAGES = ["en", "si", "fa", "vi", "id"]


def find_html() -> Path:
    """Find the animation file (main folder, this folder, "assets" or "images")."""
    here = Path(__file__).parent
    for folder in (ROOT, here, ROOT / "assets", ROOT / "images"):
        found = sorted(folder.glob("medication_guide*.html"))
        if found:
            return found[0]
    return ROOT / "medication_guide.html"


HTML_FILE = find_html()

# What we read from the PDF.
# key = name used in the HTML, label = what it is, where = which part of the brochure, pattern = how to find it.
# group 1 of the pattern is the value (if there is no group, the whole match is used).
HELP_PAGE = "help"      # the "If you need medication" page
RX_PAGE = "rx"          # the "Prescription medicines" page
EXTRAS_PAGE = "extras"  # the Extras table

READ_FROM_PDF = [
    # key, label, page, pattern
    ("pharmacy", "Pharmacy is the place to get medication", HELP_PAGE,
     r"A pharmacy is the place to go if you need to get medication\."),
    ("needRx", "Some medication needs a prescription", HELP_PAGE,
     r"Some medication can only be bought if you have been given a prescription from a doctor \(GP or specialist\)\."),
    ("pbs", "PBS and international visitors", HELP_PAGE,
     r"The government.s Pharmaceutical Benefits Scheme \(PBS\).*?pay the full price of the medication they need\."),
    ("help", "Comprehensive OSHC helps with prescription medicines", HELP_PAGE,
     r"(Comprehensive OSHC provides benefits towards the cost of eligible prescription medicines)[ ,.]"),
    ("eligible", "Only prescribed medicines are paid", RX_PAGE,
     r"Benefits are payable only for prescription medicines prescribed by a doctor \(GP or specialist\) to treat an illness, injury or condition\."),
    ("contribution", "Member contribution", RX_PAGE, r"Member contribution (\$[\d,]+)"),
    ("pct", "Amount Medibank pays", RX_PAGE, r"Amount we.ll pay \(maximum per item\) (\d+% of cost)"),
    ("annualSingle", "Annual limit, single", RX_PAGE, r"Annual limit . Single membership (\$[\d,]+)"),
    ("annualFamily", "Annual limit, couple or family", RX_PAGE,
     r"Annual limit . Couple/Family membership (\$[\d,]+ per member / \$[\d,]+ per membership)"),
    ("difference", "You pay the difference", RX_PAGE,
     r"If the cost of the prescription medicine is higher than the benefit we pay, you must pay the difference\."),
    ("notCovered", "Cosmetic and Excluded", RX_PAGE,
     r"We don.t pay benefits towards prescription medicines for cosmetic purposes or for prescription medicines that relate to an Excluded service\."),
    ("highCost", "High-cost medicines", RX_PAGE,
     r"It.s important to note that you may have large out-of-pocket expenses.*?cancer treatment\)\."),
    ("extrasCharge", "Extras: set charge", EXTRAS_PAGE, r"(Benefits will be paid after a set charge has been deducted)\.?"),
    ("healthy", "Extras: Healthy Start limit", EXTRAS_PAGE, r"Combined limit of (\$[\d,]+) for"),
]
# The Extras row for prescription pharmaceuticals: waiting period, Essential, Top 60, Top 75, Top 90
EXTRAS_ROW = r"Prescription pharmaceuticals \(non-PBS\) (\d+ months?) (\S+) (\$[\d,]+) (\$[\d,]+) (\$[\d,]+)"

PAGE_MARKERS = {                      # a phrase that is only on that page
    HELP_PAGE: "If you need medication",
    RX_PAGE: "Member contribution",
    EXTRAS_PAGE: "Prescription pharmaceuticals (non-PBS)",
}


# ---------- Reading the PDF ----------

@st.cache_data
def read_pages(pdf_path: str, modified_time: float) -> list:
    """The text of every PDF page (the number changes when the PDF changes)."""
    with pdfplumber.open(pdf_path) as pdf:
        return [p.extract_text() or "" for p in pdf.pages]


def _flat(text: str) -> str:
    """One line, single spaces."""
    return " ".join(text.split())


def _printed_number(text: str, fallback: int) -> int:
    """The page number printed at the bottom (a spread shows 'left middle right': use the middle)."""
    last = text.strip().split("\n")[-1].split()
    if last and all(w.isdigit() for w in last):
        return int(last[len(last) // 2])
    return fallback


def read_facts(pages: list):
    """Return (facts, page numbers, parts that were not found)."""
    flat = [_flat(t) for t in pages]
    found_page = {}
    for name, phrase in PAGE_MARKERS.items():
        found_page[name] = next((i for i, t in enumerate(flat) if phrase in t), None)

    facts, missing = {}, []
    numbers = {name: (_printed_number(pages[i], i + 1) if i is not None else None)
               for name, i in found_page.items()}

    for key, label, where, pattern in READ_FROM_PDF:
        i = found_page[where]
        match = re.search(pattern, flat[i], re.S) if i is not None else None
        if not match:
            missing.append(label)
            continue
        facts[key] = (match.group(1) if match.groups() else match.group(0)).strip()
        if key in ("help", "extrasCharge"):
            facts[key] += "."

    i = found_page[EXTRAS_PAGE]
    row = re.search(EXTRAS_ROW, flat[i]) if i is not None else None
    if row:
        wait, essential, top60, top75, top90 = row.groups()
        facts.update(extrasWait=wait, top60=top60, top75=top75, top90=top90,
                     essential=(essential + " each year") if essential.startswith("$") else "not covered")
    else:
        missing.append("Extras row: prescription pharmaceuticals (non-PBS)")

    pages_out = {k: v for k, v in numbers.items() if v}
    return facts, pages_out, missing


# ---------- Other helpers ----------

def get_language() -> str:
    lang = st.session_state.get("lang", "en")
    return lang if lang in SUPPORTED_LANGUAGES else "en"


@st.cache_data
def load_html(modified_time: float) -> str:
    """Cached, but reloads when the HTML file changes."""
    return HTML_FILE.read_text(encoding="utf-8")


# ---------- Page ----------

st.set_page_config(page_title="I need medication", layout="wide")
auth.require_login()

back_col, title_col = st.columns([1, 5])

with back_col:
    if st.button("← Back"):
        st.switch_page(HOME_PAGE)

with title_col:
    st.markdown("### How to get medication in Australia")
    st.caption(
        "Follow a student step by step: from the doctor to the pharmacy, "
        "and what Medibank OSHC pays. This is general information, not medical advice."
    )

# Read the facts from the PDF (if it fails, the guide still works with its saved text)
facts, page_numbers, missing = {}, {}, []
if PDF_FILE.exists():
    try:
        pdf_pages = read_pages(str(PDF_FILE), PDF_FILE.stat().st_mtime)
        facts, page_numbers, missing = read_facts(pdf_pages)
        if missing:
            st.warning(
                "Some parts could not be found in the brochure PDF any more (maybe the brochure changed). "
                "The guide shows its saved text for these parts, so please check them: "
                + "; ".join(missing)
            )
    except Exception as error:
        st.warning(f"Couldn't read the brochure PDF. The guide is showing its saved text. ({error})")
else:
    st.warning(f"Brochure PDF not found. Put it here: {PDF_FILE}")

# The guide itself
if HTML_FILE.exists():
    payload = {"facts": facts, "pages": page_numbers} if facts else {}
    html = load_html(HTML_FILE.stat().st_mtime).replace("__LANG__", get_language())
    html = html.replace("__PDF_DATA__", quote(json.dumps(payload, ensure_ascii=False), safe=""))
    components.html(html, height=GUIDE_HEIGHT, scrolling=True)
else:
    st.error(f"Can't find the guide file (medication_guide.html). Put it here: {HTML_FILE}")

# Show what was read from the PDF
if facts:
    with st.expander("See the text and numbers read from the brochure PDF"):
        st.caption(
            f"Printed pages: help {page_numbers.get('help', '?')}, prescription medicines "
            f"{page_numbers.get('rx', '?')}, Extras table {page_numbers.get('extras', '?')}."
        )
        for key, label, _, _ in READ_FROM_PDF:
            if key in facts:
                st.markdown(f"**{label}**")
                st.write(facts[key])
        st.markdown("**Extras: prescription pharmaceuticals (non-PBS)**")
        st.write(
            f"Waiting period {facts.get('extrasWait', '?')}. Essential Extras 75: {facts.get('essential', '?')}. "
            f"Top Extras 60 / 75 / 90: {facts.get('top60', '?')} / {facts.get('top75', '?')} / {facts.get('top90', '?')}."
        )
