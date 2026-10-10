"""
Voice section for the Question page (OSHC Compass).

The student taps the microphone and says what they are worried about. The words
are matched to one of the 8 cards by a small machine-learning model
(see concern_classifier.py). They can also type instead of speaking.

Use it in pages/1_Question.py:
    from voice_section import render_voice_section
    render_voice_section(PAGES)
"""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import analytics
import concern_classifier as model

# The microphone button is a small web page. Its code is kept right here, and the folder
# "voice_input" is created automatically, so there is nothing to copy by hand.
COMPONENT_DIR = Path(__file__).parent / "voice_input"
COMPONENT_HTML = r'''<!DOCTYPE html>
<!--
  Microphone row for Streamlit (a tiny custom component).
  Left: the instruction text. Right (in front of it): the microphone button.
  The browser turns speech into text (Chrome or Edge), then sends the text back to Python.
-->
<html><head><meta charset="utf-8">
<style>
  body { margin:0; font-family:"Lucida Sans","Lucida Sans Unicode",Arial,sans-serif; color:#143a5a; }
  .row { display:grid; grid-template-columns:auto 1fr; column-gap:28px; align-items:center; padding:4px 0; }
  #status { font-weight:700; font-size:16px; line-height:1.35; }
  .right { display:flex; flex-direction:column; align-items:flex-start; }
  #mic { width:64px; height:64px; border-radius:50%; border:0; cursor:pointer; background:#C8322E; color:#fff;
         font-size:28px; box-shadow:0 4px 14px rgba(200,50,46,.3); transition:transform .2s; }
  #mic:hover { transform:scale(1.06); }
  #mic:disabled { background:#b8bcc2; cursor:not-allowed; box-shadow:none; }
  #mic.on { animation:pulse 1.2s infinite; background:#A82824; }
  @keyframes pulse { 0% { box-shadow:0 0 0 0 rgba(200,50,46,.5); } 100% { box-shadow:0 0 0 22px rgba(200,50,46,0); } }
  #heard { min-height:0; margin-top:4px; font-size:14px; color:#273b42; font-style:italic; }
  #note  { font-size:12px; color:#5E6B7A; }
</style></head>
<body>
  <div class="row">
    <div id="status">Tap the microphone and tell me what you are worried about</div>
    <div class="right">
      <button id="mic" aria-label="Tap and speak">🎤</button>
      <div id="heard"></div>
      <div id="note"></div>
    </div>
  </div>
<script>
// --- Talking to Streamlit (the component protocol) ---
const send = (type, data) => window.parent.postMessage({ isStreamlitMessage: true, type, ...data }, "*");
send("streamlit:componentReady", { apiVersion: 1 });
const resize = () => send("streamlit:setFrameHeight", { height: document.body.scrollHeight + 4 });
window.addEventListener("load", resize);
resize();

let lang = "en-AU";
window.addEventListener("message", e => {
  if (e.data && e.data.type === "streamlit:render" && e.data.args && e.data.args.lang) lang = e.data.args.lang;
});

// --- Speech recognition (built into Chrome and Edge) ---
const $ = id => document.getElementById(id);
const IDLE = "Tap the microphone and tell me what you are worried about";
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null, listening = false;

if (!SR) {
  $("status").textContent = "Voice needs Chrome or Edge. You can type below instead.";
  $("mic").disabled = true;
}

function stop() { listening = false; $("mic").classList.remove("on"); }

$("mic").onclick = () => {
  if (listening && rec) { rec.stop(); return; }
  rec = new SR();
  rec.lang = lang;
  rec.interimResults = true;
  rec.maxAlternatives = 3;
  let finalText = "", alternatives = [];

  rec.onstart = () => {
    listening = true;  $("mic").classList.add("on");
    $("status").textContent = "Listening… speak now";  $("heard").textContent = "";  $("note").textContent = "";
  };
  rec.onresult = ev => {
    let text = "";
    for (let i = 0; i < ev.results.length; i++) text += ev.results[i][0].transcript;
    finalText = text;  $("heard").textContent = "“" + text + "”";  resize();
    // Chrome's other guesses (2nd and 3rd best), so Python can pick the one that fits best
    alternatives = [];
    for (let k = 1; k < 3; k++) {
      let guess = "";
      for (let i = 0; i < ev.results.length; i++) guess += (ev.results[i][k] || ev.results[i][0]).transcript;
      guess = guess.trim();
      if (guess && guess !== text.trim() && !alternatives.includes(guess)) alternatives.push(guess);
    }
  };
  rec.onerror = ev => {
    stop();
    const msg = { "not-allowed": "The microphone is blocked. Allow it in the address bar, or type below.",
                  "no-speech": "I didn't hear anything. Try again.",
                  "network": "Voice needs an internet connection." }[ev.error] || ("Voice problem: " + ev.error);
    $("status").textContent = IDLE;  $("note").textContent = msg;  resize();
  };
  rec.onend = () => {
    stop();
    if (finalText.trim()) {
      $("status").textContent = "Got it! Finding the best practice for you…";
      send("streamlit:setComponentValue", { value: { text: finalText.trim(), alts: alternatives, id: Date.now() }, dataType: "json" });
    } else if (!$("note").textContent) {
      $("status").textContent = IDLE;
    }
  };
  rec.start();
};
</script></body></html>
'''

COMPONENT_DIR.mkdir(exist_ok=True)
_page = COMPONENT_DIR / "index.html"
if not _page.exists() or _page.read_text(encoding="utf-8") != COMPONENT_HTML:
    _page.write_text(COMPONENT_HTML, encoding="utf-8")

_voice = components.declare_component("voice_input", path=str(COMPONENT_DIR))

EMERGENCY_TEXT = (
    "**If this is an emergency, call 000 now.** "
    "Don't wait for the app."
)
SELF_HARM_TEXT = (
    "**You are not alone, and help is available right now.** "
    "Please call **000** or **Lifeline on 13 11 14**. "
    "You can also call the Student Health and Support Line (24/7) on **1800 887 283**."
)


def _best_guess(guesses: list) -> str:
    """Chrome sometimes writes the wrong word (feel -> failed). Of its guesses, use the one the model
    understands best. If any guess sounds like an emergency or self-harm, use that one: safety first."""
    first, best_text, best_score = guesses[0], guesses[0], -1.0
    for guess in guesses:
        if model.safety_flag(guess):
            return guess
        if not model.understood(guess):
            continue
        label, score = model.predict(guess, top=1)[0]
        if label != model.OTHER and score > best_score:
            best_text, best_score = guess, score
    return best_text if best_score >= 0 else first


def _show_result(text: str, pages: dict, where: str, alternatives=()) -> None:
    """Show what the model understood and offer the matching practice."""
    original = text
    text = _best_guess([text, *alternatives])
    st.markdown(f"**I heard:** “{text}”")
    if text != original:
        st.caption(f"Chrome first wrote “{original}”. This other guess fits better.")
    flag = model.safety_flag(text)

    if flag == "self_harm":              # safety first: no cards, just help
        st.error(SELF_HARM_TEXT)
        return
    if flag == "emergency":              # no practice suggestion in an emergency: just the message
        st.error(EMERGENCY_TEXT)
        return

    matches = model.predict(text, top=4)
    other_p = next((p for label, p in matches if label == model.OTHER), 0.0)
    matches = [m for m in matches if m[0] != model.OTHER][:3]
    best, confidence = matches[0]

    if (not model.understood(text) or confidence < model.MIN_CONFIDENCE
            or other_p > confidence):
        st.info(
            "Sorry, I didn't quite get that. Try a short sentence, like "
            "“I miss my family”, “I have a sore throat”, or “How do I make a claim?”. "
            "Or choose a card below. "
            "If I can't help you, or you are in a hurry, you can also ask the chatbot."
        )
    else:
        st.success(f"Best match: **{best}**  ({confidence:.0%} sure)")
        # Count the card once per spoken or typed sentence (only the card name is saved)
        logged_key = (where, text, st.session_state.get("voice_last_id"))
        if st.session_state.get(f"counted_{where}") != logged_key:
            st.session_state[f"counted_{where}"] = logged_key
            analytics.log_card(best)
        if best in pages:
            if st.button(f"Open this practice →", key=f"open_practice_{where}", type="primary"):
                st.switch_page(pages[best])
        else:
            st.caption("This practice is coming soon. Other cards are below.")


# Shown under the typing box, before the cards. The app saves only a count per card
# (see analytics.py). If it ever saves more, the last sentences must change.
HOW_IT_WORKS = (
    "If you speak, your browser (Chrome or Edge) turns your voice into text, usually with Google's "
    "speech service. If you type, a small model inside this app compares your words with example "
    "sentences to suggest a practice. This app does not store your voice or your words. It only counts "
    "how often each practice is suggested, so the team can see which topics students need most."
)
CHOOSE_INSTEAD = "If you are not comfortable with this, you can just choose one of the options below."

DIVIDER = "<div style='border-top:1px solid #d7dbe1;margin:0.35rem 0'></div>"


def _label(text: str, bottom: str = "0") -> str:
    """A line of text in the same style as the heading line next to the microphone."""
    return (
        f"<div style='min-height:2.6rem;margin-bottom:{bottom};display:flex;align-items:center;"
        "font:700 16px \"Lucida Sans\",\"Lucida Sans Unicode\",Arial,sans-serif;color:#143a5a'>"
        f"{text}</div>"
    )


def render_voice_section(pages: dict) -> None:
    """Three lines: speak (microphone), type (box), or choose a card (shown below).
    The result appears right under the way the student used (voice or typing)."""
    _, middle, _ = st.columns([1, 5, 1])
    with middle:
        # Line 1: instruction, with the microphone right after it
        heard = _voice(lang="en-AU", key="voice", default=None)

        # Which one did the student use last, voice or typing?
        # (the typing box value is already known at the start of every run)
        typed_now = st.session_state.get("voice_typed", "").strip()
        if heard and heard.get("id") != st.session_state.get("voice_last_id"):
            st.session_state["voice_last_id"] = heard["id"]
            st.session_state["voice_text"] = heard["text"]
            st.session_state["voice_alts"] = heard.get("alts", [])
            st.session_state["voice_source"] = "voice"
        if typed_now != st.session_state.get("voice_last_typed", ""):
            st.session_state["voice_last_typed"] = typed_now
            if typed_now:
                st.session_state["voice_source"] = "typed"
        source = st.session_state.get("voice_source")

        # Result for voice: right under the microphone
        if source == "voice" and st.session_state.get("voice_text"):
            _show_result(st.session_state["voice_text"], pages, "voice",
                         st.session_state.get("voice_alts", []))
        st.markdown(DIVIDER, unsafe_allow_html=True)

        # Line 2: instruction, with the typing box right after it
        label, box, _ = st.columns([1.15, 2.4, 1.45])
        with label:
            st.markdown(_label("Or you can type it here"), unsafe_allow_html=True)
        with box:
            typed = st.text_input(
                "Type what you are worried about", key="voice_typed",
                placeholder="e.g. I miss my family", label_visibility="collapsed",
            )

        # Result for typing: right under the typing box
        if source == "typed" and typed.strip():
            _show_result(typed.strip(), pages, "typed")
        st.markdown(DIVIDER, unsafe_allow_html=True)

        # Line 3: how the voice and typing are handled, then the way out to the cards below
        st.markdown(
            "<div style='margin:0.3rem 0 0.2rem;font:400 14px/1.5 \"Lucida Sans\",\"Lucida Sans Unicode\",Arial,sans-serif;"
            f"color:#273b42'>{HOW_IT_WORKS}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(_label(CHOOSE_INSTEAD, "0.4rem"), unsafe_allow_html=True)
