"""
Find a Health Provider guide page (OSHC Compass)

Shows a student walking through the steps of finding a health provider.
The text for each step is read from the OSHC brochure PDF (page with the
heading "If you need to find a health provider"). The animation lives in
a separate HTML file, the same style as the hospital guide.

Folder layout:
    oshc_welcome.py                    <- your main page
    pages/Find_Provider_Guide.py       <- this file
    find_provider_guide.html
    images/find_provider_form.jpg      <- screenshot of the search form
    images/find_provider_results.jpg   <- screenshot of the results
    OSHC_Brochure.pdf

Open this page from the dashboard card with:
    st.switch_page("pages/Find_Provider_Guide.py")
"""

import base64
import json
from pathlib import Path
from urllib.parse import quote

import pdfplumber
import streamlit as st
import streamlit.components.v1 as components

import auth


# ---------- Settings ----------

HOME_PAGE = "pages/1_Question.py"

ASSETS = Path(__file__).parent.parent   # the main project folder
HTML_FILE = ASSETS / "find_provider_guide.html"
PDF_FILE = ASSETS / "OSHC_Brochure.pdf"
IMAGES = ASSETS / "images"              # all pictures live in this folder
IMG_FORM = IMAGES / "find_provider_form.jpg"
IMG_RESULTS = IMAGES / "find_provider_results.jpg"

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


# ---------- Which advice comes from the PDF? ----------
# For every "What you need to do" item and every Tip, a phrase that must appear
# in the PDF for the item to get the "from the brochure" mark. None = our own advice.
# Order matches the steps in the HTML file.
CHECKS = [
    {"todo": ["medibankoshc.com.au/find-provider", "GPS", "Online Member Services"],
     "tip": "digital membership card"},
    {"todo": ["after-hours doctor home visits", "first point of contact", None],
     "tip": "1800 887 283"},
    {"todo": ["address or location", "GPS", None], "tip": None},
    {"todo": ["address and contact details", "no matter how you travel", None], "tip": None},
    {"todo": ["OSHC Direct Billing provider", "send the bill directly", "out-of-pocket"],
     "tip": "charges more than the amount we pay"},
    {"todo": ["Members’ Choice hospital", "public hospital or a private hospital",
              "Non-Members’ Choice private hospital"], "tip": None},
    {"todo": ["Medibank OSHC membership card", "photo identification", "confirm any out-of-pocket"],
     "tip": None},
]


def _norm(text: str) -> str:
    """Lower case, straight quotes, single spaces (so phrases match reliably)."""
    text = text.replace("’", "'").replace("‘", "'")
    return " ".join(text.lower().split())


@st.cache_data
def read_all_pages(pdf_path: str, modified_time: float) -> list:
    """Text of every page, tidied for searching."""
    with pdfplumber.open(pdf_path) as pdf:
        return [_norm(p.extract_text() or "") for p in pdf.pages]


def find_page(pages: list, phrase, preferred: int):
    """Page number (1-based) where the phrase appears, else 0. Prefers the provider page."""
    if not phrase:
        return 0
    key = _norm(phrase)
    if 1 <= preferred <= len(pages) and key in pages[preferred - 1]:
        return preferred
    for number, text in enumerate(pages, start=1):
        if key in text:
            return number
    return 0


def build_marks(pages: list, preferred: int, section: dict) -> dict:
    """0 = our own advice, otherwise the PDF page the advice comes from."""
    # The provider page has side-by-side columns, so also search the cleaned-up
    # section text (the columns read one by one)
    extra = " ".join([section["intro"], section["direct"], section["network"], section["footnote"]]
                     + [t["text"] for t in section["tiles"]])
    pages = list(pages)
    pages[preferred - 1] = pages[preferred - 1] + " " + _norm(extra)
    return {
        "todo": [[find_page(pages, ph, preferred) for ph in c["todo"]] for c in CHECKS],
        "tip": [find_page(pages, c["tip"], preferred) for c in CHECKS],
    }


# ---------- Other helpers ----------

def get_language() -> str:
    lang = st.session_state.get("lang", "en")
    return lang if lang in SUPPORTED_LANGUAGES else "en"


@st.cache_data
def load_html(modified_time: float) -> str:
    """Cached, but reloads when the HTML file changes."""
    return HTML_FILE.read_text(encoding="utf-8")


def image_data(path: Path) -> str:
    """Turn a picture file into text the HTML can show."""
    if not path.exists():
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def build_guide(lang: str, pdf_data: dict) -> str:
    """Put the language and the PDF text into the HTML."""
    payload = {}
    if pdf_data:
        pages = read_all_pages(str(PDF_FILE), PDF_FILE.stat().st_mtime)
        payload = {"page": pdf_data["page"], "file": PDF_FILE.name,
                   "steps": build_step_text(pdf_data),
                   "marks": build_marks(pages, pdf_data["page"], pdf_data)}
    html = load_html(HTML_FILE.stat().st_mtime).replace("__LANG__", lang)
    html = html.replace("__IMG_FORM__", image_data(IMG_FORM))
    html = html.replace("__IMG_RESULTS__", image_data(IMG_RESULTS))
    return html.replace("__PDF_DATA__", quote(json.dumps(payload), safe=""))


# ---------- Page ----------

st.set_page_config(page_title="Find a health provider", layout="wide")
auth.require_login()

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
