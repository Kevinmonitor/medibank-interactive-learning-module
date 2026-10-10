"""Shared fixed top-left Medibank logo header, reused across all OSHCwise pages."""

import base64
from pathlib import Path

import streamlit as st

# The logo lives in the "images" folder (older copies may still have it next to this file)
_LOGO_PATH = Path(__file__).parent / "images" / "medibank.webp"
if not _LOGO_PATH.exists():
    _LOGO_PATH = Path(__file__).parent / "medibank.webp"


def render_header() -> None:
    """Render the fixed top-left Medibank logo. Call once near the top of each page."""
    logo_data = base64.b64encode(_LOGO_PATH.read_bytes()).decode()
    st.markdown(
        """
        <style>
            .app-header {
                position: fixed;
                top: 1.25rem;
                left: 1.5rem;
                z-index: 1000;
            }
            .app-header img { width: min(140px, 30vw); height: auto; display: block; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="app-header"><img src="data:image/webp;base64,{logo_data}" alt="Medibank Live Better logo"></div>',
        unsafe_allow_html=True,
    )
