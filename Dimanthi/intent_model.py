"""
Meaning model (OSHCwise) - Dimi's part

The student types what they need, in their own language, on the Hospital card or the
Homesick (mental health) card. This model understands WHAT they mean and tells the card
where to walk:

    "I want to do a blood test"        -> Hospital card, step 6 "Tests"
    "mata blood test ekak karanna one" -> Hospital card, step 6 "Tests"   (Sinhala in English letters)
    "toi nho nha qua"                  -> Homesick card, suggestion 1      (Vietnamese without accents)
    "mata hembirissawa"  (a cold)      -> not an emergency: the "I get sick" card (see a GP)
    "papuwa ridenawa"    (chest pain)  -> SAFETY: call 000 now

Data Science steps, all in this file:
  1. Data      - intent_data.json: about 1,800 short sentences students might type, in English,
                 Sinhala (+ English letters), Farsi (+ Finglish), Vietnamese (+ no accents) and
                 Bahasa Indonesia (+ chat style). Each sentence has a tag (H5 = hospital tests, ...).
                 A separate TEST set of 280 new sentences is never used for training.
  2. NLP       - text cleaning: lower case, Unicode NFC, Farsi half-space, Vietnamese accents
                 removed (so "xét nghiệm" = "xet nghiem"), punctuation removed, numbers kept
  3. Features  - two kinds of TF-IDF joined together (FeatureUnion):
                   * letter groups (2-5 letters inside words): works for every script and for typos
                   * words and word pairs: "blood test", "go home", "miss family"
  4. Model     - Logistic Regression (class_weight="balanced"), one model per card.
                 The same tags become different answers on each card (an interpreter is the
                 "Doctor" step in hospital, but "Help in your language" on the Homesick card).
  5. Testing   - 5-fold cross-validation + the separate test set + a confusion matrix
  6. Safety    - a word list in all 5 languages is checked FIRST (emergency, self-harm).
                 Safety never depends on a model guess.
  7. Saving    - trained models are saved in models/intent_models.joblib (joblib)

Privacy: nothing the student types is saved.

Run the tests:   python intent_model.py
Needs:           pip install scikit-learn
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
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import FeatureUnion, make_pipeline

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "intent_data.json"
MODEL_FILE = ROOT / "models" / "intent_models.joblib"

MIN_CONFIDENCE = 0.30      # below this the card asks "Did you mean ...?" instead of walking

# ---------- The two cards: tag -> answer ----------
# "step:N" = walk to step N of this card.  "card:X" = this belongs to another card.  "other" = not about health.

HOSPITAL_STEPS = ["Entrance", "Triage nurse", "Reception", "Waiting area", "Doctor", "Tests", "Going home"]
HOMESICK_STEPS = ["Normal", "Talk", "Language", "Counselling", "GP plan", "Connect"]

CARD_MAP = {
    "hospital": {
        **{f"H{i}": f"step:{i}" for i in range(7)},
        "INTERP": "step:4", "NURSE": "step:1", "M2": "step:4",
        "M0": "card:homesick", "M1": "card:homesick", "M3": "card:homesick", "M4": "card:homesick",
        "M5": "card:homesick",
        "SICK": "card:sick", "MED": "card:medication", "CLAIM": "card:claim", "OTHER": "other",
    },
    "homesick": {
        **{f"M{i}": f"step:{i}" for i in range(6)},
        "INTERP": "step:2", "NURSE": "step:1",
        **{f"H{i}": "card:hospital" for i in range(7)},
        "SICK": "card:sick", "MED": "card:medication", "CLAIM": "card:claim", "OTHER": "other",
    },
}
STEP_NAMES = {"hospital": HOSPITAL_STEPS, "homesick": HOMESICK_STEPS}


# ---------- Safety words (checked BEFORE the model, all 5 languages) ----------

EMERGENCY_WORDS = [
    # English
    "chest pain", "can't breathe", "cannot breathe", "can not breathe", "difficulty breathing", "not breathing",
    "unconscious", "bleeding heavily", "heavy bleeding", "a lot of blood", "overdose", "stroke", "heart attack",
    "seizure", "fainted", "passed out",
    # Sinhala (script and English letters)
    "හුස්ම ගන්න බැහැ", "හුස්ම ගන්න අමාරුයි", "පපුවේ වේදනාව", "පපුව රිදෙනවා", "සිහිය නැති", "ලේ ගොඩක් යනවා",
    "husma ganna bae", "husma ganna amarui", "papuwa ridenawa", "sihiya nathi", "le godak yanawa",
    # Farsi (script and Finglish)
    "نمی‌توانم نفس بکشم", "نمیتوانم نفس بکشم", "نمی‌تونم نفس بکشم", "تنگی نفس", "درد قفسه سینه", "سکته", "بیهوش",
    "خونریزی شدید", "nafas nemikesham", "nemitoonam nafas bekesham", "dard sine", "bihoosh",
    # Vietnamese (with and without accents)
    "khó thở", "không thở được", "đau ngực", "bất tỉnh", "chảy máu nhiều", "đột quỵ", "đau tim",
    # Indonesian
    "sesak napas", "tidak bisa bernapas", "gak bisa napas", "nyeri dada", "sakit dada", "pingsan",
    "pendarahan hebat", "serangan jantung", "kejang",
]
SELF_HARM_WORDS = [
    "suicide", "kill myself", "harm myself", "hurt myself", "want to die", "end my life", "don't want to live",
    "සියදිවි", "මැරෙන්න ඕනේ", "මට මැරෙන්න", "marenna one", "maraganna one",
    "خودکشی", "می‌خواهم بمیرم", "میخواهم بمیرم", "میخوام بمیرم", "khodkoshi", "mikham bemiram",
    "tự tử", "muốn chết", "tự làm hại",
    "bunuh diri", "ingin mati", "mau mati", "pengen mati",
]


# ---------- 2. NLP text cleaning ----------

def _no_marks(text: str) -> str:
    """Remove accents from Latin letters only (Vietnamese 'xét nghiệm' -> 'xet nghiem').
    Sinhala and Farsi vowel signs are kept."""
    out = []
    for ch in unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D")):
        if unicodedata.category(ch) == "Mn" and out and out[-1].isascii():
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def clean(text: str) -> str:
    """Lower case, Unicode NFC, Farsi half-space -> space, Latin accents removed, no punctuation."""
    text = unicodedata.normalize("NFC", text or "").lower()
    text = text.replace("\u200c", " ").replace("\u2066", "").replace("\u2069", "").replace("’", "'")
    text = _no_marks(text)
    # Keep letters, numbers and vowel signs of every script (Sinhala ් ා ි ...), remove punctuation
    text = "".join(ch if unicodedata.category(ch)[0] in "LMN" or ch in "' \u200d" else " " for ch in text)
    return " ".join(text.split())


def _plain_for_safety(text: str) -> set:
    """Several cleaned versions, so 'I cant breathe' and 'khó thở' / 'kho tho' all match."""
    base = unicodedata.normalize("NFC", text or "").lower().replace("’", "'")
    zwnj = "‌"
    versions = {base, base.replace(zwnj, ""), base.replace(zwnj, " "), clean(base)}
    versions |= {v.replace("'", "") for v in versions}
    return {" ".join(v.split()) for v in versions}


def safety_flag(text: str) -> str:
    """'self_harm', 'emergency' or '' (nothing found)."""
    versions = _plain_for_safety(text)

    def hit(words):
        keys = {k for w in words for k in (clean(w), w.lower(), w.lower().replace("'", ""), clean(w).replace("'", ""))}
        return any(k in v for k in keys for v in versions)

    if hit(SELF_HARM_WORDS):
        return "self_harm"
    if hit(EMERGENCY_WORDS):
        return "emergency"
    return ""


# ---------- 1. Data ----------

def load_data() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def card_data(card: str, part: str = "train"):
    """(texts, answers, languages) for one card."""
    data, mapping = load_data()[part], CARD_MAP[card]
    texts, labels, langs = [], [], []
    for tag, by_lang in data.items():
        for lang, sentences in by_lang.items():
            for sentence in sentences:
                texts.append(sentence)
                labels.append(mapping[tag])
                langs.append(lang)
    return texts, labels, langs


# ---------- 3 and 4. Features and model ----------

def _make_model():
    features = FeatureUnion([
        ("letters", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True,
                                    preprocessor=clean, min_df=1)),
        ("words", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True,
                                  preprocessor=clean, token_pattern=r"(?u)\b\w+\b")),
    ])
    return make_pipeline(features, LogisticRegression(C=12, max_iter=5000, class_weight="balanced"))


# ---------- 7. Saving and loading ----------

def _version() -> str:
    raw = DATA_FILE.read_bytes() + str(Path(__file__).stat().st_size).encode() + sklearn.__version__.encode()
    return hashlib.md5(raw).hexdigest()[:12]


_MODELS = {}


def get_models() -> dict:
    """Load the saved models, or train and save them (only when the data or scikit-learn changed)."""
    if _MODELS:
        return _MODELS
    version = _version()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            saved = joblib.load(MODEL_FILE)
        if saved.get("version") == version:
            _MODELS.update(saved)
            return _MODELS
    except Exception:
        pass
    _MODELS["version"] = version
    for card in CARD_MAP:
        texts, labels, _ = card_data(card)
        _MODELS[card] = _make_model().fit(texts, labels)
    try:
        MODEL_FILE.parent.mkdir(exist_ok=True)
        joblib.dump(dict(_MODELS), MODEL_FILE)
    except OSError:
        pass
    return _MODELS


# ---------- Use ----------

def understand(text: str, card: str, top: int = 3) -> dict:
    """What does the student mean on this card?

    Returns {"safety": "", "answer": "step:5", "confidence": 0.88, "ranked": [(answer, p), ...],
             "cleaned": "..."}.  answer is None when the model is not sure enough."""
    cleaned = clean(text)
    result = {"safety": safety_flag(text), "cleaned": cleaned, "answer": None, "confidence": 0.0, "ranked": []}
    if len(re.sub(r"[\W\d_]", "", cleaned)) < 2:
        return result
    model = get_models()[card]
    probs = model.predict_proba([text])[0]
    ranked = sorted(zip(model.classes_, map(float, probs)), key=lambda p: -p[1])[:top]
    result["ranked"] = [(str(a), p) for a, p in ranked]
    best, confidence = result["ranked"][0]
    result["confidence"] = confidence
    if confidence >= MIN_CONFIDENCE:
        result["answer"] = best
    return result


def answer_name(answer: str, card: str) -> str:
    """'step:5' -> 'Tests'. 'card:sick' -> 'sick'."""
    kind, _, value = answer.partition(":")
    return STEP_NAMES[card][int(value)] if kind == "step" else value


# ---------- 5. Testing ----------

def evaluate(card: str) -> dict:
    texts, labels, _ = card_data(card)
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_guess = cross_val_predict(_make_model(), texts, labels, cv=folds)
    model = get_models()[card]
    t_texts, t_labels, t_langs = card_data(card, "test")
    t_guess = list(model.predict(t_texts))
    per_lang = {}
    for lang in ["en", "si", "fa", "vi", "id"]:
        idx = [i for i, l in enumerate(t_langs) if l == lang]
        per_lang[lang] = sum(t_guess[i] == t_labels[i] for i in idx) / max(1, len(idx))
    classes = sorted(set(labels))
    return {
        "examples": len(texts), "classes": classes,
        "cv_accuracy": accuracy_score(labels, cv_guess),
        "test_accuracy": accuracy_score(t_labels, t_guess), "test_total": len(t_texts),
        "per_language": per_lang,
        "confusion": confusion_matrix(t_labels, t_guess, labels=classes),
        "mistakes": [(t, e, g) for t, e, g in zip(t_texts, t_labels, t_guess) if e != g],
    }


SAFETY_TEST = [
    ("I have chest pain", "emergency"), ("papuwa ridenawa", "emergency"), ("I cant breathe", "emergency"),
    ("khó thở quá", "emergency"), ("kho tho", "emergency"), ("نمی‌تونم نفس بکشم", "emergency"),
    ("saya sesak napas", "emergency"), ("I want to die", "self_harm"), ("muốn chết", "self_harm"),
    ("aku pengen mati", "self_harm"), ("mata marenna one", "self_harm"),
    ("I have a cold", ""), ("I want a blood test", ""), ("mata hembirissawa", ""), ("I miss home", ""),
]


if __name__ == "__main__":
    for card in CARD_MAP:
        r = evaluate(card)
        print(f"\n===== {card.upper()} card =====")
        print(f"Training sentences: {r['examples']}   answers: {', '.join(r['classes'])}")
        print(f"5-fold cross-validation accuracy: {r['cv_accuracy']:.1%}")
        print(f"Separate test set ({r['test_total']} new sentences): {r['test_accuracy']:.1%}")
        print("By language: " + ", ".join(f"{l} {a:.0%}" for l, a in r["per_language"].items()))
        print("Confusion matrix (test set, rows = true, columns = model):")
        short = [c.replace("step:", "s").replace("card:", "")[:6] for c in r["classes"]]
        print("        " + " ".join(f"{s:>6}" for s in short))
        for s, row in zip(short, r["confusion"]):
            print(f"{s:>7} " + " ".join(f"{v:>6}" for v in row))
        for text, expected, guess in r["mistakes"][:12]:
            print(f"   wrong: {text!r}  expected {expected}, model says {guess}")
    ok = sum(safety_flag(t) == e for t, e in SAFETY_TEST)
    print(f"\nSafety word check: {ok} of {len(SAFETY_TEST)} right")
    print("\nExamples:")
    for text, card in [("I want to do a blood test", "hospital"), ("mata blood test ekak karanna one", "hospital"),
                       ("mata hembirissawa", "hospital"), ("toi nho nha qua", "homesick"),
                       ("saya mau pulang hari ini", "hospital"), ("delam baraye khanevadam tang shode", "homesick")]:
        u = understand(text, card)
        print(f"  [{card}] {text!r}: {u['answer']} ({u['confidence']:.0%})  safety='{u['safety']}'")