
"""First screen of the OSHC student learning application."""
import html

import streamlit as st
from app_header import render_header

st.set_page_config(page_title="OSHCwise", initial_sidebar_state="collapsed", layout="wide")

# A later login flow can set st.session_state["student_name"].
# For a quick preview, add ?name=Tala to the app URL.
name = st.session_state.get("student_name") or st.query_params.get("name") or "Student"
first_name = str(name).strip().split()[0] if str(name).strip() else "Student"
safe_name = html.escape(first_name)
logo_data = "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"

if "screen" not in st.session_state:
    st.session_state.screen = "intro"
render_header()

st.markdown(
    """
    <style>
        .stApp { background: #ffffff; font-family: "Lucida Sans", "Lucida Sans Unicode", Arial, sans-serif; }
        header[data-testid="stHeader"] { background: transparent; }
        .block-container { max-width: 100%; padding: 0 1.5rem; }
        .intro, .welcome-screen {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            text-align: center;
        }
        .intro { padding-top: clamp(15vh, 23vh, 26vh); }
        .intro h1 {
            color: #123e52;
            font-family: "Lucida Sans", "Lucida Sans Unicode", Arial, sans-serif;
            font-size: clamp(2.7rem, 6vw, 4.5rem);
            margin: 0 0 1.4rem;
        }
        .intro h1 .wise-text { color: #d32f2f; }
        .intro p {
            color: #273b42;
            font-family: "Lucida Sans", "Lucida Sans Unicode", Arial, sans-serif;
            font-size: clamp(1.1rem, 2.2vw, 1.6rem);
            line-height: 1.45;
            max-width: 620px;
            margin: 0;
        }
        div[data-testid="element-container"]:has(div.stButton) {
            display: flex !important;
            justify-content: center !important;
        }
        div.stButton, div[data-testid="stButton"] {
            display: flex !important;
            justify-content: center !important;
            width: 100% !important;
            margin: 4rem 0 0 !important;
        }
        div.stButton > button, div[data-testid="stButton"] > button {
            width: 100%;
            max-width: 180px;
            min-height: 2.6rem;
            background: #808080;
            border: 0;
            border-radius: 6px;
            color: #ffffff;
            font-size: 1rem;
            font-weight: 600;
        }
        div.stButton > button:hover, div[data-testid="stButton"] > button:hover { background: #6b6b6b; color: #ffffff; }
        .welcome-screen { min-height: 85vh; gap: 2rem; }
        .welcome-screen img { width: min(200px, 50vw); height: auto; }
        .welcome-screen h1 {
            color: #143a5a;
            font-family: "Lucida Sans", "Lucida Sans Unicode", Arial, sans-serif;
            font-size: clamp(2rem, 4vw, 3.5rem);
            font-weight: 700;
            margin: 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.screen == "intro":
    st.markdown(
        '<main class="intro"><h1>OSHC<span class="wise-text">wise</span></h1>'
        '<p>A Medibank OSHC learning platform that<br>adapts to <strong>you</strong>.</p></main>',
        unsafe_allow_html=True,
    )
    if st.button("Continue", type="primary", use_container_width=True):
        st.session_state.screen = "welcome"
        st.rerun()
else:
    st.markdown(
        f'<main class="welcome-screen"><img src="data:image/webp;base64,{logo_data}" '
        f'alt="Medibank Live Better logo"><h1>Welcome, {safe_name}!</h1></main>',
        unsafe_allow_html=True,
    )
