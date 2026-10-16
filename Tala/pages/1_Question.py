"""Health-concern question screen for the OSHCwise prototype."""

import base64
import html
from pathlib import Path

import streamlit as st

import auth
from app_header import render_header

from map import done_module
DATA_FILE = Path(__file__).parent / ".." / "data" / "sample_module_user_list.csv"

from voice_section import render_voice_section
from quiz_button import show_quiz_button

st.set_page_config(page_title="OSHCwise", layout="wide")
auth.require_login()

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
            /* top space keeps the welcome row clear of Streamlit's top bar (it would block clicks) */
            padding: 4rem 1.5rem 0;
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

        /* Welcome row: greeting on the left, Admin dashboard button next to it */
        .welcome-greeting {
            font-family: "Lucida Sans", "Lucida Sans Unicode", Arial, sans-serif;
            font-weight: 700;
            font-size: 1.15rem;
            color: #143a5a;
            min-height: 2.6rem;
            display: flex;
            align-items: center;
        }
        [class*="st-key-to_dashboard"] button {
            background: #C8322E;
            border: 0;
            border-radius: 6px;
            color: #ffffff;
            font-weight: 600;
            min-height: 2.6rem;
        }
        [class*="st-key-to_dashboard"] button:hover {
            background: #a82823;
            color: #ffffff;
        }
        [class*="st-key-log_out"] { text-align: right; }
        [class*="st-key-log_out"] button {
            background: transparent;
            border: 0;
            color: #5b6b73;
            text-decoration: underline;
            min-height: 2.6rem;
        }

        [class*="st-key-goal_grid"] {
            max-width: 1050px;
            margin: 0 auto;
            padding-bottom: 3rem;
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

        [class*="st-key-goal_card_"]:has(button:hover) {
            border-color: #143a5a;
            box-shadow: 0 5px 16px rgba(20, 58, 90, 0.15);
            transform: translateY(-3px);
        }

        .goal-link, .goal-link:hover, .goal-link:visited {
            text-decoration: none !important;
            color: inherit !important;
        }

        [class*="st-key-goal_card_"] [data-testid="stMarkdown"],
        [class*="st-key-goal_card_"] [data-testid="stMarkdownContainer"] {
            width: 100%;
            text-align: center;
        }

        .goal-label {
            width: 100%;
            text-align: center;
            font-family: "Lucida Sans", "Lucida Sans Unicode", Arial, sans-serif;
            font-weight: 700;
            font-size: 0.72rem;
            line-height: 1.3;
            color: #123e52;
        }

        /* the button's wrapper must not be the anchor, so the button covers the whole card */
        [class*="st-key-goal_card_"] div:has(> [data-testid="stButton"]) {
            position: static !important;
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
    </style>
    """,
    unsafe_allow_html=True,
)

# Welcome row (same left edge as the microphone block below)
_, welcome_area, _ = st.columns([1, 5, 1])
with welcome_area:
    greet_col, dash_col, _, out_col = st.columns([1.2, 1.1, 2.2, 0.8])
    with greet_col:
        st.markdown(
            f'<div class="welcome-greeting">Welcome, '
            f'{html.escape(str(st.session_state.get("student_name") or "Student"))}</div>',
            unsafe_allow_html=True,
        )
    with dash_col:
        if auth.is_admin():
            if st.button("Chatbot Insights", key="to_chatbot_dashboard", use_container_width=True):
                st.switch_page(auth.MODULE_DASHBOARD_PAGE)
            if st.button("Module Insights", key="to_module_dashboard", use_container_width=True):
                st.switch_page(auth.CHATBOT_DASHBOARD_PAGE)
    with out_col:
        if st.button("Log out", key="log_out"):
            auth.logout()

st.markdown(
    '<main class="question-screen">'
    '<h1>What are you most worried about in Australia? '
    '<span class="red">Practice and learn it, Before it happens!</span></h1>'
    '</main>',
    unsafe_allow_html=True,
)

# The card pictures are in the "images" folder, one level above this file.
assets_dir = Path(__file__).parent.parent / "images"
if not assets_dir.exists():                      # some copies use a capital I
    assets_dir = Path(__file__).parent.parent / "Images"

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
    "I need medication": "pages/Medication_Guide.py",
    "I get sick": "pages/Sick_Guide.py",
    "I need to make a claim": "pages/Claim_Guide.py",
    "Comprehensive OSHC coverage": "pages/Coverage_Guide.py",
    "Nothing, just here to learn": "pages/Learn_Guide.py",
}

# The hospital guide: use whichever file in "pages" has "hospital" in its name
_hospital = sorted(p for p in (Path(__file__).parent).glob("*.py") if "hospital" in p.name.lower())
if _hospital:
    PAGES["I need to go to hospital"] = f"pages/{_hospital[0].name}"

if "health_concern" not in st.session_state:
    st.session_state.health_concern = None


def render_goal_card(opt):
    """Display one card. Cards with a page open it with switch_page."""
    with st.container(key=f"goal_card_{opt['key']}"):
        img_data = base64.b64encode(
            (assets_dir / opt["file"]).read_bytes()
        ).decode()

        inner = (
            f'<img class="goal-img" '
            f'src="data:image/png;base64,{img_data}" alt="">'
            f'<div class="goal-label">{opt["label"]}</div>'
        )

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
            if opt["label"] in PAGES:
                # i can't tell if the module is actually done but i don't want to duplicate my code
                done_module(DATA_FILE,st.session_state.get("username"),opt["key"])                            
               # Same session, so the student stays logged in
                st.switch_page(PAGES[opt["label"]])
            # this line seems to be dead
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

# Under the cards: the quiz (Myth or fact)
show_quiz_button()


# ---------------------------------------------------------------------------
# Ask-the-chatbot entry (added for the chatbot integration).
# Role-aware, self-contained block appended at the end:
#   - Student: a floating button opens an interactive chat IN PLACE on the hub,
#     answers only (no technical analysis).
#   - Admin: a floating button navigates to the chatbot page, which shows the
#     full Flesch-Kincaid readability analysis for evaluation.
# ---------------------------------------------------------------------------
import sys as _sys
from pathlib import Path as _Path
_CHATBOT = _Path(__file__).resolve().parents[2] / "Muhammad"
if str(_CHATBOT) not in _sys.path:
    _sys.path.insert(0, str(_CHATBOT))

st.markdown(
    """
    <style>
    /* ---- collapsed button (FAB), bottom-right ---- */
    [class*="st-key-chat_fab"] {
        position: fixed; right: 24px; bottom: 24px; z-index: 9999; width: auto;
    }
    [class*="st-key-chat_fab"] a,
    [class*="st-key-chat_fab"] button {
        background: #d81e2c !important; border: none !important;
        border-radius: 999px !important; padding: .7rem 1.15rem !important;
        text-decoration: none !important; box-shadow: 0 8px 22px rgba(0,0,0,.22);
        transition: transform .15s ease, box-shadow .15s ease;
    }
    [class*="st-key-chat_fab"] a:hover,
    [class*="st-key-chat_fab"] button:hover {
        transform: translateY(-2px); box-shadow: 0 12px 28px rgba(0,0,0,.28);
    }
    [class*="st-key-chat_fab"] a *,
    [class*="st-key-chat_fab"] button * { color:#fff !important; font-weight:700 !important; }
    [class*="st-key-chat_fab"] a svg { display: none; }

    /* ---- open chat widget (Message us panel), bottom-right ---- */
    [class*="st-key-chat_widget"] {
        position: fixed; right: 24px; bottom: 24px; z-index: 9999;
        width: min(370px, calc(100vw - 32px)); max-height: 74vh; overflow-y: auto;
        background: #ffffff; border-radius: 14px; padding: 0 .9rem .5rem;
        box-shadow: 0 14px 40px rgba(0,0,0,.28);
    }
    /* red header bar, full width of the panel */
    [class*="st-key-chat_widget"] .cw-head {
        position: sticky; top: 0; z-index: 2;
        background: #d81e2c; color: #fff; font-weight: 700; font-size: 1rem;
        margin: 0 -.9rem .4rem; padding: .8rem 1rem; border-radius: 14px 14px 0 0;
    }
    /* close button, over the red bar, top-right */
    [class*="st-key-cw_close"] {
        position: absolute; top: 8px; right: 10px; z-index: 3; width: auto;
    }
    [class*="st-key-cw_close"] button {
        background: transparent !important; border: none !important; color:#fff !important;
        font-size: 1.1rem; padding: .2rem .5rem !important; box-shadow: none !important;
    }
    /* send button on the input form */
    [class*="st-key-chat_widget"] [data-testid="stFormSubmitButton"] button {
        background: #d81e2c !important; color:#fff !important; border:none !important;
        border-radius: 8px !important; font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if auth.is_admin():
    # Admin: navigate to the chatbot page (full analysis view).
    with st.container(key="chat_fab"):
        st.page_link("pages/Ask_Chatbot.py", label="📊 Ask &amp; analyse")
else:
    # Student: a floating "Message us" style chat panel, opened from the FAB.
    if "hub_chat_open" not in st.session_state:
        st.session_state["hub_chat_open"] = False

    if not st.session_state["hub_chat_open"]:
        with st.container(key="chat_fab"):
            if st.button("💬 Ask about your cover", key="open_hub_chat"):
                st.session_state["hub_chat_open"] = True
                st.rerun()
    else:
        with st.container(key="chat_widget"):
            st.markdown('<div class="cw-head">💬 Ask about your cover</div>',
                        unsafe_allow_html=True)
            with st.container(key="cw_close"):
                if st.button("✕", key="close_hub_chat"):
                    st.session_state["hub_chat_open"] = False
                    st.rerun()
            st.session_state.setdefault("product", "comprehensive")
            from app.main import assistant as _assistant
            _assistant("student", show_analysis=False, widget=True)
