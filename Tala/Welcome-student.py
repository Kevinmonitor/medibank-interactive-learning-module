"""Intro and personalised welcome for the OSHCwise prototype."""

import html

import streamlit as st

from app_header import render_header


st.set_page_config(page_title="OSHCwise", layout="wide")

# A later login flow can set st.session_state["student_name"].
# The URL option makes this first screen easy to preview: ?name=Tala
name = st.session_state.get("student_name") or st.query_params.get("name") or "Tala"
first_name = str(name).strip().split()[0] if str(name).strip() else "Tala"
safe_name = html.escape(first_name)

render_header()

st.markdown(
    """
    <style>
        .stApp { background: #ffffff; font-family: "Lucida Sans", "Lucida Sans Unicode", Arial, sans-serif; }
        header[data-testid="stHeader"] { background: transparent; }
        section[data-testid="stSidebar"] { display: none; }
        .block-container { max-width: 100%; padding: 0 1.5rem; }
        .welcome-screen {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            text-align: center;
            padding-top: clamp(15vh, 23vh, 26vh);
        }
        .welcome-screen h1 {
            color: #143a5a;
            font-family: "Lucida Sans", "Lucida Sans Unicode", Arial, sans-serif;
            font-size: clamp(2rem, 4vw, 3.5rem);
            font-weight: 700;
            letter-spacing: -0.035em;
            margin: 0 0 1.4rem;
        }
        .welcome-screen p {
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
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f'<main class="welcome-screen"><h1>Welcome, {safe_name}!</h1>'
    f'<p>Answer a few questions to personalize your experience.</p></main>',
    unsafe_allow_html=True,
)
if st.button("Continue", type="primary", use_container_width=True):
    st.switch_page("pages/1_Question.py")
