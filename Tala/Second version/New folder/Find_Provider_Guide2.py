"""
Find a Health Provider guide page (OSHC Compass)

Shows a student walking through the steps of finding a health provider.
The text for each step is read from the OSHC brochure PDF (page with the
heading "If you need to find a health provider"). The animation lives in
a separate HTML file, the same style as the hospital guide.

Folder layout:
    app.py                             <- your main dashboard
    pages/Find_Provider_Guide.py       <- this file
    assets/find_provider_guide.html
    assets/OSHC_Brochure.pdf

Open this page from the dashboard card with:
    st.switch_page("pages/Find_Provider_Guide.py")
"""

import json
from pathlib import Path
from urllib.parse import quote

import pdfplumber
import streamlit as st
import streamlit.components.v1 as components


# ---------- Settings ----------

HOME_PAGE = "oshc_welcome.py"

ASSETS = Path(__file__).parent.parent
HTML_FILE = ASSETS / "find_provider_guide.html"
PDF_FILE = ASSETS / "OSHC_Brochure.pdf"

GUIDE_HEIGHT = 820
SUPPORTED_LANGUAGES = ["en", "si", "fa", "vi", "id"]

# Headings we look for in the PDF (if Medibank renames them, update here)
H_START = "If you need to find a health provider"
H_DIRECT = "How does visiting a Medibank OSHC Direct Billing provider help"
H_NETWORK = "Members’ Choice hospital network"
H_HOWTO = "How it works"
FOOTNOTE_MARK = "*Please"


# ---------- Reading the PDF ----------

def _clean(lines) -> str:
    """Join lines into one paragraph and tidy spaces."""
    return " ".join(" ".join(lines).split()).strip()


def _find_line(lines, start, begin=0):
    """Index of the first line (from `begin`) that starts with `start`."""
    for i in range(begin, len(lines)):
        if lines[i].strip().startswith(start):
            return i
    raise ValueError(f"Heading not found in PDF: {start}")


def extract_provider_section(pdf_path: Path) -> dict:
    """Read the 'find a health provider' page and split it into parts."""
    with pdfplumber.open(pdf_path) as pdf:
        # 1. Find the page that has the heading
        page, page_no = None, None
        for number, candidate in enumerate(pdf.pages, start=1):
            if H_START in (candidate.extract_text() or ""):
                page, page_no = candidate, number
                break
        if page is None:
            raise ValueError(f"Heading not found in PDF: {H_START}")

        lines = (page.extract_text() or "").split("\n")
        if lines and lines[-1].strip().isdigit():       # printed page number
            lines = lines[:-1]

        # 2. Split the text by headings
        i_start = _find_line(lines, H_START)
        i_how = _find_line(lines, H_HOWTO, i_start)
        i_direct = _find_line(lines, H_DIRECT, i_how)
        i_network = _find_line(lines, H_NETWORK, i_direct)
        i_note = _find_line(lines, FOOTNOTE_MARK, i_network)

        intro = _clean(lines[i_start + 1:i_how])
        direct = _clean(lines[i_direct + 1:i_network]).replace("*", "")
        network = _clean(lines[i_network + 1:i_note])
        footnote = _clean(lines[i_note:]).lstrip("*").strip()

        # 3. The three "How it works" tiles sit side by side, so cut them
        #    into columns using their position on the page
        words = page.extract_words()
        top = next(w for w in words if w["text"].startswith("works"))["bottom"] + 1
        bottom = min(w["top"] for w in words
                     if w["text"] == "visiting" and w["top"] > top) - 2
        third = page.width / 3
        tiles = []
        for c in range(3):
            box = (c * third, top, (c + 1) * third, bottom)
            col = (page.within_bbox(box).extract_text() or "").split("\n")
            col = [t for t in col if not t.strip().startswith(H_HOWTO)]
            tiles.append({"title": col[0].strip().rstrip("."),
                          "text": _clean(col[1:])})

    return {"page": page_no, "intro": intro, "tiles": tiles,
            "direct": direct, "network": network, "footnote": footnote}


@st.cache_data
def read_pdf(pdf_path: str, modified_time: float) -> dict:
    """Cached. `modified_time` makes the text refresh when the PDF changes."""
    return extract_provider_section(Path(pdf_path))


def sentence(text: str, keyword: str) -> str:
    """Pick the sentence that contains `keyword` (empty if none)."""
    for part in text.replace("e.g. ", "e.g.~").split(". "):
        if keyword.lower() in part.lower():
            return (part.replace("~", " ").strip().rstrip(".") + ".")
    return ""


def build_step_text(data: dict) -> list:
    """Text for the 7 steps, in the same order as the HTML file."""
    tiles = data["tiles"]
    intro = data["intro"]
    use_tool = intro.split(". ")[0].strip().rstrip(".") + "."
    by_service = sentence(intro, "by service")
    return [
        use_tool,                                   # 1 Search tool
        by_service + " " + tiles[0]["text"],        # 2 Service
        tiles[1]["text"],                           # 3 Location
        tiles[2]["text"],                           # 4 Results
        data["direct"],                             # 5 Billing
        data["network"],                            # 6 Hospitals
        data["footnote"],                           # 7 Visit
    ]


# ---------- Other helpers ----------

def get_language() -> str:
    lang = st.session_state.get("lang", "en")
    return lang if lang in SUPPORTED_LANGUAGES else "en"


@st.cache_data
def load_html() -> str:
    return HTML_FILE.read_text(encoding="utf-8")


def build_guide(lang: str, pdf_data: dict) -> str:
    """Put the language and the PDF text into the HTML."""
    payload = {}
    if pdf_data:
        payload = {"page": pdf_data["page"], "file": PDF_FILE.name,
                   "steps": build_step_text(pdf_data)}
    html = load_html().replace("__LANG__", lang)
    return html.replace("__PDF_DATA__", quote(json.dumps(payload), safe=""))


# ---------- Page ----------

st.set_page_config(page_title="Find a health provider", layout="wide")

back_col, title_col = st.columns([1, 5])

with back_col:
    if st.button("← Back"):
        st.switch_page(HOME_PAGE)

with title_col:
    st.markdown("### How to find a health provider")
    st.caption(
        "Follow a student step by step as they find a doctor or hospital. "
        "This is general information, not medical advice."
    )

# Read the PDF (if it fails, the guide still works with built-in text)
pdf_data = {}
if PDF_FILE.exists():
    try:
        pdf_data = read_pdf(str(PDF_FILE), PDF_FILE.stat().st_mtime)
    except Exception as error:
        st.warning(
            "Couldn't read the brochure PDF, so the guide is showing its "
            f"built-in text. ({error})"
        )
else:
    st.warning(f"Brochure PDF not found. Put it here: {PDF_FILE}")

# The guide itself
if HTML_FILE.exists():
    components.html(build_guide(get_language(), pdf_data),
                    height=GUIDE_HEIGHT, scrolling=True)
else:
    st.error(f"Can't find the guide file. Put it here: {HTML_FILE}")

# Show the source text from the PDF
if pdf_data:
    with st.expander(f"See the text read from the PDF (page {pdf_data['page']})"):
        st.markdown("**Intro**")
        st.write(pdf_data["intro"])
        for tile in pdf_data["tiles"]:
            st.markdown(f"**{tile['title']}**")
            st.write(tile["text"])
        st.markdown("**Direct Billing**")
        st.write(pdf_data["direct"])
        st.markdown("**Members’ Choice hospital network**")
        st.write(pdf_data["network"])
        st.markdown("**Note**")
        st.write(pdf_data["footnote"])
