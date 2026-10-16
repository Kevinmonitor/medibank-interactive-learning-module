"""
OSHC student assistant.

    streamlit run app/main.py

Three pages. The assistant sits on pages 1 and 2. Page 3 shows aggregate
patterns only and never individual students.
"""

import sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()

import json
import re
import sqlite3
import pandas as pd
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Australia/Melbourne")
except Exception:          # tzdata missing on some systems — fall back to UTC
    _TZ = timezone.utc


def _now_str():
    """Local (Melbourne) timestamp, Sheets-friendly: '2026-10-16 20:45:03'."""
    return datetime.now(_TZ).strftime("%Y-%m-%d %H:%M:%S")
from pathlib import Path

import streamlit as st

from app.pipeline import (Retriever, safety_gate, GATE_RESPONSE, NURSE_LINE,
                          crisis_check, CRISIS_RESPONSE, EMERGENCY_RESPONSE,
                          wellbeing_check, WELLBEING_RESPONSE)
from app.generate import answer as generate_answer

from app.paths import DATA
DB = DATA / "interactions.db"
APPROVED = DATA / "approved_answers.json"


# Styling for the chat bubbles and the source panel. Every rule is scoped
# to a chat testid or to one of our own classes, so this is safe to inject
# on a host app (Tala) without changing the host's own look.
_CHAT_CSS = """
<style>
/* the student's own messages, dark and on the right */
div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]){
  flex-direction:row-reverse}
div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"])
  div[data-testid="stChatMessageContent"]{
  background:#0E2033;color:#fff;margin-left:auto;max-width:80%}
div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"])
  div[data-testid="stChatMessageContent"] p{color:#fff}

/* the assistant's messages */
div[data-testid="stChatMessage"]{background:transparent;padding:.1rem 0}
div[data-testid="stChatMessageContent"]{
  background:#EDF1F5;padding:.7rem .95rem;border-radius:0;
  font-size:.95rem;line-height:1.55;max-width:88%}

div[data-testid="stChatInput"]{border-top:1px solid #CBD6E0}
div[data-testid="stChatInput"] textarea{border-radius:0}

/* the source panel under each answer */
:root{
  --ink:#0E2033; --ink-2:#4A6076; --line:#CBD6E0;
  --paper:#FFFFFF; --green:#0F7A5A; --green-soft:#E3F2EC;
  --amber:#9A6207; --amber-soft:#FCF2DF;
}
.srcbox{background:var(--paper);border:1px solid var(--line);
  padding:.8rem .95rem;margin-bottom:.55rem}
.srcwhere{font-size:.76rem;color:var(--ink-2);margin:0 0 .45rem;
  display:flex;flex-wrap:wrap;gap:.25rem .7rem;align-items:baseline}
.srcwhere b{color:var(--ink)}
.srcwords{margin:0;font-size:.87rem;line-height:1.5;color:var(--ink-2)}
.srcgrade{font-size:.75rem;margin:.5rem 0 0;padding-top:.45rem;
  border-top:1px dashed var(--line);color:var(--amber);font-weight:600}
.srcgrade.easy{color:var(--green)}
.cmp{display:flex;border:1px solid var(--line);margin-bottom:.7rem;overflow:hidden}
.cmp div{flex:1;padding:.6rem .8rem}
.cmp .lab{font-size:.66rem;letter-spacing:.1em;font-weight:700;
  margin:0 0 .15rem;color:var(--ink-2)}
.cmp .val{font-size:1.2rem;font-weight:700;margin:0;font-variant-numeric:tabular-nums}
.cmp .cap{font-size:.72rem;color:var(--ink-2);margin:.1rem 0 0}
.cmp .ours{background:var(--green-soft)} .cmp .ours .val{color:var(--green)}
.cmp .theirs{background:var(--amber-soft);border-left:1px solid var(--line)}
.cmp .theirs .val{color:var(--amber)}
.privnote{font-size:.74rem;color:var(--ink-2);margin:.6rem 0 0;line-height:1.5}
</style>
"""


def inject_chat_css():
    """Call once before rendering the chat. Safe on a host app."""
    st.markdown(_CHAT_CSS, unsafe_allow_html=True)


STYLE = """
<style>
:root{
  --ink:#0E2033; --ink-2:#4A6076; --line:#CBD6E0;
  --paper:#FFFFFF; --floor:#EDF1F5;
  --blue:#0B5FA5; --blue-soft:#E2EDF7;
  --red:#C2151B; --red-soft:#FBE9E9;
  --green:#0F7A5A; --green-soft:#E3F2EC;
  --amber:#9A6207; --amber-soft:#FCF2DF;
}
.stApp{background:var(--floor)}
.block-container{max-width:820px;padding-top:2rem;background:var(--paper);
  border-left:1px solid var(--line);border-right:1px solid var(--line)}
h1{font-size:1.65rem!important;letter-spacing:-.015em;color:var(--ink)}
h2{font-size:1.2rem!important;color:var(--ink)}
h4{font-size:1.02rem!important;color:var(--ink);margin-bottom:.2rem}

/* answer, gate and wellbeing blocks */
div[data-testid="stAlert"]{border-radius:0;border-left-width:4px;padding:1rem 1.15rem}
div[data-testid="stAlertContentSuccess"]{font-size:1.02rem;line-height:1.6}

/* the source panel */
.srcbox{background:var(--paper);border:1px solid var(--line);
  padding:.8rem .95rem;margin-bottom:.55rem}
.srcwhere{font-size:.76rem;color:var(--ink-2);margin:0 0 .45rem;
  display:flex;flex-wrap:wrap;gap:.25rem .7rem;align-items:baseline}
.srcwhere b{color:var(--ink)}
.srcwords{margin:0;font-size:.87rem;line-height:1.5;color:var(--ink-2)}
.srcgrade{font-size:.75rem;margin:.5rem 0 0;padding-top:.45rem;
  border-top:1px dashed var(--line);color:var(--amber);font-weight:600}
.srcgrade.easy{color:var(--green)}

/* readability comparison */
.cmp{display:flex;border:1px solid var(--line);margin-bottom:.7rem;overflow:hidden}
.cmp div{flex:1;padding:.6rem .8rem}
.cmp .lab{font-size:.66rem;letter-spacing:.1em;font-weight:700;
  margin:0 0 .15rem;color:var(--ink-2)}
.cmp .val{font-size:1.2rem;font-weight:700;margin:0;font-variant-numeric:tabular-nums}
.cmp .cap{font-size:.72rem;color:var(--ink-2);margin:.1rem 0 0}
.cmp .ours{background:var(--green-soft)} .cmp .ours .val{color:var(--green)}
.cmp .theirs{background:var(--amber-soft);border-left:1px solid var(--line)}
.cmp .theirs .val{color:var(--amber)}

.privnote{font-size:.74rem;color:var(--ink-2);margin:.6rem 0 0;line-height:1.5}

/* metrics on the dashboard */
div[data-testid="stMetric"]{background:var(--floor);padding:.75rem .9rem;
  border:1px solid var(--line)}
div[data-testid="stMetricValue"]{font-size:1.45rem;color:var(--ink)}
div[data-testid="stMetricLabel"]{font-size:.78rem;color:var(--ink-2)}

/* buttons */
.stButton > button{border-radius:0;border:1.5px solid var(--line);
  font-weight:600;color:var(--ink);background:var(--paper)}
.stButton > button:hover{border-color:var(--blue);color:var(--blue)}

/* input */
.stTextInput input{border-radius:0;border:1.5px solid var(--line)}
.stTextInput input:focus{border-color:var(--blue);box-shadow:none}

/* expanders */
details{border:1px solid var(--line)!important;border-radius:0!important}
summary{font-size:.86rem!important;font-weight:600;color:var(--blue)!important}

#MainMenu,footer{visibility:hidden}
</style>
"""


def md_safe(text):
    """Streamlit treats text between two dollar signs as LaTeX, which turns
    "$100 ... $200" into a formula. Escaping keeps benefit amounts readable."""
    return str(text).replace("$", "\\$")


def _grade(text):
    import re as _re
    sentences = [x for x in _re.split(r"[.!?]+", text) if x.strip()]
    words = _re.findall(r"[A-Za-z']+", text)
    if not sentences or not words:
        return None
    def _syl(w):
        w = _re.sub(r"[^a-z]", "", w.lower())
        if not w: return 0
        n = len(_re.findall(r"[aeiouy]+", w))
        if w.endswith("e") and not w.endswith(("le","ee","ye")) and n > 1:
            n -= 1
        return max(1, n)
    grade = (0.39 * len(words) / len(sentences)
             + 11.8 * sum(_syl(w) for w in words) / len(words)
             - 15.59)
    return round(grade, 1)


def _reads_as(g):
    if g is None: return ""
    if g >= 18: return "Postgraduate level"
    if g >= 13: return "University level"
    if g >= 10: return "Senior school level"
    return "About a 10 year old could read it"


def show_sources(answer_text, passages):
    """Shows the real policy wording behind the answer, and how much harder
    it is to read than the plain version. A page number tells a student
    nothing. The actual sentence lets them check."""
    import html
    ours = _grade(answer_text)
    grades = [g for g in (_grade(p["text"]) for p in passages) if g is not None]
    worst = max(grades) if grades else None

    with st.expander("What this is based on"):
        if ours is not None and worst is not None:
            st.markdown(
                f'<div class="cmp">'
                f'<div class="ours"><p class="lab">THIS ANSWER</p>'
                f'<p class="val">Grade {ours}</p>'
                f'<p class="cap">{_reads_as(ours)}</p></div>'
                f'<div class="theirs"><p class="lab">THE DOCUMENT</p>'
                f'<p class="val">Grade {worst}</p>'
                f'<p class="cap">{_reads_as(worst)}</p></div></div>',
                unsafe_allow_html=True)

        for p in passages:
            g = _grade(p["text"])
            words = html.escape(p["text"][:420])
            if len(p["text"]) > 420:
                words += "..."
            cls = " easy" if (g is not None and g <= 9) else ""
            tail = ("readable" if (g is not None and g <= 9)
                    else "harder than most people can read comfortably")
            st.markdown(
                f'<div class="srcbox">'
                f'<p class="srcwhere"><b>{html.escape(p["section"])}</b>'
                f'<span>page {p["page"]}</span>'
                f'<span>{html.escape(p["product"])}</span>'
                f'<span>effective {html.escape(str(p["effective"]))}</span></p>'
                f'<p class="srcwords">&ldquo;{words}&rdquo;</p>'
                + (f'<p class="srcgrade{cls}">Reading grade {g} &middot; {tail}</p>'
                   if g is not None else "")
                + '</div>', unsafe_allow_html=True)

        st.markdown(
            '<p class="privnote">We saved the topic of this question. '
            'We did not save what you typed, and it is not linked to you.</p>',
            unsafe_allow_html=True)




# ------------------------------------------------------------------ logging
def init_db():
    DB.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS interactions (
        ts TEXT, topic TEXT, confidence REAL, page TEXT,
        source TEXT, routed_to_nurse INTEGER)""")
    con.commit()
    return con



def md_safe(text):
    """Streamlit renders text between two dollar signs as LaTeX, which
    turns '$100 ... $200' into a formula. Escaping them keeps benefit
    amounts readable."""
    return text.replace("$", "\\$")

def log(topic, confidence, page, source, routed=0):
    """Matched topic and confidence only. Never the question text, never a
    member identity. Supports Australian Privacy Principle 2."""
    from app import store
    ts = _now_str()
    con = init_db()
    con.execute("INSERT INTO interactions VALUES (?,?,?,?,?,?)",
                (ts, topic, confidence, page, source, routed))
    con.commit()
    con.close()
    # Mirror to the Google Sheet when it is configured (no-op otherwise).
    store.append_interaction(ts, topic, confidence, page, source, routed)


# ------------------------------------------------------------------ helpers
@st.cache_resource
def load_retriever():
    return Retriever()


@st.cache_data
def load_approved():
    return json.loads(APPROVED.read_text()) if APPROVED.exists() else {}


# The readability gate (generate.py) regenerates anything above this grade.
ANSWER_GATE_GRADE = 9


@st.cache_data
def document_grade():
    """Flesch-Kincaid grade of the Medibank OSHC documents.

    Prefers the measured value in data/readability.json, produced by
    eval/readability.py running textstat over the full text of the published
    PDFs — a figure anyone can reproduce. Falls back to averaging the indexed
    chunks when that file is absent."""
    from app.paths import DATA
    rj = DATA / "readability.json"
    if rj.exists():
        try:
            return float(json.loads(rj.read_text())["document_grade"])
        except Exception:
            pass
    path = DATA / "chunks.json"
    if not path.exists():
        return None
    grades = [g for g in (_grade(c.get("text", ""))
                          for c in json.loads(path.read_text())) if g is not None]
    return round(sum(grades) / len(grades), 1) if grades else None



# ask() renders straight to the page. The chat transcript needs the text
# as well, otherwise every rerun drops the previous answers and leaves a
# column of unanswered questions.
_LAST_RENDER = {}


def log_prompt(raw, corrected, expanded, topic, confidence, product,
               was_corrected, correction_count, synonym_hit, routed):
    """Prototype only. In production, features would be extracted at query
    time and the text discarded. For the demo we keep the text so the NLP
    analysis page can show real patterns."""
    from app import store
    ts = _now_str()
    con = init_db()
    con.execute("""CREATE TABLE IF NOT EXISTS prompt_log (
        ts TEXT, raw TEXT, corrected TEXT, expanded TEXT,
        topic TEXT, confidence REAL, product TEXT,
        was_corrected INTEGER, correction_count INTEGER,
        synonym_hit INTEGER, word_count INTEGER,
        routed INTEGER)""")
    con.execute("INSERT INTO prompt_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (ts, raw, corrected, expanded, topic, confidence, product,
                 int(was_corrected), correction_count,
                 int(synonym_hit), len(raw.split()), int(routed)))
    con.commit()
    con.close()
    # Mirror to the Google Sheet when it is configured (no-op otherwise).
    store.append_prompt({
        "ts": ts, "raw": raw, "corrected": corrected, "expanded": expanded,
        "topic": topic, "confidence": confidence, "product": product,
        "was_corrected": int(was_corrected), "correction_count": correction_count,
        "synonym_hit": int(synonym_hit), "word_count": len(raw.split()),
        "routed": int(routed)})



def _record(kind, text, passages=None):
    _LAST_RENDER["kind"] = kind
    _LAST_RENDER["text"] = text
    _LAST_RENDER["passages"] = passages
    return text



def show_prompt_analysis(original_question, product):
    """Shows what the system did to the question before retrieval."""
    import html as _h
    steps = []
    tier = crisis_check(original_question)
    if tier:
        steps.append(("Safety", "Matched " + tier + " tier. Routed to human.", "block"))
        with st.expander("How your question was processed"):
            for label, detail, status in steps:
                icon = chr(0x1f6d1) if status == "block" else chr(0x2705)
                st.markdown(f"**{icon} {label}** {_h.escape(detail)}")
        return
    if wellbeing_check(original_question):
        steps.append(("Safety", "Matched wellbeing tier. Routed to counselling.", "block"))
        with st.expander("How your question was processed"):
            for label, detail, status in steps:
                icon = chr(0x1f6d1)
                st.markdown(f"**{icon} {label}** {_h.escape(detail)}")
        return
    blocked, _ = safety_gate(original_question)
    if blocked:
        steps.append(("Safety", "Symptom detected. Routed to nurse.", "block"))
        with st.expander("How your question was processed"):
            for label, detail, status in steps:
                icon = chr(0x1f6d1)
                st.markdown(f"**{icon} {label}** {_h.escape(detail)}")
        return
    steps.append(("Safety check", "No crisis, emergency, wellbeing or symptom words. Passed.", "pass"))
    current = original_question
    try:
        from app.spelling import correct, explain
        changes = explain(original_question)
        if changes:
            corrected = correct(original_question)
            change_str = ", ".join(f"\"{old}\" to \"{new}\"" for old, new in changes)
            steps.append(("Spelling correction", "Changed " + change_str, "changed"))
            current = corrected
        else:
            steps.append(("Spelling correction", "No corrections needed.", "pass"))
    except Exception:
        steps.append(("Spelling correction", "Not available.", "pass"))
    try:
        from app.synonyms import expand
        expanded = expand(current)
        if expanded != current:
            added = expanded.replace(current, "").strip()
            steps.append(("Synonym expansion", "Added policy terms: " + added, "changed"))
            current = expanded
        else:
            steps.append(("Synonym expansion", "No shorthand found.", "pass"))
    except Exception:
        steps.append(("Synonym expansion", "Not available.", "pass"))
    steps.append(("Product filter", "Restricted to " + product.title() + " chunks only.", "pass"))
    steps.append(("Query sent to retrieval", current, "final"))
    with st.expander("How your question was processed"):
        for label, detail, status in steps:
            if status == "block": icon = chr(0x1f6d1)
            elif status == "changed": icon = chr(0x1f504)
            elif status == "final": icon = chr(0x1f50d)
            else: icon = chr(0x2705)
            st.markdown(f"**{icon} {label}**\n\n{_h.escape(detail)}")


def ask(question, product, page_name, show_analysis=True):
    """The runtime path. Gate first, always.

    show_analysis controls the technical panels (source wording with
    Flesch-Kincaid reading grades, and the prompt-processing breakdown).
    Students see a clean answer; admins see the analysis."""
    # Tier 1 runs before the wellbeing and clinical checks.
    tier = crisis_check(question)
    if tier == "crisis":
        log("crisis", 1.0, page_name, "lifeline", routed=1)
        st.error(md_safe(_record("crisis", CRISIS_RESPONSE)))
        return
    if tier == "emergency":
        log("emergency", 1.0, page_name, "triple_zero", routed=1)
        st.error(md_safe(_record("crisis", EMERGENCY_RESPONSE)))
        return

    if wellbeing_check(question):
        log("wellbeing", 1.0, page_name, "support_line", routed=1)
        st.info(md_safe(_record("wellbeing", WELLBEING_RESPONSE)))
        return

    blocked, term = safety_gate(question)
    if blocked:
        log("clinical", 1.0, page_name, "nurse_line", routed=1)
        st.error(md_safe(_record("gate", GATE_RESPONSE)))
        return

    r = load_retriever()
    # ---- member balance lookup ------------------------------------------
    balance_words = ["how much", "balance", "remaining", "left",
                     "used", "claim left", "money left", "limit",
                     "berapa", "sisa"]
    is_balance_q = any(b in question.lower() for b in balance_words)
    if is_balance_q:
        try:
            from app.member import lookup, format_balance
            mid = st.session_state.get("member_id", "DEMO001")
            member = lookup(mid)
            if member:
                text = format_balance(member, question)
                st.success(md_safe(text))
                _record("answer", text)
                log("balance", 1.0, page_name, "member_sheet")
                return
        except Exception:
            pass

    hits = r.search(question, product=product, k=3)
    if not hits:
        st.warning(_record("unsure", "I do not have an answer for that. "
                   f"Please call {NURSE_LINE}."))

        try:
            from app.spelling import correct, explain
            _ch = explain(question)
            _co = correct(question) if _ch else question
        except Exception:
            _ch, _co = [], question
        log_prompt(question, _co, _co, 'unmatched',
                   0.0, product, bool(_ch), len(_ch or []),
                   False, False)
        log("unmatched", 0.0, page_name, "fallback")
        if show_analysis:
            show_prompt_analysis(question, product)
        return

    passages = [h[0] for h in hits]
    confidence = float(hits[0][1])

    # Fusion scores below this mean nothing in the corpus matched.
    # Without a floor the system answers confidently from whatever
    # ranked first, which is how an accounting question returns a
    # dental answer.
    MIN_CONFIDENCE = 0.0231  # from tune.py, best balanced accuracy 89%
    if confidence < MIN_CONFIDENCE:
        st.warning(_record("unsure", "I do not have an answer for that. "
                   f"Please call {NURSE_LINE}."))
        log("unmatched", confidence, page_name, "below_threshold")
        return
    topic = passages[0]["section"]
    # Fallback answers must be product specific. Keying on topic
    # alone would give an Essentials member the Comprehensive answer
    # whenever generation fails.
    approved = load_approved().get(product, {}).get(topic)

    member = {"product": product.title(),
              "campus": st.session_state.get("campus"),
              "weeks": st.session_state.get("weeks")}

    text, trace, source = generate_answer(question, passages, member,
                                          fallback=approved)
    log(topic, confidence, page_name, source)

    st.success(md_safe(_record("answer", text, passages)))
    if show_analysis:
        show_sources(text, passages)
    try:
        from app.spelling import correct, explain
        _changes = explain(question)
        _corrected = correct(question) if _changes else question
    except Exception:
        _changes, _corrected = [], question
    try:
        from app.synonyms import expand
        _expanded = expand(_corrected)
        _syn = _expanded != _corrected
    except Exception:
        _expanded, _syn = _corrected, False
    log_prompt(question, _corrected, _expanded, passages[0]["section"],
               confidence, product, bool(_changes), len(_changes or []),
               _syn, False)
    if show_analysis:
        show_prompt_analysis(question, product)
        if trace:
            with st.expander("Checks"):
                st.json(trace)


SUGGESTIONS = [
    "Is the dentist covered?",
    "Why did the doctor charge me?",
    "Can I see a psychologist?",
    "Do I have to wait?",
    "How do I claim?",
]


def assistant(page_name, show_analysis=True, widget=False):
    """A chat rather than a form. History stays in session state, so a
    student can see what they already asked. Answers reference each other,
    and a single question box loses that.

    show_analysis passes through to ask(): True shows the source wording and
    Flesch-Kincaid analysis (admin view), False gives a clean answer only.
    widget=True keeps the input inside the current container (a form, not the
    page-docked st.chat_input) and drops the wide suggestion grid, so the chat
    fits inside a floating 'Message us' panel."""
    inject_chat_css()
    key = "chat_" + page_name

    if key not in st.session_state:
        st.session_state[key] = []

    # replay the transcript
    for turn in st.session_state[key]:
        role, content = turn[0], turn[1]
        kind = turn[2] if len(turn) > 2 else "answer"
        with st.chat_message(role, avatar="\U0001F464" if role == "user" else "\U0001F4C4"):
            if role == "user":
                st.markdown(content)
            elif kind == "crisis" or kind == "gate":
                st.error(content)
            elif kind == "wellbeing":
                st.info(content)
            elif kind == "unsure":
                st.warning(content)
            else:
                st.success(content)

    # suggestions only while the chat is empty
    if not st.session_state[key]:
        if widget:
            st.caption("Ask what your cover includes. For medical advice I will "
                       "put you through to a nurse instead.")
        else:
            st.caption(
                "Ask what your cover includes. Every answer comes from your own "
                "policy documents, and you can open the exact wording it came "
                "from. If you need medical advice I will put you through to a "
                "nurse instead.")
            cols = st.columns(len(SUGGESTIONS))
            for col, text in zip(cols, SUGGESTIONS):
                if col.button(text, key=page_name + "_sug_" + text,
                              use_container_width=True):
                    st.session_state[key + "_pending"] = text
                    st.rerun()

    if widget:
        # A form keeps the text box inside the floating panel; st.chat_input
        # would dock to the bottom of the whole page instead.
        with st.form(key=page_name + "_form", clear_on_submit=True,
                     border=False):
            c_in, c_go = st.columns([5, 1])
            typed = c_in.text_input("Ask about your cover",
                                    key=page_name + "_tin",
                                    placeholder="Type your message",
                                    label_visibility="collapsed")
            sent = c_go.form_submit_button("➤", use_container_width=True)
        if not sent:
            typed = None
    else:
        typed = st.chat_input("Ask about your cover", key=page_name + "_input")
    pending = st.session_state.pop(key + "_pending", None)
    question = typed or pending

    if question:
        st.session_state[key].append(("user", question))
        with st.chat_message("user", avatar="\U0001F464"):
            st.markdown(question)
        with st.chat_message("assistant", avatar="\U0001F4C4"):
            with st.spinner("Checking your policy documents"):
                _LAST_RENDER.clear()
                ask(question,
                    st.session_state.get("product", "comprehensive"),
                    page_name, show_analysis)
        st.session_state[key].append(
            ("assistant", _LAST_RENDER.get("text", ""),
             _LAST_RENDER.get("kind", "answer")))

    st.caption("Please do not type personal health details. Medical "
               "questions go to a nurse, not to this assistant.")

def page_module():
    st.title("How healthcare works here")
    st.write("Five things worth knowing before you need them.")
    for title, body in [
        ("See a GP first",
         "In Australia your regular doctor is called a GP, short for general "
         "practitioner. You see a GP first for anything that is not an "
         "emergency."),
        ("Specialists need a referral",
         "You cannot book a specialist directly. The GP writes you a referral."),
        ("Some clinics cost you nothing",
         "Direct Billing clinics bill us instead of you. Find one before you "
         "need it."),
        ("Emergency departments are for emergencies",
         "For anything not urgent, a GP is faster and usually cheaper."),
        ("Some things are not covered",
         "Dental check-ups, glasses and physiotherapy are not included."),
    ]:
        with st.expander(title):
            st.write(body)
    st.divider()
    assistant("module")


def page_dashboard():
    st.title("Your cover")
    c1, c2, c3 = st.columns(3)
    c1.metric("Cover ends", "Feb 2028")
    c2.metric("Medicine left", "$412")
    c3.metric("Nearest no-cost doctor", "1.2 km")
    st.divider()
    assistant("dashboard")


def page_insights():
    """One lean analytics view for the chatbot. Replaces the old internal and
    NLP pages, which duplicated each other's topic and readability charts."""
    import pandas as pd
    from app import store

    st.markdown('<h1>Chatbot insights</h1>'
                '<p class="sub">What students ask, where the documents fail them, '
                'and what to fix first. Aggregate only, never question text tied '
                'to a student.</p>', unsafe_allow_html=True)

    con = store.connection(init_db)
    total = con.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
    if not total:
        con.close()
        st.info("No questions logged yet. Ask some on the chatbot, then come back.")
        return

    routed = con.execute(
        "SELECT COALESCE(SUM(routed_to_nurse), 0) FROM interactions").fetchone()[0]
    unanswered = con.execute(
        "SELECT COUNT(*) FROM interactions WHERE topic = 'unmatched'").fetchone()[0]

    # Rule-based routes (crisis/clinical/balance) log confidence 1.0 by rule,
    # not by retrieval, and 'unmatched' is a non-answer. Exclude both from the
    # confidence average and the topic chart, so each reflects real answers.
    META = ("crisis", "emergency", "wellbeing", "clinical", "unmatched", "balance")
    ph = ",".join("?" for _ in META)
    avg_conf = con.execute(
        f"SELECT AVG(confidence) FROM interactions "
        f"WHERE topic NOT IN ({ph}) AND confidence > 0", META).fetchone()[0] or 0
    topic_rows = con.execute(
        f"SELECT topic, COUNT(*) n FROM interactions "
        f"WHERE topic NOT IN ({ph}) GROUP BY topic ORDER BY n DESC", META).fetchall()

    try:
        pdf = pd.read_sql("SELECT was_corrected, synonym_hit FROM prompt_log", con)
    except Exception:
        pdf = pd.DataFrame()
    log_rows = con.execute(
        "SELECT topic, COUNT(*) n, AVG(confidence) c, SUM(routed_to_nurse) r "
        "FROM interactions GROUP BY topic ORDER BY n DESC").fetchall()
    con.close()

    corr_pct = pdf["was_corrected"].mean() * 100 if not pdf.empty else 0
    syn_pct = pdf["synonym_hit"].mean() * 100 if not pdf.empty else 0

    # ---- 1. headline KPIs -------------------------------------------------
    unans_pct = unanswered / total * 100 if total else 0
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Questions asked", total)
    k2.metric("Unanswered", f"{unans_pct:.0f}%",
              help="No confident match; the bot sent the student to the nurse line.")
    k3.metric("Routed to a human", int(routed),
              help="Stopped by a safety tier (crisis, emergency, wellbeing, symptom).")
    k4.metric("Avg retrieval score", f"{avg_conf:.3f}",
              help="Mean fusion score of answered questions. Anything below the "
                   "0.023 threshold is rejected as 'unanswered'.")
    st.divider()

    # ---- 2. one topic chart ----------------------------------------------
    st.markdown("#### Where students ask, and the documents are tested")
    st.caption("Coverage topics students reach most. The tallest bar is where "
               "the documentation is working hardest.")
    if topic_rows:
        st.bar_chart({t: n for t, n in topic_rows},
                     use_container_width=True, color="#0B5FA5")
    else:
        st.caption("No coverage questions yet.")
    st.divider()

    # ---- 3. the vocabulary gap (the distinctive insight) -----------------
    st.markdown("#### The language gap")
    st.caption("How far student wording sits from policy wording — the insight a "
               "click-based usage dashboard cannot show.")
    g1, g2 = st.columns(2)
    g1.metric("Needed spelling fixes", f"{corr_pct:.0f}%",
              help="Questions where a policy term was misspelled.")
    g2.metric("Used shorthand", f"{syn_pct:.0f}%",
              help="Questions using slang like 'dent' or 'meds' for the policy word.")
    if syn_pct > 50:
        st.warning("Over half of questions used shorthand. Students and the "
                   "documents speak different languages.")
    st.divider()

    # ---- 4. one readability line -----------------------------------------
    st.markdown("#### Readability")
    doc_grade = document_grade()
    r1, r2, r3 = st.columns(3)
    r1.metric("Policy documents",
              f"Grade {doc_grade}" if doc_grade is not None else "n/a",
              help="Flesch-Kincaid grade, measured from the indexed OSHC documents.")
    r2.metric("Chatbot answers", f"Grade {ANSWER_GATE_GRADE} or lower",
              help="The readability gate regenerates anything above this grade.")
    r3.metric("Simplification",
              f"~{round(doc_grade - ANSWER_GATE_GRADE)} grades"
              if doc_grade is not None else "n/a")
    st.divider()

    # ---- 5. recommended actions ------------------------------------------
    st.markdown("#### What to fix first")
    if topic_rows:
        top_topic, top_n = topic_rows[0]
        st.markdown(f"**1. Rewrite the {top_topic} section first** — "
                    f"{top_n} of {total} questions "
                    f"({top_n * 100 // max(total, 1)}%).")
    if unans_pct > 15:
        st.markdown(f"**2. Close content gaps** — {unans_pct:.0f}% of questions "
                    f"went unanswered.")
    if syn_pct > 40:
        st.markdown(f"**3. Match student language** — {syn_pct:.0f}% used shorthand "
                    f"the documents don't use.")

    # ---- raw log, tucked away --------------------------------------------
    with st.expander("Raw interaction log (topic and confidence only)"):
        st.dataframe(
            [{"Topic": t, "Questions": n, "Avg confidence": round(c or 0, 3),
              "Routed": int(r or 0)} for t, n, c, r in log_rows],
            use_container_width=True)


def _standalone():
    """Runs only when this file is the entry point (streamlit run app/main.py).
    When the chatbot is embedded in Tala, that app owns the page config and
    the navigation, and imports the functions above instead of running this."""
    st.set_page_config(page_title="Your OSHC", layout="centered")
    st.markdown(STYLE, unsafe_allow_html=True)
    inject_chat_css()

    with st.sidebar:
        st.subheader("Demo settings")
        st.session_state["product"] = st.selectbox(
            "Cover", ["comprehensive", "essentials"])
        st.session_state["member_id"] = st.selectbox(
            "Demo student",
            ["DEMO001 - Ayu Pratiwi", "DEMO002 - Wei Chen",
             "DEMO003 - Raj Patel", "DEMO004 - Linh Nguyen",
             "DEMO005 - Maria Santos"],
            index=0).split(" - ")[0]
        st.session_state["campus"] = st.text_input("Campus", "Swinburne")
        st.session_state["weeks"] = st.number_input("Weeks in Australia", 0, 200, 3)
        page = st.radio("Page", ["1. Module", "2. Dashboard", "3. Insights"])

    {"1. Module": page_module,
     "2. Dashboard": page_dashboard,
     "3. Insights": page_insights}[page]()


if __name__ == "__main__":
    _standalone()
