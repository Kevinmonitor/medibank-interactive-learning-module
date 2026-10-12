"""
If you get sick: guide page (OSHC Compass)

The student first chooses how sick they feel (GP, not sure, emergency), then walks
through the steps for that case. The animation lives in a separate HTML file.

The brochure text in the guide is READ FROM THE PDF every time the PDF changes
(sentences, the 100% / 85% MBS rates, the phone number, the app features, page numbers).
If a part can no longer be found in the PDF, the guide uses its saved text for that part
and this page shows a warning.

Folder layout:
    oshc_welcome.py                <- main page
    pages/Sick_Guide.py            <- this file
    sick_guide.html                <- the animation (main folder, or next to this file)
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
        found = sorted(folder.glob("sick_guide*.html"))
        if found:
            return found[0]
    return ROOT / "sick_guide.html"


HTML_FILE = find_html()

# What we read from the PDF.
# (key used in the HTML, label, where it is, pattern). Group 1 of the pattern is the value
# (if there is no group, the whole match is used).
SICK, MEDICAL, PROVIDER, SUPPORT, WHY, AMB, STATES, HOSPITAL = (
    "sick", "medical", "provider", "support", "why", "amb", "states", "hospital")

READ_FROM_PDF = [
    ("gpFirst", "GP is the first point of contact", SICK,
     r"If you get sick, usually a general practitioner \(GP\) is the first point of contact unless it is an emergency\."),
    ("minor", "Minor problems: stomach ache, cough, fever", SICK,
     r"You can visit a GP for more minor medical problems such as a stomach ache, cough or a fever\."),
    ("gpCan", "GP can prescribe and refer", SICK,
     r"They can also prescribe medicine to treat your condition or refer you for a blood test, x-ray or to a specialist doctor if you need one\."),
    ("pays1", "Medibank pays out-of-hospital services", SICK,
     r"Medibank will pay towards out-of-hospital medical services.*?as long as the service is Included under your cover\."),
    ("gap", "You pay the difference (out-of-pocket)", SICK,
     r"If the doctor charges more than the amount we pay, you.ll need to pay the difference\. This is often referred to as an out-of-pocket expense\."),
    ("mbsDef", "What the MBS fee is", MEDICAL,
     r"The Medicare Benefits Schedule \(MBS\) is a list.*?known as the MBS fee\."),
    ("findTool", "Find a Provider tool", PROVIDER,
     r"Use our Find a Provider search tool.*?after-hours doctor home visits\)\."),
    ("directBilling", "Direct Billing", PROVIDER,
     r"A Medibank OSHC Direct Billing provider is.*?not paid for by Medibank\."),
    ("phone", "Support line phone number", SUPPORT, r"You can call (1800 \d{3} \d{3}) anytime"),
    ("nurseLine", "24/7 Student Health and Support Line", SUPPORT,
     r"You can call 1800 \d{3} \d{3} anytime, day or night.{0,3} for health advice.*?and more\."),
    ("callback", "Not always 24/7", SUPPORT,
     r"Some services may not be available 24/7 and call back may be required\."),
    ("appIntro", "Medibank OSHC app", SUPPORT, r"Designed for international students.*?easy\."),
    ("appDoctor", "App: online doctor", SUPPORT, r"Have an online consultation with a qualified medical doctor"),
    ("appFind", "App: find a Direct Billing doctor", SUPPORT, r"Find a Direct Billing doctor nearby"),
    ("appClaim", "App: make claims", SUPPORT, r"Make claims for most medical services"),
    ("langs", "Interpreter languages", WHY, r"access to telephone interpreter services.*?in around (\d+) languages"),
    ("ambulanceHelp", "Emergency ambulance", AMB, r"(eligible emergency ambulance services Australia-wide)"),
    ("ambulanceNote", "When the ambulance is covered", AMB,
     r"# (For ambulance attendance or transportation.*?any other way\.)"),
    ("ambulanceState", "TAS and QLD ambulance schemes", STATES,
     r"(TAS and QLD have State schemes to cover ambulance services)(?=.*for residents of those States\.)"),
    ("emergencyHospital", "Go to hospital in an emergency", HOSPITAL,
     r"You.ll generally need to go to the hospital if you have a medical emergency or if you need an operation\."),
    ("facilityMeaning", "What a facility fee is", WHY,
     r"A .facility fee. is an amount that may be charged by private hospitals for attendance in their accident and emergency department\."),
]

# A phrase that is only on that page
PAGE_MARKERS = {
    SICK: "If you get sick.",
    MEDICAL: "Medical cover pays towards",
    PROVIDER: "Find a Provider search tool",
    SUPPORT: "24/7 Student Health and Support Line. Need extra support?",
    WHY: "telephone interpreter services",
    AMB: "eligible emergency ambulance services",
    STATES: "TAS and QLD have State schemes",
    HOSPITAL: "If you need to go to hospital.",
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


def _printed_number(text: str, fallback: int) -> int:
    """The page number printed at the bottom (a spread shows 'left middle right': use the middle)."""
    last = text.strip().split("\n")[-1].split()
    if last and all(w.isdigit() for w in last):
        return int(last[len(last) // 2])
    return fallback


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
    """Return (facts, page numbers, parts that were not found)."""
    pages, flat = data["pages"], [_flat(t) for t in data["pages"]]
    found = {name: next((i for i, t in enumerate(flat) if phrase in t), None)
             for name, phrase in PAGE_MARKERS.items()}
    numbers = {name: (_printed_number(pages[i], i + 1) if i is not None else None)
               for name, i in found.items()}

    facts, missing = {}, []
    for key, label, where, pattern in READ_FROM_PDF:
        i = found[where]
        match = re.search(pattern, flat[i], re.S) if i is not None else None
        if not match:
            missing.append(label)
            continue
        value = (match.group(1) if match.groups() else match.group(0)).strip()
        facts[key] = re.sub(r"[\^#&]+(?=[\s,.]|$)", "", value)       # footnote marks like ^ # &
        if key == "ambulanceState":
            facts[key] += " for residents of those States."      # the end of the sentence sits further on

    # The Medical table (100% / 85% of the MBS fee)
    i = found[MEDICAL]
    rates = read_rates(data["tables"][i]) if i is not None else {}
    for key, label in (("gpRate", "GP consultations: % of MBS fee"),
                       ("specRate", "Specialists, pathology, x-rays: % of MBS fee")):
        if key in rates:
            facts[key] = rates[key]
        else:
            missing.append(label)

    # The hospital fee sentence has a stray "+" in the PDF text
    i = found[HOSPITAL]
    match = re.search(r"(If you need to attend a public or private hospital.s accident and emergency "
                      r"department, we.ll cover 100% of any .facility fee. charged by) \+ "
                      r"(the hospital, whether or not you.re admitted\.)", flat[i] if i is not None else "")
    if match:
        facts["facilityFee"] = match.group(1) + " " + match.group(2)
    else:
        missing.append("Facility fee at the emergency department")

    pages_out = {"sick": numbers[SICK], "medical": numbers[MEDICAL], "provider": numbers[PROVIDER],
                 "support": numbers[SUPPORT], "why": numbers[WHY], "amb": numbers[AMB], "states": numbers[STATES],
                 "hospital": numbers[HOSPITAL]}
    return facts, {k: v for k, v in pages_out.items() if v}, missing


# ---------- Other helpers ----------

def get_language() -> str:
    lang = st.session_state.get("lang", "en")
    return lang if lang in SUPPORTED_LANGUAGES else "en"


@st.cache_data
def load_html(modified_time: float) -> str:
    """Cached, but reloads when the HTML file changes."""
    return HTML_FILE.read_text(encoding="utf-8")


# ---------- Page ----------

st.set_page_config(page_title="If you get sick", layout="wide")
auth.require_login()

back_col, title_col = st.columns([1, 5])

with back_col:
    if st.button("← Back"):
        st.switch_page(HOME_PAGE)

with title_col:
    st.markdown("### What to do if you get sick")
    st.caption(
        "Choose how sick you feel, then follow a student step by step. "
        "This is general information, not medical advice."
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
    st.error(f"Can't find the guide file (sick_guide.html). Put it here: {HTML_FILE}")

# Show what was read from the PDF
if facts:
    with st.expander("See the text and numbers read from the brochure PDF"):
        st.caption("Printed pages: " + ", ".join(f"{k} {v}" for k, v in page_numbers.items()) + ".")
        st.markdown("**MBS fee rates (Medical table)**")
        st.write(f"GP consultations: {facts.get('gpRate', '?')}. "
                 f"Specialists, pathology and x-rays: {facts.get('specRate', '?')}.")
        for key, label, _, _ in READ_FROM_PDF:
            if key in facts:
                st.markdown(f"**{label}**")
                st.write(facts[key])
