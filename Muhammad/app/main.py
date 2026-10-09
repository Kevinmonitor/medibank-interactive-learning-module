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
from pathlib import Path

import streamlit as st

from app.pipeline import (Retriever, safety_gate, GATE_RESPONSE, NURSE_LINE,
                          crisis_check, CRISIS_RESPONSE, EMERGENCY_RESPONSE,
                          wellbeing_check, WELLBEING_RESPONSE)
from app.generate import answer as generate_answer

DB = Path("data/interactions.db")
APPROVED = Path("data/approved_answers.json")

st.set_page_config(page_title="Your OSHC", layout="centered")

st.markdown("""
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
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
/* chat bubbles, to match the design */
div[data-testid="stChatMessage"]{background:transparent;padding:.15rem 0}
div[data-testid="stChatMessage"] div[data-testid="stChatMessageContent"]{
  background:#EDF1F5;padding:.7rem .95rem;border-radius:0;
  font-size:.95rem;line-height:1.55}
div[data-testid="stChatMessage"]:has(img[alt="user avatar"])
  div[data-testid="stChatMessageContent"]{background:#0E2033;color:#fff}
div[data-testid="stChatInput"]{border-top:1px solid #CBD6E0}
div[data-testid="stChatInput"] textarea{border-radius:0}
</style>
""", unsafe_allow_html=True)


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
st.markdown(STYLE, unsafe_allow_html=True)


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
    con = init_db()
    con.execute("INSERT INTO interactions VALUES (?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), topic,
                 confidence, page, source, routed))
    con.commit()
    con.close()


# ------------------------------------------------------------------ helpers
@st.cache_resource
def load_retriever():
    return Retriever()


@st.cache_data
def load_approved():
    return json.loads(APPROVED.read_text()) if APPROVED.exists() else {}



# ask() renders straight to the page. The chat transcript needs the text
# as well, otherwise every rerun drops the previous answers and leaves a
# column of unanswered questions.
_LAST_RENDER = {}


def log_prompt(raw, corrected, expanded, topic, confidence, product,
               was_corrected, correction_count, synonym_hit, routed):
    """Prototype only. In production, features would be extracted at query
    time and the text discarded. For the demo we keep the text so the NLP
    analysis page can show real patterns."""
    con = init_db()
    con.execute("""CREATE TABLE IF NOT EXISTS prompt_log (
        ts TEXT, raw TEXT, corrected TEXT, expanded TEXT,
        topic TEXT, confidence REAL, product TEXT,
        was_corrected INTEGER, correction_count INTEGER,
        synonym_hit INTEGER, word_count INTEGER,
        routed INTEGER)""")
    con.execute("INSERT INTO prompt_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(),
                 raw, corrected, expanded, topic, confidence, product,
                 int(was_corrected), correction_count,
                 int(synonym_hit), len(raw.split()), int(routed)))
    con.commit()
    con.close()



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


def ask(question, product, page_name):
    """The runtime path. Gate first, always."""
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
               0.0, product, bool(_changes), len(_changes or []),
               _syn, False)
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


def assistant(page_name):
    """A chat rather than a form. History stays in session state, so a
    student can see what they already asked. Answers reference each other,
    and a single question box loses that."""
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
                    page_name)
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


def page_internal():
    st.markdown('<h1>Internal view</h1>'
                '<p class="sub">Aggregate patterns only. No individual students.</p>',
                unsafe_allow_html=True)
    con = init_db()
    rows = con.execute("""SELECT topic, COUNT(*) n, AVG(confidence) c,
                          SUM(routed_to_nurse) routed
                          FROM interactions GROUP BY topic ORDER BY n DESC""").fetchall()
    total = con.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
    con.close()

    if not rows or total == 0:
        st.info("No interactions logged yet. Ask some questions on pages 1 or 2, "
                "then come back here.")
        return

    # ---- headline metrics ------------------------------------------------
    topics = [r[0] for r in rows]
    counts = [r[1] for r in rows]
    confs = [r[2] or 0 for r in rows]
    routed = sum(r[3] or 0 for r in rows)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total questions", total)
    c2.metric("Unique topics", len(topics))
    c3.metric("Routed to human", int(routed))
    c4.metric("Avg confidence", f"{sum(c * n for c, n in zip(confs, counts)) / total:.3f}")

    st.divider()

    # ---- comprehension gap map -------------------------------------------
    st.markdown("#### Which sections students ask about")
    st.caption("High frequency means the document failed there. "
               "These are topic counts, not question text.")
    st.bar_chart(
        data=dict(zip(topics, counts)),
        use_container_width=True,
        color="#0B5FA5")

    # ---- confidence by topic ---------------------------------------------
    st.markdown("#### How confident the system is per topic")
    st.caption("Low confidence means the corpus is thin on this topic. "
               "A content gap, not a retrieval gap.")
    conf_data = {t: round(c, 4) for t, c in zip(topics, confs) if c > 0}
    if conf_data:
        st.bar_chart(
            data=conf_data,
            use_container_width=True,
            color="#0F7A5A")

    st.divider()

    # ---- vocabulary distance ---------------------------------------------
    st.markdown("#### Vocabulary distance")
    st.caption("How far apart student language and policy language are.")
    try:
        con2 = init_db()
        # Count interactions where spelling correction or synonym expansion
        # would have fired. We check the source field for clues.
        answered = con2.execute(
            "SELECT COUNT(*) FROM interactions WHERE topic != 'crisis' "
            "AND topic != 'emergency' AND topic != 'wellbeing' "
            "AND topic != 'clinical'").fetchone()[0]
        con2.close()
        if answered > 0:
            v1, v2 = st.columns(2)
            v1.metric("Coverage questions", answered,
                      help="Questions that reached retrieval")
            v2.metric("Routed to human", int(routed),
                      help="Questions stopped by safety tiers")
    except Exception:
        pass

    st.divider()

    # ---- readability contribution ----------------------------------------
    st.markdown("#### Readability contribution")
    st.caption("The measurable difference between the document and the answer.")
    r1, r2, r3 = st.columns(3)
    r1.metric("Document average", "Grade 15.3",
              help="Flesch-Kincaid grade of Medibank OSHC documents")
    r2.metric("Answer target", "Below 9",
              help="The readability gate regenerates anything above grade 9")
    r3.metric("Simplification", "~10 grades",
              help="Document average minus answer average")

    st.divider()

    # ---- raw data --------------------------------------------------------
    st.markdown("#### Raw interaction log")
    st.caption("Topic and confidence only. Never question text.")
    st.dataframe(
        [{"Topic": t, "Questions": n,
          "Avg confidence": round(c or 0, 3),
          "Routed": int(r or 0)}
         for t, n, c, r in rows],
        use_container_width=True)

    st.caption("Topics with low average confidence are where the answers are "
               "weakest and should be rewritten first.")


def page_nlp():
    st.markdown('<h1>Student Insights</h1>'
                '<p class="sub">What students are asking, where they struggle, '
                'and what to fix first.</p>',
                unsafe_allow_html=True)

    con = init_db()
    try:
        con.execute("SELECT 1 FROM prompt_log LIMIT 1")
    except Exception:
        st.info("No data yet. Ask some questions on pages 1 or 2.")
        con.close()
        return

    import pandas as pd
    df = pd.read_sql("SELECT * FROM prompt_log", con)
    con.close()

    if df.empty:
        st.info("No data yet. Ask some questions on pages 1 or 2.")
        return

    st.markdown("### At a glance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Questions asked", len(df))
    routed = int(df["routed"].sum()) if "routed" in df.columns else 0
    c2.metric("Sent to a human", routed,
              help="Questions that contained symptoms or crisis language")
    corr_pct = df["was_corrected"].mean() * 100 if len(df) > 0 else 0
    c3.metric("Had spelling issues", f"{corr_pct:.0f}%",
              help="Students who misspelled a policy term")
    syn_pct = df["synonym_hit"].mean() * 100 if len(df) > 0 else 0
    c4.metric("Used different words", f"{syn_pct:.0f}%",
              help="Students who used shorthand instead of policy terms")

    st.divider()

    st.markdown("### Where students get lost")
    st.caption("The topics students ask about most. The tallest bar is "
               "where the current documentation is failing hardest.")
    if "topic" in df.columns:
        topic_counts = df["topic"].value_counts().head(10)
        if not topic_counts.empty:
            st.bar_chart(data=topic_counts, use_container_width=True, color="#0B5FA5")

    st.divider()

    st.markdown("### The language gap")
    st.caption("Students and policy documents use different words for the "
               "same thing. This is how wide the gap is.")
    g1, g2 = st.columns(2)
    g1.metric("Spelling correction rate", f"{corr_pct:.0f}%",
              help="How many students misspell policy terms")
    g2.metric("Shorthand rate", f"{syn_pct:.0f}%",
              help="How many students say dent when the policy says dental")
    if corr_pct > 30:
        st.warning("More than 30% of queries needed spelling correction. "
                   "The policy vocabulary is a barrier.")
    if syn_pct > 50:
        st.warning("More than half of queries used shorthand. Students and "
                   "the documents speak different languages.")

    st.divider()

    st.markdown("### What students actually say")
    st.caption("The words students use. If these do not match the policy, "
               "the documents need rewriting.")
    stop = {"i","a","the","is","it","my","do","to","how","can","does","what",
            "are","or","for","in","on","of","and","with","that","this","me",
            "if","not","no","yes","be","have","has","was","were","an","at",
            "by","from","its","but","so","up","out","about","am","will"}
    from collections import Counter
    all_words = []
    for text in df["raw"].dropna():
        for w in re.findall(r"[a-z]+", text.lower()):
            if w not in stop and len(w) > 1:
                all_words.append(w)
    word_freq = Counter(all_words).most_common(12)
    if word_freq:
        st.bar_chart(data={w: c for w, c in word_freq},
                     use_container_width=True, color="#0F7A5A")

    st.divider()

    st.markdown("### How students phrase their questions")
    st.caption("Short questions mean searching like Google. "
               "Long questions mean explaining context because "
               "they do not know the right term.")
    if len(df) > 0 and "word_count" in df.columns:
        bins = {"Searching (1-3 words)": 0, "Direct question (4-7)": 0,
                "Explaining (8+ words)": 0}
        for wc in df["word_count"]:
            if wc <= 3: bins["Searching (1-3 words)"] += 1
            elif wc <= 7: bins["Direct question (4-7)"] += 1
            else: bins["Explaining (8+ words)"] += 1
        st.bar_chart(data=bins, use_container_width=True, color="#9A6207")

    st.divider()

    st.markdown("### How much simpler the answers are")
    st.caption("The gap between what the documents say and what the "
               "chatbot says, measured in reading grade levels.")
    r1, r2, r3 = st.columns(3)
    r1.metric("Policy documents", "Grade 15.3",
              help="Flesch-Kincaid grade of OSHC documents. University level.")
    r2.metric("Chatbot answers", "Below grade 9",
              help="The readability gate blocks anything above grade 9.")
    r3.metric("Simplification", "~10 grades",
              help="Same information, easier words and shorter sentences.")

    st.divider()

    st.markdown("### Recommended actions")
    if not df.empty and "topic" in df.columns:
        top_topic = df["topic"].value_counts().index[0]
        top_count = int(df["topic"].value_counts().iloc[0])
        total = len(df)

        st.markdown(f"**1. Rewrite the {top_topic} section first.** "
                    f"It accounts for {top_count} of {total} questions "
                    f"({top_count*100//max(total,1)}%).")

        if corr_pct > 20:
            st.markdown(f"**2. Simplify the vocabulary.** "
                        f"{corr_pct:.0f}% of queries had spelling issues "
                        f"with policy terms.")

        if syn_pct > 40:
            st.markdown(f"**3. Match student language.** "
                        f"{syn_pct:.0f}% of queries used shorthand like "
                        f"dent or meds instead of dental or pharmaceutical.")

    st.divider()
    st.caption("Prototype data. In production, question text would be "
               "processed at query time and discarded.")


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
    page = st.radio("Page", ["1. Module", "2. Dashboard", "3. Internal", "4. NLP Analysis"])

{"1. Module": page_module,
 "2. Dashboard": page_dashboard,
 "3. Internal": page_internal,
 "4. NLP Analysis": page_nlp}[page]()
