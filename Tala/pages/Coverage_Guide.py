"""
Comprehensive OSHC coverage: guide page (OSHC Compass)

Four parts: "Is it covered?" search, the main benefits, an Extras plan explorer,
and a "Good to know" list. The animation/UI lives in a separate HTML file.

Facts, the hospital list (Included / Excluded) and the Extras table are READ FROM THE PDF
every time the PDF changes. If a part can no longer be found, the guide uses its saved text
for that part and this page shows a warning.

Folder layout:
    oshc_welcome.py                <- main page
    pages/Coverage_Guide.py        <- this file
    coverage_guide.html            <- the page design (main folder, or next to this file)
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
GUIDE_HEIGHT = 800
SUPPORTED_LANGUAGES = ["en", "si", "fa", "vi", "id"]


def find_html() -> Path:
    """Find the page file (main folder, this folder, "assets" or "images")."""
    here = Path(__file__).parent
    for folder in (ROOT, here, ROOT / "assets", ROOT / "images"):
        found = sorted(folder.glob("coverage_guide*.html"))
        if found:
            return found[0]
    return ROOT / "coverage_guide.html"


HTML_FILE = find_html()

# What we read from the PDF.
# (key used in the HTML, label, where it is, pattern). Group 1 of the pattern is the value
# (if there is no group, the whole match is used).
(INTRO, HOSP, HOSPTBL, MEDICAL, RX, EXTRAS, MENTAL, MORE, LIMITS, CONTACT, AMB) = (
    "intro", "hosp", "hosptbl", "medical", "rx", "extras", "mental", "more", "limits", "contact", "amb")

READ_FROM_PDF = [
    ("intro", "What Comprehensive OSHC helps pay", INTRO,
     r"(Comprehensive OSHC can help pay towards the cost of a range of in-hospital procedures.*?Australia-wide\.)"),
    ("who1", "Who it is for: not a permanent resident", INTRO, r"• (Do not hold permanent resident status in Australia)"),
    ("who2", "Who it is for: not eligible for Medicare", INTRO, r"• (Are not eligible for full Medicare benefits)"),
    ("who3", "Who it is for: 500 Student visa", INTRO,
     r"• (Are/will be in Australia on a 500 Student visa subclass as): º (An Overseas Student), or º (An eligible Dependant of an Overseas Student)"),
    ("hospitalIntro", "Hospital cover", HOSP,
     r"Hospital cover can help pay towards your treatment when you.re admitted to hospital as a private patient\. It also helps pay towards the cost of accommodation and medical services for Included services provided in hospital\."),
    ("waitNote", "Waiting periods and pregnancy", HOSP,
     r"It.s important to be aware that waiting periods may apply to some services, including Pre-existing Conditions and Pregnancy and birth services\."),
    ("cosmetic", "No cosmetic treatment", HOSP,
     r"Medibank does not pay towards cosmetic treatment or services without an MBS item\."),
    ("pharmaLimited", "Limited benefits for pharmaceuticals", HOSP,
     r"Under Comprehensive OSHC, we pay limited benefits towards pharmaceuticals\. You may have large out-of-pocket expenses if you require high-cost drugs, such as those used in oncology \(cancer treatment\)\."),
    ("waitingPeriods", "Waiting periods", HOSP,
     r"A waiting period applies when you join Medibank, or change your cover to include new or upgraded services\. We won.t pay benefits for any items purchased or services received while you are serving a waiting period\."),
    ("extrasSeparate", "Extras are bought separately", HOSP,
     r"You can purchase a Medibank Extras cover separately to help towards the cost of everyday health services, like dental and optical\."),
    ("mbsDef", "What the MBS fee is", MEDICAL,
     r"The Medicare Benefits Schedule \(MBS\) is a list.*?known as the MBS fee\."),
    ("mustPayDiff", "You pay the difference", MEDICAL,
     r"You must pay any difference between the benefit we pay and the actual fee charged for the service\."),
    ("eligible", "Only prescribed medicines are paid", RX,
     r"Benefits are payable only for prescription medicines prescribed by a doctor \(GP or specialist\) to treat an illness, injury or condition\."),
    ("contribution", "Medicines: member contribution", RX, r"Member contribution (\$[\d,]+)"),
    ("pct", "Medicines: amount Medibank pays", RX, r"Amount we.ll pay \(maximum per item\) (\d+% of cost)"),
    ("annualSingle", "Medicines: annual limit, single", RX, r"Annual limit . Single membership (\$[\d,]+)"),
    ("annualFamily", "Medicines: annual limit, family", RX,
     r"Annual limit . Couple/Family membership (\$[\d,]+ per member / \$[\d,]+ per membership)"),
    ("notCovered", "Medicines: cosmetic and Excluded", RX,
     r"We don.t pay benefits towards prescription medicines for cosmetic purposes or for prescription medicines that relate to an Excluded service\."),
    ("highCost", "Medicines: high-cost medicines", RX,
     r"It.s important to note that you may have large out-of-pocket expenses.*?cancer treatment\)\."),
    ("ambulanceHelp", "Emergency ambulance", AMB, r"(eligible emergency ambulance services Australia-wide)"),
    ("ambulanceNote", "When the ambulance is covered", AMB,
     r"# (For ambulance attendance or transportation.*?any other way\.)"),
    ("mentalIntro", "Mental health support", MENTAL,
     r"(Comprehensive OSHC provides benefits towards psychology, counselling and mental health social workers services received from recognised providers and billed without an MBS item number\.)"),
    ("psychiatric", "Hospital psychiatric services", MENTAL,
     r"With Medibank OSHC, you.ll have immediate access to hospital psychiatric services even if it.s treatment for a pre-existing condition\."),
    ("repatriation", "Repatriation: travel", MORE, r"we may arrange and pay the reasonable cost of travel with the appropriate medical supervision \(up to a maximum of (\$[\d,]+)\)"),
    ("remains", "Repatriation: mortal remains", MORE, r"repatriation of mortal remains of you \(or anyone else on your membership\) to your home country \(up to a maximum of (\$[\d,]+)\)"),
    ("repatNote", "Repatriation: conditions", MORE,
     r"The provision of any repatriation benefit is at our discretion and is payable only once per member per lifetime\. Conditions apply, including waiting periods\."),
    ("boarder", "Family stay in hospital (boarder fee)", MORE, r"up to (\$\d+) per admission"),
    ("annualLimit", "What an annual limit is", LIMITS,
     r"An annual limit is the maximum amount of benefits payable per member and/or per membership, within a calendar year \(1 January to 31 December\)\."),
    ("phoneAu", "Phone (in Australia)", CONTACT, r"(134 148) \(from within Australia\)"),
    ("hours", "Phone hours", CONTACT, r"Available (Monday to Friday 8am-8pm AEST)"),
]

# A phrase that is only on that page
PAGE_MARKERS = {
    INTRO: "Comprehensive OSHC is intended for people who",
    HOSP: "Hospital cover can help pay towards your treatment",
    MEDICAL: "Medical cover pays towards",
    RX: "Member contribution",
    EXTRAS: "Prescription pharmaceuticals (non-PBS)",
    MENTAL: "mental health social workers services received from recognised providers",
    MORE: "Repatriation.",
    LIMITS: "An annual limit is the maximum amount",
    CONTACT: "to find your nearest Medibank store",
    AMB: "eligible emergency ambulance services",
}
PLAN_KEYS = ["healthy", "essential", "top60", "top75", "top90"]
MARKS = "*^+†‡~#&"


# ---------- Reading the PDF ----------

@st.cache_data
def read_pdf(pdf_path: str, modified_time: float) -> dict:
    """The text and the tables of every PDF page (reloads when the PDF changes)."""
    with pdfplumber.open(pdf_path) as pdf:
        return {
            "pages": [p.extract_text() or "" for p in pdf.pages],
            "tables": [p.extract_tables() for p in pdf.pages],
        }


def _flat(text) -> str:
    """One line, single spaces."""
    return " ".join((text or "").split())


def _page_label(index: int, pages: list) -> str:
    """'page 5' (the printed number; a spread shows 'left middle right', use the middle), or a cover."""
    last = pages[index].strip().split("\n")[-1].split()
    if last and all(w.isdigit() for w in last):
        return f"page {last[len(last) // 2]}"
    if index >= len(pages) - 1:
        return "the back cover"
    return "the inside front cover" if index <= 1 else f"PDF page {index + 1}"


def read_rates(tables: list) -> dict:
    """The 'We pay 100% / 85% of the MBS fee for' table: which service gets which percentage."""
    rates, current = {}, None
    for table in tables:
        if not table or not table[0] or "Included services" not in (table[0][0] or ""):
            continue
        for left, right in (r for r in table[1:] if len(r) >= 2):
            percent = re.search(r"(\d+)%", left or "")
            current = percent.group(1) + "%" if percent else current
            text = _flat(right).lower()
            if current and "general practitioner" in text:
                rates["gpRate"] = current
            elif current and "other medical services" in text:
                rates["specRate"] = current
    return rates


def read_mental(tables: list) -> dict:
    """The mental health table: Psychology / Counselling and social workers, and the annual limits."""
    for table in tables:
        flat = [[_flat(c) for c in row] for row in table if row]
        if len(flat) >= 4 and "Psychology" in flat[0] and "maximum per consultation" in flat[1][0]:
            return {"psychology": flat[1][1], "social": flat[1][2],
                    "limitSingle": flat[2][1], "limitFamily": flat[3][1]}
    return {}


def read_hospital(data: dict, flat: list):
    """The Included / Excluded list of in-hospital services (a tick = Included, a cross = Excluded)."""
    for i, tables in enumerate(data["tables"]):
        for table in tables:
            if table and table[0] and "Services that are Included or Excluded" in (table[0][0] or ""):
                notes = {}
                for mark, pattern in (("*", r"\* (We will only pay.*?under your cover\.)"),
                                      ("^", r"\^ (For Dental surgery.*?medical charges\.)"),
                                      ("+", r"\+ (For Podiatric surgery.*?out-of-pocket expenses\.)")):
                    found = re.search(pattern, flat[i])
                    if found:
                        notes[mark] = found.group(1)
                items = []
                for name, symbol in ((_flat(r[0]), _flat(r[1])) for r in table[1:] if len(r) >= 2):
                    if not name or symbol not in ("c", "b"):
                        continue
                    mark = name[-1] if name[-1] in MARKS else ""
                    items.append({"name": name.rstrip(MARKS).strip(),
                                  "in": symbol == "c", "note": notes.get(mark, "")})
                return i, items
    return None, []


def read_extras(tables: list) -> dict:
    """The Extras table. Blank cells in the PDF are merged cells: they repeat the cell above."""
    for table in tables:
        if not table or len(table[0]) < 8 or "Waiting period" not in _flat(table[0][2]):
            continue
        header = [(c or "").split("\n") for c in table[0]]
        plans = [{"key": k, "name": _flat(header[3 + n][0]) if header[3 + n] else k,
                  "about": _flat(" ".join(header[3 + n][1:]))} for n, k in enumerate(PLAN_KEYS)]
        rows, above, previous_name = [], [""] * 8, ""
        for raw in table[1:]:
            cells = [_flat(c).strip() for c in raw]
            name = cells[0].split(" Members")[0].rstrip(MARKS + " ")
            if not name:
                name = previous_name
            for c in range(2, 8):                      # blank = merged with the cell above
                cells[c] = cells[c] or above[c]
            above = cells
            previous_name = name
            vals = [("not covered" if v == "b" else v.rstrip(MARKS + " ")) for v in cells[3:8]]
            rows.append({"name": name, "desc": cells[1].rstrip("~ "), "wait": cells[2], "vals": vals})
        return {"plans": plans, "rows": rows}
    return {}


def read_facts(data: dict):
    """Return (payload for the HTML, parts that were not found)."""
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
        value = " ".join(g for g in match.groups() if g) if match.groups() else match.group(0)
        if key == "who3":
            value = f"{match.group(1)} an Overseas Student, or an eligible Dependant of an Overseas Student"
        facts[key] = re.sub(r"[\^#&]+(?=[\s,.]|$)", "", value.strip())

    i = found[MEDICAL]
    rates = read_rates(data["tables"][i]) if i is not None else {}
    for key, label in (("gpRate", "GP consultations: % of MBS fee"),
                       ("specRate", "Specialists, pathology, x-rays: % of MBS fee")):
        if key in rates:
            facts[key] = rates[key]
        else:
            missing.append(label)

    i = found[MENTAL]
    mental = read_mental(data["tables"][i]) if i is not None else {}
    if mental:
        facts.update(mental)
    else:
        missing.append("Mental health table (Psychology / Counselling)")

    h_index, hospital = read_hospital(data, flat)
    if not hospital:
        missing.append("List of Included and Excluded hospital services")
    if h_index is not None and found[HOSP] is not None:
        if "Included c or Excluded b" not in flat[found[HOSP]]:
            missing.append("The meaning of the tick and cross (page changed: check the hospital list)")

    i = found[EXTRAS]
    extras = read_extras(data["tables"][i]) if i is not None else {}
    if not extras:
        missing.append("Extras table")

    labels = {name: _page_label(i, pages) for name, i in found.items() if i is not None}
    if h_index is not None:
        labels["hosptbl"] = _page_label(h_index, pages)
    payload = {"facts": facts, "pages": labels, "hospital": hospital, "extras": extras}
    return payload, missing



# ---------- Other helpers ----------

def get_language() -> str:
    lang = st.session_state.get("lang", "en")
    return lang if lang in SUPPORTED_LANGUAGES else "en"


@st.cache_data
def load_html(modified_time: float) -> str:
    """Cached, but reloads when the HTML file changes."""
    return HTML_FILE.read_text(encoding="utf-8")


# ---------- Page ----------

st.set_page_config(page_title="Comprehensive OSHC coverage", layout="wide")
auth.require_login()

back_col, title_col = st.columns([1, 5])

with back_col:
    if st.button("← Back"):
        st.switch_page(HOME_PAGE)

with title_col:
    st.markdown("### Comprehensive OSHC coverage")
    st.caption(
        "Pick a situation to see what Comprehensive OSHC does and does not pay for. "
        "This is general information. Your policy and the Medibank website have the final say."
    )

payload, missing = {}, []
if PDF_FILE.exists():
    try:
        pdf_data = read_pdf(str(PDF_FILE), PDF_FILE.stat().st_mtime)
        payload, missing = read_facts(pdf_data)
        if missing:
            st.warning(
                "Some parts could not be found in the brochure PDF any more (maybe the brochure changed). "
                "The guide shows its saved text for these parts, so please check them: "
                + "; ".join(missing)
            )
    except Exception as error:
        payload = {}
        st.warning(f"Couldn't read the brochure PDF. The guide is showing its saved text. ({error})")
else:
    st.warning(f"Brochure PDF not found. Put it here: {PDF_FILE}")

if HTML_FILE.exists():
    html = load_html(HTML_FILE.stat().st_mtime).replace("__LANG__", get_language())
    html = html.replace("__PDF_DATA__", quote(json.dumps(payload, ensure_ascii=False), safe=""))
    components.html(html, height=GUIDE_HEIGHT, scrolling=True)
else:
    st.error(f"Can't find the guide file (coverage_guide.html). Put it here: {HTML_FILE}")

if payload.get("facts"):
    with st.expander("See the text and numbers read from the brochure PDF"):
        st.caption("Where it is in the brochure: "
                   + ", ".join(f"{k} {v}" for k, v in payload["pages"].items()) + ".")
        for key, label, _, _ in READ_FROM_PDF:
            if key in payload["facts"]:
                st.markdown(f"**{label}**")
                st.write(payload["facts"][key])
        if payload.get("hospital"):
            st.markdown("**Hospital services list**")
            st.write(f"{len(payload['hospital'])} items read.")
        if payload.get("extras"):
            st.markdown("**Extras table**")
            st.write(f"{len(payload['extras'])} rows read.")
