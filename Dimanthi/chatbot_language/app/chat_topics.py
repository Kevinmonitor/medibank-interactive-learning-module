"""
Question understanding in 5 languages for the OSHC chatbot (ML + NLP) - Dimi's part

The chatbot searches English policy documents. A question like
"mta kiyanna medical certificate gnne kohenda" (Sinhala in English letters, with typos)
does not match English words, so this model works out WHAT the student is asking about,
in any of the 5 languages, without needing internet or an AI key.

  Data      data/chat_topic_data.json - student questions for 11 topics in English, Sinhala,
            Farsi, Vietnamese and Bahasa Indonesia (script and English letters, with and
            without accents)
  NLP       the same text cleaning as the language model + accents removed, so
            "bảo hiểm" and "bao hiem" look the same
  Features  TF-IDF of letter groups (2-5 letters, handles typos like "gnne" for "ganne")
            joined with TF-IDF of words and word pairs
  Model     Logistic Regression (class_weight="balanced") -> a probability for every topic
  Testing   5-fold cross-validation, a confusion matrix and a separate hand-written test set
            (data/chat_topic_test.json, never used for training): python -m app.chat_topics

Each topic has one clear English question. That English question is what the chatbot
searches with, so the student gets the same checked answer as an English speaker.
"""

import hashlib
import json
import unicodedata
import warnings
from pathlib import Path

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, make_pipeline

from app.chat_language import clean as clean_language

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "chat_topic_data.json"
MODEL_FILE = ROOT / "data" / "chat_topic_model.joblib"

# topic -> (English question used for the search, the chatbot's approved-answer topic)
TOPICS = {
    "dental":    ("Is the dentist covered?", "Benefit exclusions"),
    "doctor":    ("Why did the doctor charge me?", "Medical cover"),
    "waiting":   ("Do I have to wait?", "Waiting periods"),
    "claim":     ("How do I claim?", "Making a claim"),
    "ambulance": ("Is an ambulance covered?", "Ambulance services"),
    "mental":    ("Can I see a psychologist?", "Mental health support"),
    "activate":  ("How do I activate my cover?", "Activating your cover"),
    "medicine":  ("Are prescription medicines covered?", "Prescription medicines"),
    "balance":   ("How much do I have left?", None),
    "hello":     (None, None),            # hello / thank you -> a friendly reply
}
TOPIC_NAMES = {"dental": "Dental, glasses, physio", "doctor": "Doctor / GP visits", "waiting": "Waiting periods",
               "claim": "Making a claim", "ambulance": "Ambulance", "mental": "Mental health",
               "activate": "Activating cover", "medicine": "Medicines", "balance": "My balance",
               "hello": "Hello / thanks"}
MIN_CONFIDENCE = 0.40


def clean(text: str) -> str:
    """Language-model cleaning + no accents (Vietnamese typed with or without accents)."""
    text = clean_language(text)
    out = "".join(ch for ch in unicodedata.normalize("NFD", text)
                  if not (unicodedata.category(ch) == "Mn" and ord(ch) < 0x0370))
    return unicodedata.normalize("NFC", out).replace("đ", "d")


def load_data():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    texts, labels = [], []
    for topic, by_lang in data.items():
        for sentences in by_lang.values():
            texts += sentences
            labels += [topic] * len(sentences)
    return texts, labels


def make_model():
    features = FeatureUnion([
        ("letters", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, preprocessor=clean)),
        ("words", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, preprocessor=clean,
                                  token_pattern=r"(?u)\b\w+\b")),
    ])
    return make_pipeline(features, LogisticRegression(C=15, max_iter=4000, class_weight="balanced"))


def _version() -> str:
    raw = DATA_FILE.read_bytes() + str(Path(__file__).stat().st_size).encode() + sklearn.__version__.encode()
    return hashlib.md5(raw).hexdigest()[:12]


_MODEL = {}


def get_model():
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
    texts, labels = load_data()
    _MODEL.update(version=version, model=make_model().fit(texts, labels))
    try:
        joblib.dump(dict(_MODEL), MODEL_FILE)
    except OSError:
        pass
    return _MODEL["model"]


def understand(text: str):
    """(topic or None, confidence, [(topic, probability), ...top 3])"""
    if len(clean(text).replace(" ", "")) < 2:
        return None, 0.0, []
    model = get_model()
    probs = model.predict_proba([text])[0]
    ranked = sorted(zip(model.classes_, map(float, probs)), key=lambda p: -p[1])[:3]
    topic, p = ranked[0]
    return (str(topic) if p >= MIN_CONFIDENCE else None), p, [(str(t), q) for t, q in ranked]


if __name__ == "__main__":
    texts, labels = load_data()
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    guess = cross_val_predict(make_model(), texts, labels, cv=folds)
    names = list(TOPICS)
    print("===== Chatbot question understanding model =====")
    print(f"Training questions: {len(texts)} in 5 languages, {len(names)} topics")
    print(f"5-fold cross-validation accuracy: {accuracy_score(labels, guess):.1%}\n")
    print("Confusion matrix (rows = true topic):")
    print(" " * 10 + " ".join(f"{n[:5]:>5}" for n in names))
    for n, row in zip(names, confusion_matrix(labels, guess, labels=names)):
        print(f"{n:>10}" + " ".join(f"{v:>5}" for v in row))
    test = json.loads((ROOT / "data" / "chat_topic_test.json").read_text(encoding="utf-8"))
    t_texts = [q for qs in test.values() for q in qs]
    t_labels = [t for t, qs in test.items() for _ in qs]
    t_guess = [understand(q)[0] or "not sure" for q in t_texts]
    print(f"\nSeparate hand-written test set ({len(t_texts)} new questions, 5 languages): "
          f"{accuracy_score(t_labels, t_guess):.1%}")
    for q, e, g in zip(t_texts, t_labels, t_guess):
        if e != g:
            print(f"   wrong: {q!r} expected {e}, model says {g}")
    print("\nNew questions (never seen in training):")
    for q in ["mta kiyanna medical certificate gnne kohenda", "dath ridenawa dosthara cover da",
              "مراجعه به روانشناس هزینه داره؟", "toi muon lay lai tien kham benh", "obat di apotek ditanggung?",
              "hi", "mmmm", "how do i make a claim for my physio"]:
        topic, p, _ = understand(q)
        print(f"  {q!r:50} -> {TOPIC_NAMES.get(topic, 'not sure')} ({p:.0%})")
