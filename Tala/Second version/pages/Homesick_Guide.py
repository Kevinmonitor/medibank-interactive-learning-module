"""
Homesickness guide page (OSHC Compass)

A wheel with six suggestions. Each "Next" turns the wheel and brings one
suggestion to the top. The sentences about the support line, counselling,
GP mental health plan and Student Rewards Plus are read from the OSHC
brochure PDF. Our own advice is marked "our advice" on the page.

Folder layout:
    oshc_welcome.py
    pages/Homesick_Guide.py        <- this file
    homesick_guide.html
    homesick.png                   <- the picture in the middle (the card picture)
    OSHC_Brochure.pdf

Open it from the card with:  st.switch_page("pages/Homesick_Guide.py")
"""

import base64
import io
import json
import re
from pathlib import Path
from urllib.parse import quote

import pdfplumber
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image


# ---------- Settings ----------

HOME_PAGE = "pages/1_Question.py"           # where the Back button goes

ASSETS = Path(__file__).parent.parent       # the main project folder
HTML_FILE = ASSETS / "homesick_guide.html"
PDF_FILE = ASSETS / "OSHC_Brochure.pdf"
CENTER_IMAGE = ASSETS / "homesick.png"

GUIDE_HEIGHT = 900
SUPPORTED_LANGUAGES = ["en", "si", "fa", "vi", "id"]

# A sentence to look for in the PDF for each of the 6 suggestions (None = our own text)
SENTENCE_KEYS = [
    None,
    "anytime, day or night",
    "telephone interpreter services in around",
    "benefits towards psychology",
    "gp mental health treatment plan",
    "find work and enhance",
]

# A phrase that must be in the PDF for each advice item to get the "from the brochure" mark
CHECKS = [
    {"todo": [None, None, None], "tip": None},
    {"todo": ["1800 887 283", "registered nurse", None], "tip": "call back may be required"},
    {"todo": [None, "interpreter services", "dozen languages"], "tip": "simplified Chinese"},
    {"todo": ["maximum per consultation", "maximum per consultation", "single membership $200"],
     "tip": "pay the difference"},
    {"todo": ["Direct Billing provider", "mental health treatment plan", "consultations with a psychologist"],
     "tip": "waiting periods may apply"},
    {"todo": ["Student Rewards Plus", "find work", None], "tip": None},
]


# ---------- Reading the PDF ----------

def _norm(text: str) -> str:
    """Lower case, straight quotes, single spaces (so phrases match reliably)."""
    text = text.replace("’", "'").replace("‘", "'")
    return " ".join(text.lower().split())


def _sentences(text: str) -> list:
    text = " ".join(text.split())
    return re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)


@st.cache_data
def read_pdf(pdf_path: str, modified_time: float) -> list:
    """For every page: full text, plus the text of its left and right half and of its
    three columns (side-by-side boxes mix together in the full text)."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            views = [page.extract_text() or ""]
            for parts in (2, 3):
                width = page.width / parts
                for c in range(parts):
                    box = (c * width, 0, (c + 1) * width, page.height)
                    views.append(page.within_bbox(box).extract_text() or "")
            pages.append(views)
    return pages


def find_sentence(pages: list, key: str):
    """(sentence, page number) of the first sentence that contains the key."""
    # Clean sentences are usually on the later pages, so look from the end
    for number in range(len(pages), 0, -1):
        for view in pages[number - 1]:
            for sentence in _sentences(view):
                if _norm(key) in _norm(sentence):
                    return sentence.replace("^", "").replace("*", "").strip(), number
    return "", 0


def find_page(pages: list, phrase) -> int:
    """Page number where the phrase appears (0 = not in the PDF)."""
    if not phrase:
        return 0
    key = _norm(phrase)
    for number, views in enumerate(pages, start=1):
        if any(key in _norm(v) for v in views):
            return number
    return 0


def build_pdf_data(pages: list) -> dict:
    """Everything the HTML needs from the PDF."""
    what, what_page = [], []
    for key in SENTENCE_KEYS:
        sentence, number = find_sentence(pages, key) if key else ("", 0)
        what.append(sentence)
        what_page.append(number)
    return {
        "what": what,
        "whatPage": what_page,
        "marks": {
            "todo": [[find_page(pages, p) for p in c["todo"]] for c in CHECKS],
            "tip": [find_page(pages, c["tip"]) for c in CHECKS],
        },
    }


# ---------- Other helpers ----------

def get_language() -> str:
    lang = st.session_state.get("lang", "en")
    return lang if lang in SUPPORTED_LANGUAGES else "en"


@st.cache_data
def load_html(modified_time: float) -> str:
    """Cached, but reloads when the HTML file changes."""
    return HTML_FILE.read_text(encoding="utf-8")


@st.cache_data
def center_image_data(path: str, modified_time: float) -> str:
    """The middle picture, made smaller so the page stays light."""
    image = Image.open(path).convert("RGB")
    image.thumbnail((500, 500))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def build_guide(lang: str, pdf_data: dict) -> str:
    html = load_html(HTML_FILE.stat().st_mtime).replace("__LANG__", lang)
    payload = quote(json.dumps(pdf_data), safe="") if pdf_data else ""
    html = html.replace("__PDF_DATA__", payload)
    picture = ""
    if CENTER_IMAGE.exists():
        picture = center_image_data(str(CENTER_IMAGE), CENTER_IMAGE.stat().st_mtime)
    return html.replace("__IMG_CENTER__", picture)


# ---------- Page ----------

st.set_page_config(page_title="Feeling homesick", layout="wide")

back_col, title_col = st.columns([1, 5])

with back_col:
    if st.button("← Back"):
        st.switch_page(HOME_PAGE)

with title_col:
    st.markdown("### When you miss home")
    st.caption(
        "Six ways to find support. Press Next to turn the wheel. "
        "This is general information, not medical advice."
    )

# Read the PDF (if it fails, the guide still works with built-in text)
pdf_data = {}
if PDF_FILE.exists():
    try:
        pdf_data = build_pdf_data(read_pdf(str(PDF_FILE), PDF_FILE.stat().st_mtime))
    except Exception as error:
        st.warning(f"Couldn't read the brochure PDF, so the guide is using built-in text. ({error})")
else:
    st.warning(f"Brochure PDF not found. Put it here: {PDF_FILE}")

if HTML_FILE.exists():
    components.html(build_guide(get_language(), pdf_data), height=GUIDE_HEIGHT, scrolling=True)
else:
    st.error(f"Can't find the guide file. Put it here: {HTML_FILE}")
