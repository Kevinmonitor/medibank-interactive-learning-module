"""
Make a claim: guide page (OSHC Compass)

The student first chooses how to claim (Online Member Services or app, Online Claims
Form, mail, store), then walks through the steps. The animation lives in a separate HTML file.

The brochure text in the guide is READ FROM THE PDF every time the PDF changes
(when you can start claiming, waiting periods, phone numbers and hours, the 100% / 85% rates, page numbers).
If a part can no longer be found in the PDF, the guide uses its saved text for that part
and this page shows a warning.

The steps of each way to claim (website and member portal) are NOT in the PDF. They are saved
text inside claim_guide.html (see WEB_DATE there). Check them now and then.

Folder layout:
    oshc_welcome.py                <- main page
    pages/Claim_Guide.py           <- this file
    claim_guide.html                <- the animation (main folder, or next to this file)
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
GUIDE_HEIGHT = 920
SUPPORTED_LANGUAGES = ["en", "si", "fa", "vi", "id"]


def find_html() -> Path:
    """Find the animation file (main folder, this folder, "assets" or "images")."""
    here = Path(__file__).parent
    for folder in (ROOT, here, ROOT / "assets", ROOT / "images"):
        found = sorted(folder.glob("claim_guide*.html"))
        if found:
            return found[0]
    return ROOT / "claim_guide.html"


HTML_FILE = find_html()

# What we read from the PDF.
# (key used in the HTML, label, where it is, pattern). Group 1 of the pattern is the value
# (if there is no group, the whole match is used).
BEGIN, WAIT, SUPPORT, CONTACT, MEDICAL, RX = "begin", "wait", "support", "contact", "medical", "rx"

READ_FROM_PDF = [
    ("begin", "When you can begin claiming", BEGIN,
     r"You can begin claiming when your membership has been activated and your relevant waiting periods are served\."),
    ("oms", "Online Member Services (OMS)", BEGIN,
     r"Medibank OSHC OMS is a convenient way of managing your membership online\."),
    ("register", "Register or download the app", BEGIN,
     r"You can register at medibankoshc\.com\.au or download the Medibank OSHC app\."),
    ("waiting", "No benefits in a waiting period", WAIT,
     r"We won.t pay benefits for any items purchased or services received while you are serving a waiting period\."),
    ("appClaim", "The app can make claims", SUPPORT, r"Make claims for most medical services"),
    ("storeUrl", "Store finder", CONTACT, r"(medibank\.com\.au/locations) to find your nearest Medibank store"),
    ("phoneAu", "Phone (in Australia)", CONTACT, r"(134 148) \(from within Australia\)"),
    ("phoneOs", "Phone (outside Australia)", CONTACT, r"(\+61 3 9862 1095) \(from outside Australia\)"),
    ("hours", "Phone hours", CONTACT, r"Available (Monday to Friday 8am-8pm AEST)"),
    ("mustPayDiff", "You pay the difference", MEDICAL,
     r"You must pay any difference between the benefit we pay and the actual fee charged for the service\."),
    ("contribution", "Prescription medicines: member contribution", RX, r"Member contribution (\$[\d,]+)"),
    ("pct", "Prescription medicines: amount Medibank pays", RX, r"Amount we.ll pay \(maximum per item\) (\d+% of cost)"),
]

# A phrase that is only on that page
PAGE_MARKERS = {
    BEGIN: "You can begin claiming when your membership",
    WAIT: "pay benefits for any items purchased",
    SUPPORT: "24/7 Student Health and Support Line. Need extra support?",
    CONTACT: "to find your nearest Medibank store",
    MEDICAL: "Medical cover pays towards",
    RX: "Member contribution",
}


# ---------- Reading the PDF ----------

@st.cache_data
def read_pdf(pdf_path: str, modified_time: float) -> dict:
    """The text and the tables of every PDF page (reloads when the PDF changes)."""
    with pdfplumber.open(pdf_path) as pdf:
        return {
            "pages": [p.extract_text() or "" for p in pdf.pages],
            "tables": [p.extract_tables() for p in pdf.pages],
        }


def _flat(text: str) -> str:
    """One line, single spaces."""
    return " ".join(text.split())


def _page_label(index: int, pages: list) -> str:
    """'on page 5' (the printed number), or the cover pages, which have no number."""
    last = pages[index].strip().split("\n")[-1].split()
    if last and all(w.isdigit() for w in last):
        return f"on page {last[len(last) // 2]}"
    if index >= len(pages) - 1:
        return "on the back cover"
    return "on the inside front cover" if index <= 1 else f"on PDF page {index + 1}"


def read_rates(tables: list) -> dict:
    """The 'We pay 100% / 85% of the MBS fee for' table: which service gets which percentage."""
    rates, current = {}, None
    for table in tables:
        if not table or not table[0] or "Included services" not in (table[0][0] or ""):
            continue
        for left, right in (r for r in table[1:] if len(r) >= 2):
            percent = re.search(r"(\d+)%", left or "")
            current = percent.group(1) + "%" if percent else current
            text = _flat(right or "").lower()
            if current and "general practitioner" in text:
                rates["gpRate"] = current
            elif current and "other medical services" in text:
                rates["specRate"] = current
    return rates


def read_facts(data: dict):
    """Return (facts, page labels, parts that were not found)."""
    pages, flat = data["pages"], [_flat(t) for t in data["pages"]]
    found = {name: next((i for i, t in enumerate(flat) if phrase in t), None)
             for name, phrase in PAGE_MARKERS.items()}

    facts, missing = {}, []
    for key, label, where, pattern in READ_FROM_PDF:
        i = found[where]
        match = re.search(pattern, flat[i], re.S) if i is not None else None
        if not match:
            missing.append(label)
            continue
        value = (match.group(1) if match.groups() else match.group(0)).strip()
        facts[key] = re.sub(r"[\^#&]+(?=[\s,.]|$)", "", value)       # footnote marks like ^ # &

    # The Medical table (100% / 85% of the MBS fee)
    i = found[MEDICAL]
    rates = read_rates(data["tables"][i]) if i is not None else {}
    for key, label in (("gpRate", "GP consultations: % of MBS fee"),
                       ("specRate", "Specialists, pathology, x-rays: % of MBS fee")):
        if key in rates:
            facts[key] = rates[key]
        else:
            missing.append(label)

    labels = {name: _page_label(i, pages) for name, i in found.items() if i is not None}
    return facts, labels, missing


# ---------- Other helpers ----------

def get_language() -> str:
    lang = st.session_state.get("lang", "en")
    return lang if lang in SUPPORTED_LANGUAGES else "en"


@st.cache_data
def load_html(modified_time: float) -> str:
    """Cached, but reloads when the HTML file changes."""
    return HTML_FILE.read_text(encoding="utf-8")


# ---------- Page ----------

st.set_page_config(page_title="I need to make a claim", layout="wide")
auth.require_login()

back_col, title_col = st.columns([1, 5])

with back_col:
    if st.button("← Back"):
        st.switch_page(HOME_PAGE)

with title_col:
    st.markdown("### How to make a claim")
    st.caption(
        "Choose how you want to claim, then follow a student step by step. "
        "This is general information. Check the Medibank website for the latest steps."
    )

# Read the facts from the PDF (if it fails, the guide still works with its saved text)
facts, page_numbers, missing = {}, {}, []
if PDF_FILE.exists():
    try:
        pdf_data = read_pdf(str(PDF_FILE), PDF_FILE.stat().st_mtime)
        facts, page_numbers, missing = read_facts(pdf_data)
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
    st.error(f"Can't find the guide file (claim_guide.html). Put it here: {HTML_FILE}")

# Show what was read from the PDF
if facts:
    with st.expander("See the text and numbers read from the brochure PDF"):
        st.caption("Where it is in the brochure: " + ", ".join(f"{k} {v}" for k, v in page_numbers.items()) + ".")
        st.caption("The steps for each way to claim come from the Medibank website and member portal. "
                   "They are saved text inside claim_guide.html (see WEB_DATE there), not read from the PDF.")
        st.markdown("**MBS fee rates (Medical table)**")
        st.write(f"GP consultations: {facts.get('gpRate', '?')}. "
                 f"Specialists, pathology and x-rays: {facts.get('specRate', '?')}.")
        for key, label, _, _ in READ_FROM_PDF:
            if key in facts:
                st.markdown(f"**{label}**")
                st.write(facts[key])
