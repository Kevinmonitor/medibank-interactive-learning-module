"""
Chatbot insights (administrators only).

Reuses Muhammad's analysis pages: topic/confidence patterns and the
prompt (NLP) analysis. Reads the chatbot's own interaction log in
Muhammad/data/interactions.db. Aggregate only, no student identities.
"""
import sys
from pathlib import Path

import streamlit as st

import auth

_CHATBOT = Path(__file__).resolve().parents[2] / "Muhammad"
if str(_CHATBOT) not in sys.path:
    sys.path.insert(0, str(_CHATBOT))

from app.main import page_insights   # noqa: E402

st.set_page_config(page_title="Chatbot insights", layout="wide")
auth.require_login(admin_only=True)

if st.button("← Back", key="insights_back"):
    st.switch_page("pages/1_Question.py")

page_insights()
