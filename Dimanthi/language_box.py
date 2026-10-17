"""
Translation for the Hospital card and the Homesick (mental health) card (OSHCwise) - Dimi's part

The guide pages are NOT rewritten. This file:

  1. tr()      - translates text written by Python (the page title, the caption, the Back button)
  2. inject()  - adds a translation layer (lang_layer.js) to the guide's HTML. It translates what the
                 guide shows into the student's language, using translations.json, and can make the
                 student walk to a step (the step is found by intent_model.py, see ask_box.py).
                 Things that must stay in English stay in English: the English sentence in
                 "What to say" (you say it to staff) and the signs inside the pictures.

NLP steps used here:
  - Sentence splitting: each sentence is translated on its own (never split after "e.g.")
  - Templates: "Step 3 of 7: Reception" -> "පියවර 3 / 7: <Reception in Sinhala>"
  - Right-to-left: Farsi pages read right to left; numbers, $ amounts, phone numbers and English
    names stay left to right (Unicode isolates), phone numbers never break over two lines
  - Fallback: a sentence that has no translation stays in English (never a wrong guess)
"""

import json
import re
from pathlib import Path

import streamlit as st

import language_model as lm

ROOT = Path(__file__).parent
TRANSLATIONS_FILE = ROOT / "translations.json"
LAYER_FILE = ROOT / "lang_layer.js"

LRI, PDI = "⁦", "⁩"            # Unicode "left-to-right isolate" (keeps $30 the right way round in Farsi)

# ---------- Translations ----------

@st.cache_data
def _load(modified_time: float) -> dict:
    return json.loads(TRANSLATIONS_FILE.read_text(encoding="utf-8"))


def load_translations() -> dict:
    if not TRANSLATIONS_FILE.exists():
        return {"templates": {}, "sentences": {}}
    return _load(TRANSLATIONS_FILE.stat().st_mtime)


def current_language() -> str:
    lang = st.session_state.get("lang", "en")
    return lang if lang in lm.LANGS else "en"


NO_SPLIT_AFTER = ("e.g.", "eg.", "i.e.", "etc.", "p.", "No.")


def split_sentences(text: str) -> list:
    """Split after . ! ? when a new sentence starts (a capital letter, a quote or a bracket).
    Never after 'e.g.' and similar. The same rule is used in lang_layer.js."""
    parts, start = [], 0
    for m in re.finditer(r"[.!?]\s+(?=[A-Z“‘(])", text):
        piece = text[start:m.end()].strip()
        if piece.split()[-1].lstrip("(“‘") in NO_SPLIT_AFTER:   # a short form, not the end of a sentence
            continue
        parts.append(piece)
        start = m.end()
    if text[start:].strip():
        parts.append(text[start:].strip())
    return parts


def _template_regex(template: str):
    pattern = re.escape(template)
    pattern = pattern.replace(r"\{n\}", r"(?P<n>\d+)").replace(r"\{t\}", r"(?P<t>\d+)").replace(r"\{x\}", r"(?P<x>.+)")
    return re.compile("^" + pattern + "$", re.S)


def _isolate(text: str) -> str:
    """Farsi: keep numbers, prices and English names left to right inside the right-to-left text."""
    return re.sub(r"([$+]?[0-9A-Za-z][0-9A-Za-z'’&./:%,\- ]*[0-9A-Za-z.%]|[$+]?[0-9A-Za-z]%?)",
                  lambda m: LRI + _keep_together(m.group(1)) + PDI, text)


def _keep_together(run: str) -> str:
    """Phone numbers like 1800 887 283 never break over two lines (non-breaking spaces)."""
    return run.replace(" ", "\u00a0") if re.fullmatch(r"[$+]?\d[\d ]*\d", run) else run


def translate(text: str, lang: str, data: dict = None, missing: set = None) -> str:
    """Translate one piece of text. Unknown sentences stay in English (and are added to `missing`)."""
    if lang == "en" or not text or not re.search(r"[A-Za-z]", text):
        return text
    data = data or load_translations()
    lead, core, trail = re.match(r"^(\s*)(.*?)(\s*)$", text, re.S).groups()
    core = " ".join(core.split())          # HTML line breaks and double spaces -> one space

    def one(piece: str) -> str:
        found = data["sentences"].get(piece)
        if found and found.get(lang):
            return found[lang]
        for template, by_lang in data["templates"].items():
            m = _template_regex(template).match(piece)
            if m and by_lang.get(lang):
                values = m.groupdict()
                if values.get("x") is not None:
                    values["x"] = translate(values["x"], lang, data, missing)
                return by_lang[lang].format(**values)
        return None

    whole = one(core)
    if whole is None:
        # Sentence by sentence. Two or more sentences that were translated together are used together.
        sentences, pieces, i = split_sentences(core), [], 0
        while i < len(sentences):
            for j in range(len(sentences), i, -1):
                done = one(" ".join(sentences[i:j]))
                if done is not None:
                    break
            if done is None:
                j = i + 1
                if missing is not None:
                    missing.add(sentences[i])
                done = sentences[i]
            pieces.append(done)
            i = j
        whole = " ".join(pieces)
    if lang in lm.RTL:
        whole = _isolate(whole)
    return lead + whole + trail


def tr(text: str) -> str:
    """Translate a Python string into the student's current language."""
    return translate(text, current_language())


# ---------- The translation layer for the guide HTML ----------

def inject(html: str, lang: str = None, goto: int = None) -> str:
    """Add the translation layer to a guide's HTML (just before </body>).
    goto = a step number: the student walks there (found by the meaning model, see ask_box.py)."""
    lang = lang or current_language()
    if (lang == "en" and goto is None) or not LAYER_FILE.exists():
        return html
    data = load_translations()
    # Only the target language, to keep the page small
    if lang == "en":
        data = {"templates": {}, "sentences": {}}
    small = {
        "lang": lang,
        "goto": goto,
        "rtl": lang in lm.RTL,
        "templates": {k: v[lang] for k, v in data["templates"].items() if v.get(lang)},
        "sentences": {k: v[lang] for k, v in data["sentences"].items() if v.get(lang)},
    }
    script = LAYER_FILE.read_text(encoding="utf-8").replace(
        "__LANG_DATA__", json.dumps(small, ensure_ascii=False).replace("</", "<\\/"))
    tag = f"<script>\n{script}\n</script>\n"
    if "</body>" in html:
        return html.replace("</body>", tag + "</body>", 1)
    return html + tag
