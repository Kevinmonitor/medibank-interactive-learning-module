"""
Other languages for the voice and typing box (OSHCwise).

Two small jobs:
  1. LANGUAGES: the languages in the menu above the microphone. The browser needs the language
     BEFORE it starts listening (it cannot guess), so for voice the student picks it.
  2. to_english(): the model in concern_classifier.py only knows English sentences, so a
     sentence in another language is translated into English first.
     - Typed text: the language is found automatically with `py3langid` (runs on this computer).
     - Translation: `deep-translator` (an online translation service). If it is not installed or
       there is no internet, the app says so and keeps working in English.

Install:  py -m pip install py3langid deep-translator
"""

# Menu label -> language code used by the browser's speech recognition (Chrome / Edge).
LANGUAGES = {
    "English": "en-AU",
    "සිංහල (Sinhala)": "si-LK",
    "فارسی (Persian)": "fa-IR",
    "Tiếng Việt (Vietnamese)": "vi-VN",
    "Bahasa Indonesia": "id-ID",
}

# Browser code -> code used by the translator and by langdetect.
_TRANSLATOR_CODE = {"en": "en", "si": "si", "fa": "fa", "vi": "vi", "id": "id"}
_DETECT_TO_TRANSLATOR = {"zh": "zh-CN"}


def is_english(lang_code: str) -> bool:
    return (lang_code or "en").lower().startswith("en")


def detect_language(text: str) -> str:
    """Language of typed text, e.g. 'fa', 'en'. If the answer is not one of the languages in the
    menu (or it cannot tell), it returns 'en': very short text is hard to detect, so English is
    the safe default."""
    try:
        import py3langid
        code, _score = py3langid.classify(text)
    except Exception:
        return "en"
    code = _DETECT_TO_TRANSLATOR.get(code, code)
    return code if code in _TRANSLATOR_CODE.values() else "en"


# Names for the second translation service (MyMemory), used only if Google Translate fails.
_NAMES = {"si": "sinhala", "fa": "persian", "vi": "vietnamese", "id": "indonesian"}


def to_english(text: str, lang_code: str):
    """Translate `text` into English.
    Returns (english_text, error). `error` is None when it worked, otherwise a short message
    for the student (with the technical reason in brackets) and `english_text` is the original.
    The technical reason is also printed in the Terminal, to help the team find the problem."""
    if is_english(lang_code) or not text.strip():
        return text, None
    base = lang_code.split("-")[0].lower()
    source = _TRANSLATOR_CODE.get(base, base)
    try:
        from deep_translator import GoogleTranslator, MyMemoryTranslator
    except ImportError:
        return text, "Translation is not installed (run: py -m pip install deep-translator)."

    reasons = []
    # 1st try: Google Translate. 2nd try: MyMemory (a different service) if the first one fails.
    for name, make in (
        ("Google", lambda: GoogleTranslator(source=source, target="en")),
        ("MyMemory", lambda: MyMemoryTranslator(source=_NAMES.get(source, source), target="english")),
    ):
        try:
            english = make().translate(text)
            if english and english.strip():
                return english, None
            reasons.append(f"{name}: empty answer")
        except Exception as error:                         # no internet, blocked, too many requests...
            reasons.append(f"{name}: {type(error).__name__}")
            print(f"[language_support] {name} translation failed: {type(error).__name__}: {error}")
    return text, "I couldn't translate that (" + "; ".join(reasons) + ")."
