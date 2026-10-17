"""
Translation quality check (OSHC Compass) - Dimi's part

Checks translations.json, so a wrong number or a missing translation is found
BEFORE a student sees it. For every English sentence and every language it checks:

  1. Missing      - is there a translation for every language?
  2. Numbers      - every number, $ amount, % and phone number in the English
                    must be in the translation too (e.g. "$300", "1800 887 283", "000")
  3. Names        - names that must not change (OSHC, Medibank, GP, PBS ...) are still there
  4. Placeholders - templates keep {n}, {t} and {x}
  5. Script       - the translation is really in that language's letters
                    (Sinhala letters for si, Persian letters for fa)
  6. Model check  - the language detection model agrees which language it is

Run:   python translation_check.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
TRANSLATIONS_FILE = ROOT / "translations.json"
LANGS = ["si", "fa", "vi", "id"]

# Names that must stay the same in every language
KEEP_WORDS = ["OSHC", "Medibank", "Medicare", "MBS", "PBS", "Healthdirect", "Lifeline", "000",
              "1800 887 283", "134 148", "13 11 14"]

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def numbers_in(text: str) -> list:
    """'$1,000 per member / 12 months' -> ['1000', '12']"""
    text = text.translate(PERSIAN_DIGITS)
    found = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    return [n.replace(",", "") for n in found]


def script_ok(lang: str, text: str) -> bool:
    letters = re.sub(r"[^\w]|[\d_]", "", text)
    if not letters:
        return True
    if lang == "si":
        return bool(re.search(r"[඀-෿]", text)) or len(letters) < 6
    if lang == "fa":
        return bool(re.search(r"[؀-ۿ]", text)) or len(letters) < 6
    return True


def check(model_check: bool = True) -> dict:
    data = json.loads(TRANSLATIONS_FILE.read_text(encoding="utf-8"))
    problems = {"missing": [], "numbers": [], "names": [], "placeholders": [], "script": [], "model": []}

    detect = None
    if model_check:
        try:
            import language_model as lm
            detect = lm.detect_language
        except Exception as error:          # scikit-learn not installed: skip this part
            print(f"(model check skipped: {error})")

    for part in ("sentences", "templates"):
        for english, by_lang in data[part].items():
            english_numbers = sorted(numbers_in(english))
            for lang in LANGS:
                text = by_lang.get(lang, "")
                if not text.strip():
                    problems["missing"].append((lang, english))
                    continue
                if sorted(numbers_in(text)) != english_numbers and not set(numbers_in(english)) <= set(numbers_in(text)):
                    problems["numbers"].append((lang, english, text))
                for word in KEEP_WORDS:
                    if word in english and word not in text:
                        problems["names"].append((lang, word, english, text))
                for holder in re.findall(r"\{[ntx]\}", english):
                    if holder not in text:
                        problems["placeholders"].append((lang, holder, english))
                if not script_ok(lang, text):
                    problems["script"].append((lang, english, text))
                # Long translations only: short ones are mostly names ("Medibank", "GP")
                if detect and part == "sentences" and len(text) > 40 and text != english:
                    found, confidence, _ = detect(text)
                    if found != lang:
                        problems["model"].append((lang, found, f"{confidence:.0%}", text))
    return {"total": len(data["sentences"]) + len(data["templates"]), **problems}


if __name__ == "__main__":
    result = check()
    print(f"Checked {result['total']} English texts x {len(LANGS)} languages\n")
    titles = {
        "missing": "Missing translations",
        "numbers": "Numbers / $ / phone numbers not the same",
        "names": "Names that must not change",
        "placeholders": "Template placeholders lost",
        "script": "Not in the right letters",
        "model": "Language model thinks it is another language (please read again)",
    }
    for key, title in titles.items():
        items = result[key]
        print(f"{'OK ' if not items else '!! '} {title}: {len(items)}")
        for item in items[:10]:
            print("     ", " | ".join(str(x) for x in item))
        if len(items) > 10:
            print(f"      ... and {len(items) - 10} more")
