"""
Language detection for the OSHC chatbot (ML + NLP) - Dimi's part

Finds which language a student is writing in, so the chatbot can answer in that language:
English, Sinhala, Farsi, Vietnamese or Bahasa Indonesia. It also understands the ways students
really type: Sinhala in English letters ("mata dath ridenawa"), Farsi in English letters
("dandanpezeshki cover mishe") and Vietnamese without accents ("nha si co duoc bao hiem khong").

Data Science steps, all in this file:
  1. Data      - data/chat_language_data.json: about 3,400 short student sentences in the
                 5 languages (train) and 281 different sentences (test, never used for training)
  2. NLP       - text cleaning: lower case, Unicode NFC, the Farsi half-space, hidden direction
                 marks removed, punctuation removed (letters and vowel signs of every script kept)
  3. Features  - TF-IDF on small groups of letters (1 to 4 letters inside words).
                 Letter groups work for every script, for typos and for very short messages.
  4. Model     - Logistic Regression: gives a probability for each language
  5. Testing   - 5-fold cross-validation, the separate test set and a confusion matrix
  6. Saving    - the trained model is saved in data/chat_language_model.joblib and trained
                 again by itself when the data or the scikit-learn version changes

Nothing the student types is saved by this file.

Run the tests:   python -m app.chat_language        (from the chatbot folder)
"""

import hashlib
import json
import re
import unicodedata
import warnings
from pathlib import Path

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]          # the chatbot folder
DATA_FILE = ROOT / "data" / "chat_language_data.json"
MODEL_FILE = ROOT / "data" / "chat_language_model.joblib"

LANGS = ["en", "si", "fa", "vi", "id"]
LANG_NAMES = {"en": "English", "si": "සිංහල (Sinhala)", "fa": "فارسی (Farsi)",
              "vi": "Tiếng Việt (Vietnamese)", "id": "Bahasa Indonesia"}
ENGLISH_NAMES = {"en": "English", "si": "Sinhala", "fa": "Farsi (Persian)",
                 "vi": "Vietnamese", "id": "Bahasa Indonesia"}
RTL = {"fa"}
MIN_CONFIDENCE = 0.55          # below this the chatbot keeps the language it already had


# ---------- 2. NLP text cleaning ----------

def clean(text: str) -> str:
    """Lower case, Unicode NFC, Farsi half-space -> space, no punctuation.
    Letters, numbers and vowel signs of every script are kept (Sinhala ් ා ි, Farsi, Vietnamese)."""
    text = unicodedata.normalize("NFC", text or "").lower()
    text = text.replace("‌", " ").replace("⁦", "").replace("⁩", "").replace("’", "'")
    text = "".join(ch if unicodedata.category(ch)[0] in "LMN" or ch in "' ‍" else " " for ch in text)
    return " ".join(text.split())


# ---------- 1. Data ----------

def load_data(part: str = "train"):
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))[part]
    texts, labels = [], []
    for lang in LANGS:
        for sentence in data.get(lang, []):
            texts.append(sentence)
            labels.append(lang)
    return texts, labels


# ---------- 3 and 4. Features and model ----------

def make_model():
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 4), sublinear_tf=True, preprocessor=clean),
        LogisticRegression(C=20, max_iter=4000),
    )


# ---------- 6. Saving and loading ----------

def _version() -> str:
    raw = DATA_FILE.read_bytes() + str(Path(__file__).stat().st_size).encode() + sklearn.__version__.encode()
    return hashlib.md5(raw).hexdigest()[:12]


_MODEL = {}


def get_model():
    """Load the saved model, or train and save it (only when something changed)."""
    if "model" in _MODEL:
        return _MODEL["model"]
    version = _version()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            saved = joblib.load(MODEL_FILE)
        if saved.get("version") == version:
            _MODEL.update(saved)
            return _MODEL["model"]
    except Exception:
        pass
    texts, labels = load_data("train")
    _MODEL.update(version=version, model=make_model().fit(texts, labels))
    try:
        joblib.dump(dict(_MODEL), MODEL_FILE)
    except OSError:
        pass                                   # still works, it just trains again next time
    return _MODEL["model"]


# ---------- Use ----------

def detect(text: str):
    """(language code, confidence 0-1, [(code, probability), ...]). Code is None for very short text."""
    if len(re.sub(r"[\W\d_]", "", text or "")) < 2:
        return None, 0.0, []
    model = get_model()
    probs = model.predict_proba([text])[0]
    ranked = sorted(zip(model.classes_, map(float, probs)), key=lambda p: -p[1])
    return str(ranked[0][0]), ranked[0][1], [(str(c), p) for c, p in ranked]


# ---------- 5. Testing ----------

def evaluate() -> dict:
    texts, labels = load_data("train")
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv = cross_val_predict(make_model(), texts, labels, cv=folds)
    t_texts, t_labels = load_data("test")
    guess = list(get_model().predict(t_texts))
    return {
        "examples": len(texts), "cv_accuracy": accuracy_score(labels, cv),
        "test_total": len(t_texts), "test_accuracy": accuracy_score(t_labels, guess),
        "report": classification_report(t_labels, guess, labels=LANGS, zero_division=0),
        "confusion": confusion_matrix(t_labels, guess, labels=LANGS),
        "mistakes": [(t, e, g) for t, e, g in zip(t_texts, t_labels, guess) if e != g],
    }


if __name__ == "__main__":
    r = evaluate()
    print("===== Chatbot language detection model =====")
    print(f"Training sentences: {r['examples']}")
    print(f"5-fold cross-validation accuracy: {r['cv_accuracy']:.1%}")
    print(f"Separate test set ({r['test_total']} new sentences): {r['test_accuracy']:.1%}")
    print(r["report"])
    print("Confusion matrix (test set, rows = true language, columns = model):")
    print("      " + " ".join(f"{l:>5}" for l in LANGS))
    for l, row in zip(LANGS, r["confusion"]):
        print(f"{l:>5} " + " ".join(f"{v:>5}" for v in row))
    for text, e, g in r["mistakes"][:10]:
        print(f"   wrong: {text!r}  expected {e}, model says {g}")
    print("\nExamples:")
    for text in ["is the dentist covered", "dath dosthara cover wenawada", "دندانپزشکی پوشش داده می‌شود",
                 "nha si co duoc bao hiem khong", "apakah dokter gigi ditanggung"]:
        lang, p, _ = detect(text)
        print(f"  {text!r}: {ENGLISH_NAMES[lang]} ({p:.0%} sure)")
