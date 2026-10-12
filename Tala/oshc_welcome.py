
"""First screen of the OSHC student learning application."""
import html

import streamlit as st
from app_header import render_header
import auth

st.set_page_config(page_title="OSHCwise", initial_sidebar_state="collapsed", layout="wide")

# (Not read from session_state: after an admin login it would still say "Admin".)
name = st.query_params.get("name") or "Student"
first_name = str(name).strip().split()[0] if str(name).strip() else "Student"
safe_name = html.escape(first_name)

if "screen" not in st.session_state:
    st.session_state.screen = "intro"
render_header()

# After a successful login in the pop-up, go straight to the question page
if st.session_state.pop("go_welcome", False):
    st.switch_page("pages/1_Question.py")

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

st.markdown(
    '<main class="intro"><h1>OSHC<span class="wise-text">wise</span></h1>'
    '<p>A Medibank OSHC learning platform that<br>'
    'adapts to <strong>you</strong>.</p></main>',
    unsafe_allow_html=True,
)

# ---------- Login ----------
# Two big red buttons. Each opens a small pop-up window that asks for a username and
# a password (accounts are in auth.py, a prototype login).
st.markdown(
    """
    <style>
        /* the two buttons: red, bigger, close together */
        [class*="st-key-login_area"] div.stButton,
        [class*="st-key-login_area"] div[data-testid="stButton"] {
            margin: 2.5rem 0 0 !important;
        }
        [class*="st-key-login_area"] div.stButton > button,
        [class*="st-key-login_area"] div[data-testid="stButton"] > button {
            max-width: 360px;
            min-height: 3.6rem;
            font-size: 1.15rem;
            background: #C8322E;
            color: #ffffff;
        }
        [class*="st-key-login_area"] div.stButton > button:hover,
        [class*="st-key-login_area"] div[data-testid="stButton"] > button:hover {
            background: #a82823;
            color: #ffffff;
        }
        /* the pop-up window */
        div[data-testid="stDialog"] [data-testid="stForm"] { border: 0; padding: 0; }
        div[data-testid="stDialog"] div.stButton,
        div[data-testid="stDialog"] div[data-testid="stFormSubmitButton"] {
            margin: 1rem 0 0 !important;
            display: block !important;
        }
        div[data-testid="stDialog"] div.stButton > button,
        div[data-testid="stDialog"] div[data-testid="stFormSubmitButton"] > button {
            max-width: none;
            width: 100%;
            min-height: 2.8rem;
            background: #C8322E;
            border: 0;
            border-radius: 6px;
            color: #ffffff;
            font-size: 1rem;
            font-weight: 600;
        }
        div[data-testid="stDialog"] div[data-testid="stFormSubmitButton"] > button:hover {
            background: #a82823;
            color: #ffffff;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def _login_form(role: str) -> None:
    """The username and password form inside the pop-up (Enter also logs in)."""
    with st.form(f"{role}_form", border=False):
        username = st.text_input("Username", key=f"{role}_user")
        password = st.text_input("Password", type="password", key=f"{role}_pw")
        submitted = st.form_submit_button("Login", use_container_width=True)
    if submitted:
        if auth.check_login(role, username, password):
            auth.login(role, first_name if role == "student" else "Admin")
            st.session_state["go_welcome"] = True
            st.rerun()                       # closes the pop-up, then the page moves on
        else:
            st.error("The username or password is not right.")


@st.dialog("Login as a student")
def student_dialog() -> None:
    _login_form("student")


@st.dialog("Login as an administrator")
def admin_dialog() -> None:
    _login_form("admin")


with st.container(key="login_area"):
    _, left, right, _ = st.columns([1.6, 1.4, 1.4, 1.6], gap="small")
    with left:
        if st.button("Login as a student", use_container_width=True):
            student_dialog()
    with right:
        if st.button("Login as an administrator", use_container_width=True):
            admin_dialog()
