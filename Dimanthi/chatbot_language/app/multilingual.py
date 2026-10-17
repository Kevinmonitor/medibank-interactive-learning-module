"""
Language support for the OSHC chatbot - Dimi's part
English, Sinhala (සිංහල), Farsi (فارسی), Vietnamese (Tiếng Việt), Bahasa Indonesia

What happens when a student types a question:
  1. ML language detection     (chat_language.py) finds the language, e.g. Sinhala 98% sure
  2. Safety in 5 languages     (chat_safety.py)   checks the ORIGINAL words first
  3. ML question understanding (chat_topics.py)   finds the topic in any of the 5 languages,
                                                  e.g. "mta kiyanna medical certificate gnne kohenda"
                                                  -> Doctor / GP visits -> "Why did the doctor charge me?"
  4. The chatbot finds and checks the answer in English, exactly as before
  5. The answer is shown in the student's language:
       - the approved answers and all safety messages are translated in advance
         (data/chat_page_text.json, data/chat_messages.json) and checked for numbers
       - any other answer is translated by the AI (chat_translate.py) only if a GROQ key is set
  6. The page itself (headings, tips, sidebar, "What this is based on") is translated by
     chat_page_layer.js, without changing the page code

Steps 1, 2, 3, 5 (approved answers) and 6 work with no internet and no AI key.
Nothing the student types is saved by these files.
"""

import html
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from app import chat_language, chat_safety, chat_topics, chat_translate
from app.chat_language import LANGS, LANG_NAMES, ENGLISH_NAMES, RTL

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
MESSAGES = json.loads((DATA / "chat_messages.json").read_text(encoding="utf-8"))
PAGE_TEXT = json.loads((DATA / "chat_page_text.json").read_text(encoding="utf-8"))
LANG_KEY = "chat_lang"          # the language the chatbot is using now
TURN_KEY = "_chat_lang_turn"    # what happened to the last question (memory only)
HINT_CONFIDENCE = 0.60          # how sure the topic model must be to choose the approved answer


def current() -> str:
    return st.session_state.get(LANG_KEY, "en")


def ui(key: str, **values) -> str:
    text = MESSAGES.get(current(), MESSAGES["en"]).get(key) or MESSAGES["en"][key]
    return text.format(**values) if values else text


def suggestions() -> list:
    return [ui(f"sug_{i}") for i in range(1, 6)]


# ---------- 1-3: before the chatbot searches ----------

def prepare(question: str) -> str:
    """Language, safety and topic. Returns the English question the chatbot searches with."""
    lang, confidence, ranked = chat_language.detect(question)
    if lang and confidence >= chat_language.MIN_CONFIDENCE:
        st.session_state[LANG_KEY] = lang
    lang = current()
    topic, topic_p, topic_ranked = chat_topics.understand(question)
    turn = {"original": question, "detected": lang, "confidence": confidence, "ranked": ranked[:3],
            "crisis": chat_safety.crisis(question), "wellbeing": chat_safety.wellbeing(question),
            "clinical": chat_safety.clinical(question), "english": question, "how": "same",
            "topic": topic, "topic_p": topic_p, "topic_ranked": topic_ranked}
    st.session_state[TURN_KEY] = turn

    # Safety first: these are answered from the ready-made messages, never sent to the AI
    if turn["crisis"] or turn["wellbeing"] or turn["clinical"]:
        return question

    english_buttons = {MESSAGES[l][f"sug_{i}"]: MESSAGES["en"][f"sug_{i}"] for l in LANGS for i in range(1, 6)}
    canonical = chat_topics.TOPICS.get(topic, (None, None))[0]
    if question.strip() in english_buttons:                      # a suggestion button
        turn["english"], turn["how"] = english_buttons[question.strip()], "button"
    elif lang != "en" and chat_translate.available():            # AI translation (best for long questions)
        turn["english"] = chat_translate.to_english(question, lang)
        turn["how"] = "ai" if turn["english"] != question else "same"
        if turn["how"] == "same" and canonical:                  # AI failed: use the ML topic model
            turn["english"], turn["how"] = canonical, "topic"
    elif lang != "en" and canonical:                             # ML topic model, no AI needed
        turn["english"], turn["how"] = canonical, "topic"
    return turn["english"]


def _turn() -> dict:
    return st.session_state.get(TURN_KEY, {})


def extra_crisis():
    return _turn().get("crisis")


def extra_wellbeing():
    return _turn().get("wellbeing")


def extra_gate():
    return _turn().get("clinical")


def small_talk():
    """'hi' / 'thanks' -> a friendly hello. A question nobody could understand -> help text."""
    turn = _turn()
    if turn.get("topic") == "hello" and turn.get("how") != "button":
        return MESSAGES["en"]["greeting"]
    if current() != "en" and turn.get("how") == "same" and not turn.get("topic"):
        return MESSAGES["en"]["not_understood"]
    return None


def topic_hint():
    """The approved-answer topic, when the topic model is sure (fixes e.g. 'How do I claim?')."""
    turn = _turn()
    if turn.get("topic_p", 0) >= HINT_CONFIDENCE:
        return chat_topics.TOPICS.get(turn.get("topic"), (None, None))[1]
    return None


# ---------- 5: before the student sees the answer ----------

def _fixed_key(text: str):
    """Is this a ready-made message? Then the translation written in advance is used."""
    from app.pipeline import CRISIS_RESPONSE, EMERGENCY_RESPONSE, WELLBEING_RESPONSE, GATE_RESPONSE
    from app.generate import _no_answer
    known = {CRISIS_RESPONSE: "crisis", EMERGENCY_RESPONSE: "emergency",
             WELLBEING_RESPONSE: "wellbeing", GATE_RESPONSE: "gate", _no_answer(): "no_answer"}
    known.update({v: k for k, v in MESSAGES["en"].items()})
    if text in known:
        return known[text]
    if text.startswith("I do not have an answer for that."):
        return "unsure"
    return None


def localise(kind: str, text: str, passages=None) -> str:
    lang = current()
    if not text:
        return text
    key = _fixed_key(text)
    if key:
        return MESSAGES[lang][key]
    if lang == "en":
        return text
    ready = PAGE_TEXT["answers"].get(text.strip(), {}).get(lang)
    if ready:                                                  # approved answer, translated in advance
        return f"{ready}\n\n*{MESSAGES[lang]['translated_note']}*"
    translated, ok = chat_translate.from_english(text, lang)
    note = MESSAGES[lang]["translated_note"] if ok else MESSAGES[lang]["english_only"]
    return f"{translated}\n\n*{note}*"


# ---------- 6: screen parts ----------

LANG_COLOURS = {"en": "#2563eb", "si": "#c2410c", "fa": "#047857", "vi": "#dc2626", "id": "#7c3aed"}

CSS = """
<style>
/* every paragraph takes the direction of its own first letter: Farsi right-to-left, others left-to-right */
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li, [data-testid="stExpander"] p,
[data-testid="stChatInput"] textarea, [data-testid="stCaptionContainer"] p {unicode-bidi: plaintext; text-align: start}

/* ---- Language card (Dimi) ---- */
.lm-card{background:linear-gradient(135deg,#0E2033 0%,#16407a 55%,#1d6fb8 100%);color:#fff;border-radius:16px;
  padding:16px 18px;margin:6px 0 10px 0;box-shadow:0 8px 24px rgba(14,32,51,.18);position:relative;overflow:hidden}
.lm-card:after{content:"";position:absolute;right:-40px;top:-40px;width:160px;height:160px;border-radius:50%;
  background:radial-gradient(circle,rgba(255,255,255,.18),rgba(255,255,255,0) 70%)}
.lm-head{display:flex;align-items:center;gap:12px}
.lm-globe{width:42px;height:42px;border-radius:12px;background:rgba(255,255,255,.14);display:flex;
  align-items:center;justify-content:center;font-size:22px;flex:none}
.lm-title{font-size:1.05rem;font-weight:700;letter-spacing:.01em}
.lm-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.lm-chip{font-size:.74rem;padding:3px 10px;border-radius:999px;background:rgba(255,255,255,.12);
  border:1px solid rgba(255,255,255,.22);color:#e6eefb;white-space:nowrap}
.lm-chip.on{background:#fff;color:#0E2033;font-weight:700;border-color:#fff}
.lm-badge{margin-left:auto;font-size:.68rem;font-weight:700;letter-spacing:.08em;padding:4px 9px;border-radius:8px;
  background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.3);white-space:nowrap;align-self:flex-start}
.lm-panel{background:#fff;border:1px solid #d7e0ea;border-radius:14px;padding:12px 14px;margin-bottom:10px;
  box-shadow:0 2px 10px rgba(14,32,51,.06)}
.lm-cap{font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#4A6076;margin-bottom:8px}
.lm-row{display:grid;grid-template-columns:150px 1fr 44px;align-items:center;gap:10px;margin:5px 0;font-size:.84rem;color:#0E2033}
.lm-bar{height:8px;border-radius:99px;background:#edf1f5;overflow:hidden}
.lm-bar span{display:block;height:100%;border-radius:99px}
.lm-pct{text-align:right;font-variant-numeric:tabular-nums;color:#4A6076;font-size:.8rem}
.lm-tags{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.lm-tag{font-size:.8rem;padding:5px 11px;border-radius:10px;background:#eef4ff;color:#16407a;border:1px solid #cfdcf3}
.lm-tag b{font-weight:700}
.lm-tag.topic{background:#ecfdf5;color:#065f46;border-color:#bfe8d6}
.lm-hint{font-size:.85rem;color:#4A6076;padding:6px 2px 10px 2px}
@media (max-width:640px){.lm-row{grid-template-columns:110px 1fr 40px}.lm-badge{display:none}}
</style>
"""


def _picked(widget_key):
    st.session_state[LANG_KEY] = st.session_state[widget_key]


def _page_layer():
    lang = current()
    data = {"lang": lang,
            "page": {en: tr[lang] for en, tr in PAGE_TEXT["page"].items()} if lang != "en" else {},
            "patterns": [[re, tr[lang]] for re, tr in PAGE_TEXT["patterns"]] if lang != "en" else []}
    js = (HERE / "chat_page_layer.js").read_text(encoding="utf-8")
    components.html("<script>" + js.replace("__DATA__", json.dumps(data, ensure_ascii=False)) + "</script>",
                    height=0)


def language_bar(page_name: str):
    """Language picker + page translation. Changes by itself when the model finds the student's language."""
    st.markdown(CSS, unsafe_allow_html=True)
    # A question was just sent: find its language now, so the whole page is drawn in that language
    waiting = st.session_state.get(page_name + "_input") or st.session_state.get("chat_" + page_name + "_pending")
    if isinstance(waiting, str) and waiting.strip():
        lang, confidence, _ = chat_language.detect(waiting)
        if lang and confidence >= chat_language.MIN_CONFIDENCE:
            st.session_state[LANG_KEY] = lang
    _page_layer()
    st.session_state["_lang_at_render"] = current()
    lang = current()

    # 1. the coloured header with the 5 languages
    chips = "".join(f"<span class='lm-chip{' on' if c == lang else ''}'>{LANG_NAMES[c]}</span>" for c in LANGS)
    st.markdown(f"<div class='lm-card'><div class='lm-head'><div class='lm-globe'>🌏</div><div>"
                f"<div class='lm-title'>{ui('ui_title')}</div><div class='lm-chips'>{chips}</div></div>"
                f"</div></div>", unsafe_allow_html=True)

    # 2. the language picker
    widget_key = page_name + "_lang_pick"
    st.session_state[widget_key] = lang
    st.selectbox(ui("lang_label"), LANGS, format_func=lambda c: LANG_NAMES[c], key=widget_key,
                 on_change=_picked, args=(widget_key,), label_visibility="collapsed")

    # 3. how the models understood the last question
    turn = _turn()
    if not turn.get("ranked"):
        st.markdown(f"<div class='lm-hint'>{ui('lang_auto')}</div>", unsafe_allow_html=True)
        return
    rows = "".join(
        f"<div class='lm-row'><span>{LANG_NAMES[c]}</span><div class='lm-bar'><span style='width:{p * 100:.0f}%;"
        f"background:{LANG_COLOURS[c]}'></span></div><span class='lm-pct'>{p:.0%}</span></div>"
        for c, p in turn["ranked"][:3])
    tags = ""
    if turn.get("topic"):
        tags += (f"<span class='lm-tag topic'>🎯 {ui('ui_topic')}: <b>{ui('topic_' + turn['topic'])}</b> "
                 f"{turn['topic_p']:.0%}</span>")
    if turn.get("english") and turn["english"] != turn["original"]:
        tags += f"<span class='lm-tag'>🔎 {ui('ui_search')}: <b>{html.escape(turn['english'])}</b></span>"
    st.markdown(f"<div class='lm-panel'><div class='lm-cap'>{ui('ui_last')}</div>{rows}"
                + (f"<div class='lm-tags'>{tags}</div>" if tags else "") + "</div>", unsafe_allow_html=True)


def rerun_if_language_changed():
    """Backup only: normally the language is found before the page is drawn (language_bar)."""
    if st.session_state.get("_lang_at_render", current()) != current():
        st.rerun()


def analysis_steps() -> list:
    """Language steps for the chatbot's 'How your question was processed' box, in the student's language."""
    return []   # not shown: the language card above the chat already shows these results
    turn = _turn()
    if not turn:
        return []
    sure = ui("sure")
    others = ", ".join(f"{ENGLISH_NAMES[c]} {p:.0%}" for c, p in turn["ranked"][1:])
    steps = [(ui("step_lang"), f"{LANG_NAMES[turn['detected']]} ({turn['confidence']:.0%} {sure})"
              + (f" · {others}" if others else "") + " · TF-IDF + Logistic Regression", "pass")]
    if turn.get("topic"):
        steps.append((ui("step_topic"), f"{ui('topic_' + turn['topic'])} ({turn['topic_p']:.0%} {sure})"
                      " · TF-IDF + Logistic Regression", "pass"))
    if turn["english"] != turn["original"]:
        steps.append((ui("step_translate"), turn["english"], "changed"))
    return steps
