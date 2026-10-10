"""Admin analytics dashboard (administrators only).

Shows how many times the model suggested each practice card. Only counts are
saved (see analytics.py): no sentences, no voice, no names, no times.
"""

import altair as alt
import pandas as pd
import streamlit as st

import analytics
import auth

st.set_page_config(page_title="Admin analytics dashboard", layout="wide")
auth.require_login(admin_only=True)

# Made-up numbers, only so the dashboard can be shown before there is real use
DEMO_COUNTS = {
    "I feel homesickness": 42, "I need to go to hospital": 31, "I get sick": 27,
    "I need medication": 18, "I need to find a health provider": 36,
    "Comprehensive OSHC coverage": 14, "I need to make a claim": 22,
    "Nothing, just here to learn": 9,
}

DEMO_QUIZ = {
    "pays_all": (9, 31), "gp_rate": (28, 12), "glasses": (14, 26), "claim_now": (12, 28), "rx_free": (17, 23),
    "psych_hosp": (22, 18), "cosmetic": (25, 15), "ivf": (11, 19), "counselling": (20, 10), "ambulance": (30, 8),
}

top_left, top_right = st.columns([5, 1])
with top_left:
    st.markdown("### Admin analytics dashboard")
    st.caption(
        "How often the model suggested each practice. Only these counts are saved: "
        "no sentences, no voice, no names and no times."
    )
with top_right:
    if st.button("← Back to practices"):
        st.switch_page("pages/1_Question.py")
    if st.button("Log out"):
        auth.logout()

real = analytics.read_counts()
real_total = sum(real.values())

use_demo = st.checkbox("Show demo data (made-up numbers)", value=(real_total == 0))
counts = DEMO_COUNTS if use_demo else real
total = sum(counts.values())

if use_demo:
    st.warning("Demo data: these numbers are made up, not real students.")
elif total == 0:
    st.info("No suggestions counted yet. Use the microphone or the typing box on the question page, then come back.")

data = pd.DataFrame({"Card": list(counts), "Times suggested": list(counts.values())})
data = data.sort_values("Times suggested", ascending=False).reset_index(drop=True)

m1, m2, m3 = st.columns(3)
m1.metric("Suggestions counted", total)
m2.metric("Most suggested", data.iloc[0]["Card"] if total else "-")
m3.metric("Cards never suggested", int((data["Times suggested"] == 0).sum()))

if total:
    chart = (
        alt.Chart(data)
        .mark_bar(color="#143a5a", cornerRadiusEnd=4)
        .encode(
            x=alt.X("Times suggested:Q", title="Times suggested"),
            y=alt.Y("Card:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
            tooltip=["Card", "Times suggested"],
        )
        .properties(height=34 * len(data) + 40)
    )
    st.altair_chart(chart, use_container_width=True)
    data["Share"] = (data["Times suggested"] / total).map("{:.0%}".format)
    st.dataframe(data, hide_index=True, use_container_width=True)

st.caption(
    "A suggestion is counted when the model picks a card for a spoken or typed sentence. "
    "Cards chosen by clicking, and sentences the app did not understand, are not counted."
)

with st.expander("Reset the real counts"):
    st.write("This deletes the saved counts (it cannot be undone).")
    if st.button("Delete real counts"):
        analytics.clear_counts()
        st.rerun()

# ---------- Learning quiz ("Nothing, just here to learn") ----------
st.divider()
st.markdown("### Learning quiz: which myths do students believe?")
st.caption("Only counts are saved: right and wrong answers for each question. No names and no times.")

quiz_real = analytics.read_quiz()
quiz_real_total = sum(c["right"] + c["wrong"] for c in quiz_real.values())
quiz_demo = st.checkbox("Show demo quiz data (made-up numbers)", value=(quiz_real_total == 0), key="quiz_demo")
quiz = ({q: {"right": DEMO_QUIZ[q][0], "wrong": DEMO_QUIZ[q][1]} for q in analytics.QUIZ_QUESTIONS}
        if quiz_demo else quiz_real)

rows = []
for q, label in analytics.QUIZ_QUESTIONS.items():
    right, wrong = quiz[q]["right"], quiz[q]["wrong"]
    answers = right + wrong
    rows.append({"Statement": label, "Answers": answers, "Right": right, "Wrong": wrong,
                 "Correct %": round(100 * right / answers) if answers else None})
quiz_df = pd.DataFrame(rows)
answered = quiz_df[quiz_df["Answers"] > 0]

if quiz_demo:
    st.warning("Demo data: these numbers are made up, not real students.")
elif answered.empty:
    st.info("No quiz answers yet. Open the card 'Nothing, just here to learn' and answer a question.")

if not answered.empty:
    all_right, all_answers = int(quiz_df["Right"].sum()), int(quiz_df["Answers"].sum())
    hardest = answered.sort_values("Correct %").iloc[0]
    q1, q2, q3 = st.columns(3)
    q1.metric("Quiz answers counted", all_answers)
    q2.metric("Answers that were right", f"{round(100 * all_right / all_answers)}%")
    q3.metric("Lowest score on one statement", f"{int(hardest['Correct %'])}% right")
    st.caption(f"Hardest statement: “{hardest['Statement']}”")

    quiz_chart = (
        alt.Chart(answered)
        .mark_bar(color="#C8322E", cornerRadiusEnd=4)
        .encode(
            x=alt.X("Correct %:Q", title="Answered correctly (%)", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("Statement:N", sort="x", title=None, axis=alt.Axis(labelLimit=420)),
            tooltip=["Statement", "Answers", "Correct %"],
        )
        .properties(height=34 * len(answered) + 40)
    )
    st.altair_chart(quiz_chart, use_container_width=True)
    st.dataframe(answered.sort_values("Correct %").reset_index(drop=True), hide_index=True, use_container_width=True)
    st.caption("The lower the bar, the more students get it wrong. These are the topics worth explaining better.")

with st.expander("Reset the real quiz counts"):
    st.write("This deletes the saved quiz counts (it cannot be undone).")
    if st.button("Delete real quiz counts"):
        analytics.clear_quiz()
        st.rerun()
