"""
Hospital Visit Guide page (OSHC Compass)

Shows a student walking through a hospital emergency department,
step by step. The animation lives in a separate HTML file.

Folder layout:
    oshc_welcome.py                 <- first (login) page
    pages/1_Question.py             <- the cards (opens this page)
    pages/Hospital_Visit.py         <- this file
    pages/hospital_visit.html       <- the animation (or in "assets" / the main folder)
"""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import auth


# ---------- Settings ----------

# Page with the cards (used by the Back button)
HOME_PAGE = "pages/1_Question.py"


def find_html() -> Path:
    """Find the animation file. It may be next to this file, in "assets", "images" or the main folder.
    A name like "hospital_visit (1).html" (from a download) works too."""
    here = Path(__file__).parent
    for folder in (here, here.parent / "assets", here.parent / "images", here.parent):
        found = sorted(folder.glob("hospital_visit*.html"))
        if found:
            return found[0]
    return here / "hospital_visit.html"


HTML_FILE = find_html()

# Height of the guide on the page (pixels)
GUIDE_HEIGHT = 820

# Languages the guide supports
# en = English, si = Sinhala, fa = Farsi, vi = Vietnamese, id = Bahasa Indonesia
SUPPORTED_LANGUAGES = ["en", "si", "fa", "vi", "id"]


# ---------- Helper functions ----------

def get_language() -> str:
    """Get the language chosen on the dashboard (English by default)."""
    lang = st.session_state.get("lang", "en")
    return lang if lang in SUPPORTED_LANGUAGES else "en"


@st.cache_data
def load_html() -> str:
    """Read the HTML file once and keep it in memory."""
    return HTML_FILE.read_text(encoding="utf-8")


def build_guide(lang: str) -> str:
    """Put the student's language into the HTML."""
    return load_html().replace("__LANG__", lang)


# ---------- Page ----------

st.set_page_config(page_title="Hospital visit guide", layout="wide")
auth.require_login()          # students and the admin only

# Top bar: Back button + heading
back_col, title_col = st.columns([1, 5])

with back_col:
    if st.button("← Back"):
        st.switch_page(HOME_PAGE)

with title_col:
    st.markdown("### What happens when you go to hospital")
    st.caption(
        "Follow a student through an emergency department, step by step. "
        "This is general information, not medical advice."
    )

# The guide itself
if HTML_FILE.exists():
    components.html(
        build_guide(get_language()),
        height=GUIDE_HEIGHT,
        scrolling=True,
    )
else:
    st.error(f"Can't find the guide file (hospital_visit.html). Put it here: {HTML_FILE}")
