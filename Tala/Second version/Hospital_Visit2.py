"""
Hospital Visit Guide page (OSHC Compass)

Shows a student walking through a hospital emergency department,
step by step. The animation lives in a separate HTML file.

Folder layout:
    app.py                          <- your main dashboard
    pages/Hospital_Visit_Guide.py   <- this file
    assets/hospital_visit_guide.html

Open this page from the dashboard with:
    st.switch_page("pages/Hospital_Visit_Guide.py")
"""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


# ---------- Settings ----------

# Main dashboard file (used by the Back button)
HOME_PAGE = "app.py"

# Path to the HTML file (assets folder next to the pages folder)
HTML_FILE = Path(__file__).parent / "hospital_visit (1).html"

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
    st.error(f"Can't find the guide file. Put it here: {HTML_FILE}")
