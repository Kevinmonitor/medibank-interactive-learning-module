"""
Language detection model (OSHC Compass) - Dimi's part

A machine-learning model (scikit-learn) that finds which language a student wrote in:
English, Sinhala, Farsi, Vietnamese or Bahasa Indonesia.
It also works for Sinhala typed in English letters ("mata una"), Farsi typed in
English letters ("komak lazem daram") and Vietnamese typed without accents ("toi can giup do").
language_box.py uses it on the Hospital card and the Homesick (mental health) card: the student
types a few words and the card changes to that language.

Data Science steps, all in this file:
  1. Data      - every sentence of the Hospital and Homesick cards in all 5 languages
                 (translations.json), plus everyday sentences a student might type (EXTRA_LANG and
                 CARD_SENTENCES below)
  2. NLP       - text cleaning: lower case, Unicode normalising (NFC), the Farsi half-space,
                 the left-to-right marks removed
  3. Features  - TF-IDF on small groups of letters (character n-grams, 1 to 4 letters).
                 Letter groups work for every script: Sinhala, Farsi and Latin letters.
  4. Model     - Logistic Regression: learns which letter groups belong to which language
                 and says how sure it is (a probability)
  5. Testing   - 5-fold cross-validation, a confusion matrix, and new test sentences
                 the model never saw
  6. Saving    - the trained model is saved in models/ (joblib) and loaded next time.
                 It is trained again only when the data changes.

Privacy: nothing the student types is saved. Only the model file is saved.

Run the tests:   python language_model.py
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
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).parent
TRANSLATIONS_FILE = ROOT / "translations.json"
MODEL_DIR = ROOT / "models"
MODEL_FILE = MODEL_DIR / "language_model.joblib"

LANGS = ["en", "si", "fa", "vi", "id"]
LANG_NAMES = {"en": "English", "si": "සිංහල (Sinhala)", "fa": "فارسی (Farsi)",
              "vi": "Tiếng Việt (Vietnamese)", "id": "Bahasa Indonesia"}
RTL = {"fa"}

LANG_MIN_CONFIDENCE = 0.55     # below this we keep the language the student already had


# ---------- 1. Data ----------

# Extra everyday sentences, so the language model does not only learn hospital words.
# "si" includes Sinhala typed in English letters (very common in chat).
# "vi" includes Vietnamese typed without accents. "fa" includes "Finglish".
EXTRA_LANG = {
    "en": [
        "hello how are you", "I need help", "where is the hospital", "my head hurts",
        "I feel sick", "can you help me please", "I don't understand", "thank you very much",
        "how much does it cost", "I lost my card", "my friend is sick", "where do I go",
        "I have a fever", "is this covered by my insurance", "what should I do", "I am a student",
        "I miss my family", "can I speak to a nurse", "I need a doctor now", "when can I go home",
        "I broke my leg", "how long do I wait", "please call my friend", "what does this mean",
    ],
    "si": [
        "ආයුබෝවන්", "මට උදව් ඕනේ", "රෝහල කොහෙද", "මගේ ඔළුව රිදෙනවා", "මට අසනීපයි",
        "කරුණාකර මට උදව් කරන්න", "මට තේරෙන්නේ නැහැ", "බොහොම ස්තූතියි", "මේකට කීයද",
        "මගේ කාඩ්පත නැති වුණා", "මගේ යාළුවා අසනීපයි", "මම කොහෙද යන්න ඕනේ", "මට උණ තියෙනවා",
        "මම ශිෂ්‍යයෙක්", "මට දොස්තර කෙනෙක් ඕනේ", "මට ගෙදර යන්න ඕනේ", "මගේ කකුල කැඩුණා",
        # Sinhala in English letters
        "mata una", "mata asaneepai", "mage oluwa ridenawa", "mata udaw one", "rohala koheda",
        "mata therenne naha", "bohoma sthuthi", "mage kakula ridenawa", "mata dosthara kenek one",
        "mama koheda yanna one", "mage yaluwa asaneepai", "mata bada ridenawa", "kaadpatha nathi wuna",
        "mata gedara yanna one", "kochchara wela inna one", "meka kiyada", "mata kassa thiyenawa",
        "ammata kiyanna", "mama shishyayek", "mata beheth one", "mata hari amaru",
    ],
    "fa": [
        "سلام حال شما چطور است", "کمک لازم دارم", "بیمارستان کجاست", "سرم درد می‌کند", "حالم خوب نیست",
        "لطفاً کمکم کنید", "متوجه نمی‌شوم", "خیلی ممنون", "قیمتش چقدر است", "کارتم را گم کردم",
        "دوستم مریض است", "کجا باید بروم", "تب دارم", "من دانشجو هستم", "دکتر لازم دارم",
        "می‌خواهم به خانه بروم", "پایم شکسته", "چقدر باید صبر کنم", "این یعنی چه",
        # Farsi in English letters (Finglish)
        "salam khoobi", "komak lazem daram", "bimarestan kojast", "saram dard mikone", "halam khoob nist",
        "motevajeh nemisham", "kheili mamnoon", "doktor lazem daram", "tab daram", "dastam dard mikone",
    ],
    "vi": [
        "xin chào bạn khỏe không", "tôi cần giúp đỡ", "bệnh viện ở đâu", "tôi bị đau đầu", "tôi thấy mệt",
        "làm ơn giúp tôi", "tôi không hiểu", "cảm ơn rất nhiều", "cái này bao nhiêu tiền", "tôi bị mất thẻ",
        "bạn tôi bị ốm", "tôi phải đi đâu", "tôi bị sốt", "tôi là sinh viên", "tôi cần bác sĩ",
        "tôi muốn về nhà", "tôi bị gãy chân", "phải chờ bao lâu", "cái này nghĩa là gì",
        # Vietnamese without accents
        "xin chao", "toi can giup do", "benh vien o dau", "toi bi dau dau", "toi bi sot",
        "toi khong hieu", "cam on nhieu", "toi bi dau tay", "toi can bac si", "toi muon ve nha",
    ],
    "id": [
        "halo apa kabar", "saya butuh bantuan", "rumah sakit di mana", "kepala saya sakit", "saya merasa sakit",
        "tolong bantu saya", "saya tidak mengerti", "terima kasih banyak", "berapa harganya", "kartu saya hilang",
        "teman saya sakit", "saya harus ke mana", "saya demam", "saya mahasiswa", "saya butuh dokter",
        "saya mau pulang", "kaki saya patah", "berapa lama menunggu", "ini artinya apa", "saya sakit perut",
        "tolong panggil teman saya", "apakah ini ditanggung asuransi", "saya kehilangan obat", "dokternya di mana",
    ],
}

# Sentences about the two cards (hospital and missing home), in all 5 languages,
# so the model also knows the words students use for these worries.
CARD_SENTENCES = {
    "en": ["I miss my family", "I feel lonely here", "I want to go home", "I need to go to the emergency department",
           "where is the hospital emergency", "I feel sad and alone", "can I talk to a counsellor", "I hurt my leg"],
    "si": ["මට මගේ පවුල මතක් වෙනවා", "මට මෙහෙ තනිකමක් දැනෙනවා", "මට ගෙදර යන්න ඕනේ", "මට හදිසි ප්‍රතිකාර අංශයට යන්න ඕනේ",
           "mata gedara mathak wenawa", "mata thanikamak danenawa", "mage pawula mathak wenawa", "mata hospital yanna one"],
    "fa": ["دلم برای خانواده‌ام تنگ شده", "اینجا احساس تنهایی می‌کنم", "می‌خواهم به خانه برگردم", "باید به اورژانس بروم",
           "delam baraye khanevadam tang shode", "ehsase tanhayi mikonam", "bayad beram orjans", "mikham ba moshaver harf bezanam"],
    "vi": ["tôi nhớ gia đình", "tôi thấy cô đơn ở đây", "tôi muốn về nhà", "tôi cần đến phòng cấp cứu",
           "toi nho gia dinh", "toi thay co don", "toi can di benh vien", "toi muon noi chuyen voi ai do"],
    "id": ["saya rindu keluarga", "saya merasa kesepian di sini", "saya ingin pulang", "saya harus ke IGD",
           "saya kangen rumah", "saya sedih dan sendirian", "bisakah saya bicara dengan konselor", "kaki saya terluka"],
}
for _lang, _sentences in CARD_SENTENCES.items():
    EXTRA_LANG[_lang] = EXTRA_LANG[_lang] + _sentences


# New sentences used ONLY for testing (not in the training data)
LANG_TEST = [
    ("my stomach hurts a lot", "en"), ("where can I find a nurse", "en"), ("I need to see someone now", "en"),
    ("is the ambulance free", "en"), ("can you speak slowly please", "en"), ("I have a cough", "en"),
    ("ok", "en"), ("help me", "en"),
    ("මගේ බඩ රිදෙනවා", "si"), ("හෙදිය කොහෙද", "si"), ("මට කැස්ස තියෙනවා", "si"), ("කරුණාකර හෙමින් කතා කරන්න", "si"),
    ("mage bada godak ridenawa", "si"), ("hediya koheda", "si"), ("mata hemin kiyanna", "si"), ("mata kassa", "si"),
    ("شکمم خیلی درد می‌کند", "fa"), ("پرستار کجاست", "fa"), ("سرفه دارم", "fa"), ("لطفاً آرام صحبت کنید", "fa"),
    ("shekamam dard mikone", "fa"), ("parastar kojast", "fa"),
    ("bụng tôi đau quá", "vi"), ("y tá ở đâu", "vi"), ("tôi bị ho", "vi"), ("làm ơn nói chậm lại", "vi"),
    ("bung toi dau qua", "vi"), ("y ta o dau", "vi"), ("toi bi ho", "vi"),
    ("perut saya sakit sekali", "id"), ("perawat di mana", "id"), ("saya batuk", "id"),
    ("tolong bicara pelan-pelan", "id"), ("apakah ambulans gratis", "id"), ("saya perlu bertemu seseorang", "id"),
    ("di mana toiletnya", "id"), ("saya pusing", "id"),
]


# ---------- 2. NLP text cleaning ----------

def _plain(text: str) -> str:
    """Lower case, straight quotes, single spaces, Unicode tidied. Keeps every script."""
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("\u2066", "").replace("\u2069", "")      # left-to-right marks (Farsi pages)
    text = text.replace("’", "'").replace("\u200c", " ")         # Farsi half-space -> space
    return " ".join(text.lower().split())


def _sentences(text: str) -> list:
    """Split a paragraph into shorter pieces (more, shorter training examples)."""
    parts = re.split(r"(?<=[.!?؟।])\s+|[;:]\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 2]


def language_data():
    """(texts, labels): every card sentence in all 5 languages + the everyday sentences."""
    data = json.loads(TRANSLATIONS_FILE.read_text(encoding="utf-8"))
    texts, labels = [], []

    def add(lang, text):
        text = re.sub(r"\{\w+\}", " ", text)
        for piece in _sentences(text):
            # Skip pieces that are only names / numbers (e.g. "Medibank", "134 148")
            if len(re.sub(r"[\W\d_]", "", piece)) >= 3:
                texts.append(piece)
                labels.append(lang)

    for english, by_lang in list(data["sentences"].items()) + list(data["templates"].items()):
        add("en", english)
        for lang, text in by_lang.items():
            if text != english:            # a brand name copied unchanged is not Sinhala/Farsi/...
                add(lang, text)
    for lang, sentences in EXTRA_LANG.items():
        for text in sentences:
            texts.append(text)
            labels.append(lang)
    return texts, labels


# ---------- 3 and 4. Features and model ----------

def _make_language_model():
    # char_wb = letter groups inside each word (with the word edges), 1 to 4 letters long
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 4), sublinear_tf=True, preprocessor=_plain),
        LogisticRegression(C=20, max_iter=4000),
    )


# ---------- 6. Saving and loading the trained model ----------

def _data_hash() -> str:
    """Changes when the training data or the scikit-learn version changes, so the model is trained again.
    (A model saved with one scikit-learn version can break in another version.)"""
    raw = json.dumps([language_data(), Path(__file__).stat().st_size, sklearn.__version__], ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


_MODEL = {}


def get_model():
    """Load the saved model, or train and save it (only when the data changed)."""
    if _MODEL:
        return _MODEL["language"]
    version = _data_hash()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")        # an old saved model is simply trained again below
            saved = joblib.load(MODEL_FILE)
        if saved.get("version") == version:
            _MODEL.update(saved)
            return _MODEL["language"]
    except Exception:
        pass
    texts, labels = language_data()
    _MODEL.update(version=version, language=_make_language_model().fit(texts, labels))
    try:
        MODEL_DIR.mkdir(exist_ok=True)
        joblib.dump(dict(_MODEL), MODEL_FILE)
    except OSError:
        pass                                   # still works, just trains again next time
    return _MODEL["language"]


# ---------- Use ----------

def detect_language(text: str):
    """(language code, confidence 0-1, {code: probability}). Code is None if the text is too short."""
    if len(re.sub(r"[\W\d_]", "", text or "")) < 2:
        return None, 0.0, {}
    model = get_model()
    probs = model.predict_proba([text])[0]
    ranked = dict(sorted(zip(model.classes_, map(float, probs)), key=lambda p: -p[1]))
    best = next(iter(ranked))
    return str(best), ranked[best], ranked


# ---------- 5. Testing ----------

def evaluate() -> dict:
    """5-fold cross-validation (always tested on sentences the model did not learn from),
    a confusion matrix, and the new test sentences."""
    texts, labels = language_data()
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    guesses = cross_val_predict(_make_language_model(), texts, labels, cv=folds)
    model = get_model()
    test_guesses = [model.predict([t])[0] for t, _ in LANG_TEST]
    mistakes = [(t, e, g) for (t, e), g in zip(LANG_TEST, test_guesses) if g != e]
    return {
        "examples": len(texts),
        "per_language": {l: labels.count(l) for l in LANGS},
        "cv_accuracy": accuracy_score(labels, guesses),
        "confusion": confusion_matrix(labels, guesses, labels=LANGS),
        "report": classification_report(labels, guesses, labels=LANGS, zero_division=0),
        "test_right": len(LANG_TEST) - len(mistakes), "test_total": len(LANG_TEST), "mistakes": mistakes,
    }


if __name__ == "__main__":
    r = evaluate()
    print("===== Language detection model =====")
    print(f"Training examples: {r['examples']}  {r['per_language']}")
    print(f"5-fold cross-validation accuracy: {r['cv_accuracy']:.1%}")
    print(r["report"])
    print("Confusion matrix (rows = true language, columns = model):")
    print("      " + " ".join(f"{l:>6}" for l in LANGS))
    for l, row in zip(LANGS, r["confusion"]):
        print(f"{l:>6}" + " ".join(f"{v:>6}" for v in row))
    print(f"\nNew test sentences: {r['test_right']} of {r['test_total']} right")
    for text, expected, guess in r["mistakes"]:
        print(f"   wrong: {text!r}  expected {expected}, model says {guess}")
    print("\nExamples:")
    for text in ["mata una", "how do I make a claim", "tôi cần giúp đỡ", "toi can giup do",
                 "مترجم می‌خواهم", "komak lazem daram", "saya butuh dokter"]:
        lang, conf, _ = detect_language(text)
        print(f"  {text!r}: {LANG_NAMES[lang]} ({conf:.0%} sure)")
