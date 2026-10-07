"""Health-concern question screen for the OSHCwise prototype."""

import base64
from pathlib import Path

import streamlit as st

from app_header import render_header
from voice_section import render_voice_section


st.set_page_config(page_title="OSHCwise", layout="wide")

render_header()

st.markdown(
    """
    <style>
    [class*="st-key-goal_card_"] {
    cursor: pointer;
    transition: border-color 0.2s ease, box-shadow 0.2s ease,
                transform 0.2s ease;
}

[class*="st-key-goal_card_"]:has(button:hover) {
    border-color: #143a5a;
    box-shadow: 0 5px 16px rgba(20, 58, 90, 0.15);
    transform: translateY(-3px);
}
        .stApp {
            background: #ffffff;
            font-family: "Lucida Sans", "Lucida Sans Unicode", Arial, sans-serif;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        section[data-testid="stSidebar"] {
            display: none;
        }

        .block-container {
            max-width: 100%;
            padding: 0 1.5rem;
        }

        .question-screen {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            text-align: center;
            padding-top: clamp(3vh, 5vh, 6vh);
        }

        .question-screen h1 {
            color: #143a5a;
            font-family: "Lucida Sans", "Lucida Sans Unicode", Arial, sans-serif;
            font-size: clamp(1.1rem, 2.2vw, 2rem);
            font-weight: 700;
            letter-spacing: -0.025em;
            margin: 0 0 1.5rem;
        }

        .question-screen h1 .red {
            color: #C8322E;
            display: block;

        }

        [class*="st-key-goal_grid"] {
            max-width: 1050px;
            margin: 0 auto;
        }

        [class*="st-key-goal_card_"] {
            position: relative;
            background: #ffffff;
            border: 1.5px solid #d7dbe1;
            border-radius: 16px;
            padding: 0.7rem 0.5rem 0.9rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            text-align: center;
            min-height: 220px;
        }

        .goal-img {
            display: block;
            width: 100%;
            max-width: 150px;
            height: 150px;
            margin: 0 auto 0.5rem;
            object-fit: contain;
            border-radius: 12px;
        }

        .goal-link {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
            text-decoration: none;
        }

        /* Make the whole card clickable */
        .goal-link::after {
            content: "";
            position: absolute;
            inset: 0;
            z-index: 2;
        }

        [class*="st-key-goal_card_"]:has(.goal-link:hover) {
            border-color: #143a5a;
            box-shadow: 0 5px 16px rgba(20, 58, 90, 0.15);
            transform: translateY(-3px);
        }

        .goal-link, .goal-link:hover, .goal-link:visited {
            text-decoration: none !important;
            color: inherit !important;
        }

        .goal-label {
            font-family: "Lucida Sans", "Lucida Sans Unicode", Arial, sans-serif;
            font-weight: 700;
            font-size: 0.72rem;
            line-height: 1.3;
            color: #123e52;
        }

        [class*="st-key-goal_card_"] [data-testid="stButton"] {
            position: absolute;
            inset: 0;
            z-index: 2;
            width: 100%;
            height: 100%;
            margin: 0;
        }

        [class*="st-key-goal_card_"] [data-testid="stButton"] > button {
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
        }

        [class*="st-key-goal_card_"]:has(.selected-marker) {
            outline: 3px solid #143a5a;
            outline-offset: -3px;
        }

        [class*="st-key-continue_goal"] {
            max-width: 180px;
            margin: 2rem auto 0;
        }

        [class*="st-key-continue_goal"] button {
            width: 100%;
            min-height: 2.6rem;
            background: #808080;
            border: 0;
            border-radius: 6px;
            color: #ffffff;
            font-size: 1rem;
            font-weight: 600;
        }

        [class*="st-key-continue_goal"] button:hover {
            background: #6b6b6b;
            color: #ffffff;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<main class="question-screen">'
    '<h1>What are you most worried about in Australia? '
    '<span class="red">Practice and learn it, Before it happens!</span></h1>'
    '</main>',
    unsafe_allow_html=True,
)

# The images are stored one folder above this Python file.
assets_dir = Path(__file__).parent.parent

options = [
    {"key": "homesick", "file": "homesick.png",
     "label": "I feel homesickness"},
    {"key": "hospital", "file": "hospital.png",
     "label": "I need to go to hospital"},
    {"key": "sick", "file": "feelsick.png",
     "label": "I get sick"},
    {"key": "medication", "file": "medication.png",
     "label": "I need medication"},
    {"key": "find_provider", "file": "find a healthprovider.png",
     "label": "I need to find a health provider"},
    {"key": "comprehensive_oshc", "file": "see a doctor.png",
     "label": "Comprehensive OSHC coverage"},
    {"key": "make_claim", "file": "make_claim.png",
     "label": "I need to make a claim"},
    {"key": "just_learning", "file": "just learn.png",
     "label": "Nothing, just here to learn"},
]

# Cards that open their own page when clicked (card label -> page file)
PAGES = {
    "I need to find a health provider": "pages/Find_Provider_Guide.py",
    "I feel homesickness": "pages/Homesick_Guide.py",
    "I need to go to hospital": "pages/Hospital_Guide.py",
}

if "health_concern" not in st.session_state:
    st.session_state.health_concern = None


def render_goal_card(opt):
    """Display one card. Cards with a page are real links."""
    with st.container(key=f"goal_card_{opt['key']}"):
        img_data = base64.b64encode(
            (assets_dir / opt["file"]).read_bytes()
        ).decode()

        inner = (
            f'<img class="goal-img" '
            f'src="data:image/png;base64,{img_data}" alt="">'
            f'<div class="goal-label">{opt["label"]}</div>'
        )

        # Card has its own page: the whole card is a link
        if opt["label"] in PAGES:
            slug = Path(PAGES[opt["label"]]).stem
            st.markdown(
                f'<a class="goal-link" href="{slug}" target="_self">'
                f'{inner}</a>',
                unsafe_allow_html=True,
            )
            return

        # Other cards: select as before
        selected = st.session_state.health_concern == opt["label"]
        marker = (
            '<span class="selected-marker" style="display:none"></span>'
            if selected
            else ""
        )
        st.markdown(inner + marker, unsafe_allow_html=True)

        if st.button(
            "select",
            key=f"btn_{opt['key']}",
            use_container_width=True,
        ):
            st.session_state.health_concern = opt["label"]
            st.rerun()


# Microphone and typing box (matches what the student says to a card)
render_voice_section(PAGES)

with st.container(key="goal_grid"):
    for row_start in range(0, len(options), 4):
        row = options[row_start : row_start + 4]
        cols = st.columns(4, gap="small")

        for col, opt in zip(cols, row):
            with col:
                render_goal_card(opt)


health_concern = st.session_state.health_concern
if st.button(
    "Continue",
    key="continue_goal",
    type="primary",
    use_container_width=True,
    disabled=health_concern is None,
):
    st.session_state.health_concern = health_concern