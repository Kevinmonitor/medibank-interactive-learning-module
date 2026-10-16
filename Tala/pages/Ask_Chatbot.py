"""
Ask the chatbot about your OSHC cover.

This page reuses Muhammad's chatbot. The chatbot code lives in the
Muhammad/ folder and is loaded here; nothing is copied. The search bar on
the hub (1_Question.py) sets "chat_tala_pending", which assistant() picks
up and answers straight away.
"""
import sys
from pathlib import Path

import streamlit as st

import auth
from app_header import render_header

# Make the chatbot package importable. parents[2] is the repository root.
_CHATBOT = Path(__file__).resolve().parents[2] / "Muhammad"
if str(_CHATBOT) not in sys.path:
    sys.path.insert(0, str(_CHATBOT))

from app.main import assistant   # noqa: E402

st.set_page_config(page_title="Ask about your cover", layout="wide")
auth.require_login()
render_header()

# These used to come from the chatbot's own sidebar. Ask for them here.
st.session_state.setdefault("product", "comprehensive")

_, main_area, _ = st.columns([1, 5, 1])
with main_area:
    if st.button("← Back", key="chat_back"):
        st.switch_page("pages/1_Question.py")

    st.markdown("## Ask about your cover")
    st.session_state["product"] = st.selectbox(
        "Your cover", ["comprehensive", "essentials"],
        index=0 if st.session_state["product"] == "comprehensive" else 1)

    # Admin view: show the full answer with the source wording and
    # Flesch-Kincaid readability analysis.
    assistant("admin", show_analysis=True)
