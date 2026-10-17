"""
Translation for the OSHC chatbot - Dimi's part

Two jobs, using the same Groq AI model the chatbot already uses (GROQ_API_KEY):
  1. Student question -> English, so the search finds the right part of the policy documents.
     Works for romanised Sinhala ("dath dosthara cover wenawada") and Farsi in English letters.
  2. The checked English answer -> the student's language.

Checks after translating the answer (a wrong number in health insurance is dangerous):
  - every number, $ amount and phone number must be the same as in the English answer
    (Persian digits ۱۸۰۰ are read as 1800)
  - names like OSHC, Medibank and Medicare must not change
  If a check fails it tries once more. If it fails again, the student gets the English answer
  with a short note in their own language - never a wrong translation.

Without a GROQ_API_KEY nothing is sent anywhere: the question is searched as it was typed and
the English answer is shown with the note. Translations are kept in memory only (never saved).
"""

import re
from functools import lru_cache

from app.chat_language import ENGLISH_NAMES

KEEP_NAMES = ["OSHC", "Medibank", "Medicare", "Lifeline", "Healthdirect"]
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def numbers_in(text: str) -> list:
    """'$1,000 a year, call 1800 887 283' -> ['1000', '1800', '283', '887'] (sorted)"""
    text = (text or "").translate(PERSIAN_DIGITS)
    return sorted(n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text))


def translation_ok(english: str, translated: str) -> bool:
    if not translated or not translated.strip():
        return False
    if numbers_in(english) != numbers_in(translated):
        return False
    return all(name in translated for name in KEEP_NAMES if name in english)


def available() -> bool:
    try:
        from app.generate import _secret
        return bool(_secret("GROQ_API_KEY"))
    except Exception:
        return False


def _ask_model(prompt: str, temperature: float = 0.1) -> str:
    from openai import OpenAI
    from app.generate import _secret
    client = OpenAI(api_key=_secret("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
    resp = client.chat.completions.create(
        model=_secret("MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature, max_tokens=900,
    )
    text = (resp.choices[0].message.content or "").strip()
    return text.strip('"“”')


@lru_cache(maxsize=256)
def to_english(question: str, lang: str) -> str:
    """Returns the English question, or the original question if translation is not possible."""
    if lang == "en" or not available():
        return question
    prompt = (
        "A university student in Australia asked a question about their health insurance (OSHC). "
        f"It is written in {ENGLISH_NAMES.get(lang, lang)}. It may be typed in English letters "
        "(romanised Sinhala, or Farsi written in English letters 'Finglish'), or Vietnamese without accents, "
        "and may mix in English words.\n"
        "Translate it into simple English. Keep every number exactly. Do not answer it. "
        "Output only the English question.\n\n"
        f"Question: {question}"
    )
    try:
        english = _ask_model(prompt, 0.0)
    except Exception:
        return question
    if not english or len(english) > 4 * len(question) + 80 or numbers_in(english) != numbers_in(question):
        return question
    return english


@lru_cache(maxsize=256)
def from_english(answer: str, lang: str):
    """Returns (translated answer, True) or (English answer, False) when it could not be checked."""
    if lang == "en" or not available():
        return answer, lang == "en"
    prompt = (
        f"Translate this health insurance answer for an international student into {ENGLISH_NAMES[lang]}.\n"
        "Rules:\n"
        "- Use simple everyday words, short sentences, the same meaning. Do not add anything.\n"
        "- Copy every number, $ amount and phone number exactly as written, with Western digits 0-9 "
        "(for example $1,000 and 1800 887 283).\n"
        "- Keep these names in English letters: OSHC, Medibank, Medicare, Lifeline, Healthdirect.\n"
        + ("- Use standard Persian (Farsi) script.\n" if lang == "fa" else "")
        + ("- Use Sinhala script.\n" if lang == "si" else "")
        + "Output only the translation.\n\n"
        f"Answer:\n{answer}"
    )
    for temperature in (0.1, 0.0):
        try:
            translated = _ask_model(prompt, temperature)
        except Exception:
            break
        if translation_ok(answer, translated):
            return translated, True
    return answer, False


if __name__ == "__main__":
    english = "Yes. Emergency ambulance is fully covered. Call 1800 887 283. The limit is $1,000."
    print(translation_ok(english, "ඔව්. හදිසි ගිලන් රථය ආවරණය වේ. 1800 887 283 අමතන්න. සීමාව $1,000."))   # True
    print(translation_ok(english, "ඔව්. 1800 887 283 අමතන්න. සීමාව $100."))                              # False
    print(translation_ok(english, "بله. با ۱۸۰۰ ۸۸۷ ۲۸۳ تماس بگیرید. سقف $1,000 است."))                    # True
    print("AI translation available:", available())
