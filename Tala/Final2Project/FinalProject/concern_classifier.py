"""
Concern classifier (OSHC Compass)

Turns what a student says ("I miss my family") into one of the 8 cards.

Data Science steps, all in this file:
  1. Data     - example sentences we wrote for each card (TRAINING_DATA)
  2. Features - TF-IDF turns each sentence into numbers (single words and word pairs)
  3. Model    - Logistic Regression learns which words belong to which card
  4. Testing  - 5-fold cross-validation gives an honest accuracy
  5. Use      - predict() returns the best matches with a confidence score

Needs:  py -m pip install scikit-learn
"""

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline


# ---------- 1. Data (the label is the card text on the Question page) ----------

OTHER = "Something else"

TRAINING_DATA = {
    "I feel homesickness": [
        "I miss my family so much", "I feel lonely and I miss home", "I am homesick",
        "I cry at night because I miss my country", "I don't have friends here and I feel alone",
        "I feel sad being so far from my parents", "everything feels strange and I want to go back home",
        "I miss my mum's cooking and my friends back home", "I feel isolated in Melbourne",
        "I can't sleep because I keep thinking about home", "nothing feels familiar here and I feel down",
        "I feel sad and alone", "I miss my country", "I feel like I don't belong here",
        "I miss the food from my country", "I miss my friends back home", "I want to go back to my family",
    ],
    "I need to go to hospital": [
        "I need to go to the hospital", "I think I should go to the emergency department",
        "I hurt my leg badly", "what happens when I go to hospital", "I had an accident and need an ambulance",
        "I am scared of going to emergency", "my friend needs to go to the hospital",
        "how does the emergency room work", "I broke my arm", "will I need to stay overnight in hospital",
        "I have a really high fever and feel very weak", "what do I do in an emergency",
        "I need an operation", "do I go to a public or a private hospital",
    ],
    "I get sick": [
        "I have a cold", "I have a fever and a sore throat", "I feel sick and I have a cough",
        "I have a stomach ache", "I think I have the flu", "I feel unwell and tired", "I have a headache",
        "I am throwing up", "I caught a cold", "my throat hurts", "I feel dizzy and have a runny nose",
        "I need to see a doctor because I am sick", "I have diarrhea", "I have been coughing for three days",
    ],
    "I need medication": [
        "I need medicine", "where can I buy tablets", "how do I get a prescription",
        "I need to go to the pharmacy", "my medication ran out", "do I need a prescription for painkillers",
        "how much do medicines cost in Australia", "I take pills every day and I need more",
        "can I get my medicine covered", "what is a pharmacy", "I need antibiotics", "I need paracetamol",
        "I lost my medicine", "how do I refill my prescription",
    ],
    "I need to find a health provider": [
        "I need to find a doctor near me", "how do I find a GP", "where is the nearest clinic",
        "I want to find a dentist or a specialist", "how do I search for a health provider",
        "which doctors accept my insurance", "I need to book an appointment with a doctor",
        "how do I find a direct billing clinic", "which hospitals are in the network",
        "I don't know where to go for a check-up", "find a clinic close to my university",
        "who can I see for my skin problem", "how to find an after hours doctor", "where can I see a doctor",
    ],
    "Comprehensive OSHC coverage": [
        "what does my insurance cover", "what is OSHC", "does my cover include dental",
        "what is covered under overseas student health cover", "do I have to pay anything myself",
        "what are waiting periods", "is pregnancy covered", "what are extras", "does my insurance cover an ambulance",
        "how much will I pay out of pocket", "what is not covered", "explain my health cover",
        "do I need insurance for my visa", "what is included in comprehensive cover",
    ],
    "I need to make a claim": [
        "how do I make a claim", "I paid for the doctor and I want my money back", "how do I submit a receipt",
        "how do I get a refund from my insurance", "I need to claim for my visit",
        "where do I upload my invoice", "how long does a claim take", "can I claim using the app",
        "I paid upfront and want to be reimbursed", "how to claim for physio", "I have a bill from the clinic",
        "submit a claim for my x-ray", "how do I get paid back", "claim my medical expenses",
    ],
    # Not about health or insurance. Includes "hard negatives": sentences that share words
    # with a real card (like "miss") but mean something else.
    OTHER: [
        "I miss pizza", "I miss the bus every morning", "I missed my train", "I miss playing video games",
        "I miss sleeping in on weekends", "I like football", "the weather is nice today",
        "what is the capital of France", "tell me a joke", "I am hungry", "I want to buy a laptop",
        "where can I eat pizza", "hello how are you", "my phone is broken", "I love music",
        "what time is it", "I need a new backpack", "how do I get to the library", "I am late for class",
        "my laptop is slow", "I want to learn to cook", "what is your name",
        # Worries that are NOT about health or insurance (jobs, visa, housing, study, money).
        # Several use "find" or "worried", which also appear in real cards.
        "I am worried about finding a job", "I need to find a part time job", "where can I find a cheap flat",
        "I am worried about finding a place to live", "I can't find my keys", "I am worried about my visa",
        "I am stressed about my exams", "I need help with my assignment", "I am worried about paying my rent",
        "how do I find a good tutor", "I am worried about my grades", "where can I find a cheap supermarket",
    ],
    "Nothing, just here to learn": [
        "I am just here to learn", "I am only looking around", "nothing in particular",
        "I just want to learn about the Australian health system", "I am curious how it works",
        "no worries, just exploring", "I want to understand how health care works here",
        "I am new and want to know the basics", "I don't have a problem right now", "just browsing",
        "I want to prepare in advance", "teach me about health care in Australia",
        "I am not sick, I just want to learn", "I just arrived and I am learning about the system",
    ],
}


# More training sentences that start the way students speak ("I am worried about ...").
# Words like "worried" and "I am" now appear in many cards, so they do not point to one card.
EXTRA = {
    "I feel homesickness": ["I am worried that I will always feel lonely here", "I am sad that I cannot hug my family",
                            "I feel homesickness", "homesickness", "homesick"],
    "I need to go to hospital": [
        "I need to go to hospital", "hospital", "go to hospital",
        "I am worried about going to the emergency room", "I am scared about being admitted to hospital",
        # small injuries
        "I cut my thumb with a knife and it will not stop bleeding",
        "I burned my hand on the stove",
        "I sprained my ankle playing sport",
        "I fell off my bike and hurt my knee",
        "what should I do if I cut my toe",
        "I hit my head and now I feel dizzy",
        "my wrist is swollen after a fall",
        "I got a deep cut on my arm",
    ],
    "I get sick": ["I get sick", "sickness", "I am sick", "I am worried because I have a fever and a cough", "I am not feeling well and my throat is sore"],
    "I need medication": ["I need medication", "medication", "medicine", "I am worried about paying for my tablets", "I am looking for a pharmacy to buy medicine"],
    "I need to find a health provider": ["I need to find a health provider", "health provider", "find a provider", "I am worried about booking a doctor appointment", "I am nervous about finding a clinic", "I do not know how to find a dentist here"],
    "Comprehensive OSHC coverage": ["Comprehensive OSHC coverage", "OSHC coverage", "I am worried that my cover does not include dental", "I am not sure what my insurance pays for"],
    "I need to make a claim": ["I need to make a claim", "make a claim", "claim", "I am worried about how to send my receipt", "I am waiting for my claim to be paid"],
    "Nothing, just here to learn": ["Nothing, just here to learn", "just here to learn", "I am a bit worried and I want to learn how it works", "I am new here and I am looking around"],
}
for _label, _sentences in EXTRA.items():
    TRAINING_DATA[_label] += _sentences


# Sentences used only for TESTING the card model (none is in the training data).
# We wrote them ourselves, so treat the score as a first sign.
CONCERN_TEST = [
    ("I failed homesickness", "I feel homesickness"),
    ("I keep thinking about my parents back home", "I feel homesickness"),
    ("I feel lonely far from my country", "I feel homesickness"),
    ("I want to go home and see my family", "I feel homesickness"),
    ("my friend broke his arm and needs the emergency room", "I need to go to hospital"),
    ("what happens after I arrive at the hospital", "I need to go to hospital"),
    ("I am nervous about staying overnight in hospital", "I need to go to hospital"),
    ("if I cut my finger what should I do", "I need to go to hospital"),
    ("I slipped and hurt my wrist", "I need to go to hospital"),
    ("I burned my arm while cooking", "I need to go to hospital"),
    ("I have had a high temperature since yesterday", "I get sick"),
    ("my stomach hurts and I feel weak", "I get sick"),
    ("I think I caught the flu", "I get sick"),
    ("where can I get my tablets", "I need medication"),
    ("do I need a prescription for antibiotics", "I need medication"),
    ("my medicine has run out", "I need medication"),
    ("I am worried about finding a doctor", "I need to find a health provider"),
    ("how can I search for a clinic near my university", "I need to find a health provider"),
    ("which GP takes my insurance", "I need to find a health provider"),
    ("does my health cover include dental", "Comprehensive OSHC coverage"),
    ("what is covered when I go to hospital", "Comprehensive OSHC coverage"),
    ("what will I have to pay myself", "Comprehensive OSHC coverage"),
    ("I paid the clinic and need the money back from insurance", "I need to make a claim"),
    ("how long until my claim is paid", "I need to make a claim"),
    ("can I send my receipt through the app", "I need to make a claim"),
    ("I just want to understand how things work here", "Nothing, just here to learn"),
    ("I am only exploring the site", "Nothing, just here to learn"),
    ("nothing is wrong, I am learning", "Nothing, just here to learn"),
    ("what is the best pizza in Melbourne", OTHER),
    ("I lost my bus card", OTHER),
    ("tell me about football", OTHER),
    ("I am worried about finding a flat near the university", OTHER),
    ("I am nervous about my final exam", OTHER),
    ("how do I find work on weekends", OTHER),
]

# Below this confidence we say "I'm not sure" instead of guessing
MIN_CONFIDENCE = 0.30

# Little words that carry no meaning on their own. A sentence made only of these
# (and words the model has never seen) is treated as "not understood".
STOPWORDS = set("""a an the i me my we you your he she it is am are was be been do does did to of in on at for
and or but not no so if as by with from this that what how when where who which can could would should will
have has had there here just about up out""".split())

# Safety check (a simple word list, separate from the model)
EMERGENCY_WORDS = [
    "chest pain", "can't breathe", "cannot breathe", "can not breathe", "difficulty breathing",
    "unconscious", "bleeding heavily", "heavy bleeding", "overdose", "stroke", "heart attack",
]
SELF_HARM_WORDS = [
    "suicide", "kill myself", "harm myself", "hurt myself", "want to die", "end my life", "don't want to live",
]


# ---------- 2 and 3. Features and model ----------

def _stem(word: str) -> str:
    """Very light stemming, so finding = find, doctors = doctor, worried = worry, homesickness = homesick."""
    if len(word) > 6 and word.endswith("ness"):
        return word[:-4]
    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 4 and word.endswith("ied"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("ed"):
        return word[:-2]
    if len(word) > 4 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def _plain(text: str) -> str:
    """Lower case, no punctuation. NOT shortened: the safety word lists need the exact words."""
    text = text.lower().replace("’", "'")
    return " ".join(re.sub(r"[^a-z0-9' ]+", " ", text).split())


def _clean(text: str) -> str:
    """For the model: plain text with every word lightly shortened."""
    return " ".join(_stem(word) for word in _plain(text).split())


def _make_model():
    return make_pipeline(
        TfidfVectorizer(preprocessor=_clean, ngram_range=(1, 2), sublinear_tf=True,
                        stop_words=sorted(STOPWORDS)),
        LogisticRegression(C=8, max_iter=2000),
    )


def _data():
    texts, labels = [], []
    for label, sentences in TRAINING_DATA.items():
        texts += sentences
        labels += [label] * len(sentences)
    return texts, labels


_MODEL = None


def get_model():
    """Train once, then reuse."""
    global _MODEL
    if _MODEL is None:
        texts, labels = _data()
        _MODEL = _make_model().fit(texts, labels)
    return _MODEL


# ---------- 4. Testing ----------

def evaluate(folds: int = 5) -> dict:
    """Cross-validation: train on part of the data, test on the rest, repeat."""
    texts, labels = _data()
    scores = cross_val_score(_make_model(), texts, labels, cv=folds)
    return {"examples": len(texts), "cards": len(TRAINING_DATA) - 1,
            "accuracy": float(scores.mean()), "spread": float(scores.std())}


def held_out_check():
    """How many of the test sentences get the right card? Returns (right, total, mistakes)."""
    model = get_model()
    mistakes = []
    for text, expected in CONCERN_TEST:
        guess = str(model.predict([text])[0])
        if guess != expected:
            mistakes.append((text, expected, guess))
    return len(CONCERN_TEST) - len(mistakes), len(CONCERN_TEST), mistakes


# ---------- 5. Use ----------

def safety_flag(text: str) -> str:
    """'self_harm', 'emergency' or '' (nothing found)."""
    clean = _plain(text)
    if any(w in clean for w in SELF_HARM_WORDS):
        return "self_harm"
    if any(w in clean for w in EMERGENCY_WORDS):
        return "emergency"
    return ""


def understood(text: str) -> bool:
    """True if the sentence has at least one meaningful word the model has seen before.
    (Stops nonsense like 'asdfgh' or 'what is the capital of France' from getting a match.)"""
    vocabulary = get_model().named_steps["tfidfvectorizer"].vocabulary_
    words = [w for w in _clean(text).split() if w not in STOPWORDS]
    return any(w in vocabulary for w in words)


def is_other(text: str) -> bool:
    """True if the model thinks this sentence is not about any card."""
    return predict(text, top=1)[0][0] == OTHER


def predict(text: str, top: int = 3) -> list:
    """Best matches as [(card label, confidence 0-1), ...]."""
    model = get_model()
    probabilities = model.predict_proba([text])[0]
    ranked = sorted(zip(model.classes_, probabilities), key=lambda p: -p[1])
    return [(str(label), float(p)) for label, p in ranked[:top]]


if __name__ == "__main__":
    info = evaluate()
    print(f"Training sentences: {info['examples']}, cards: {info['cards']} (+ Something else)")
    print(f"5-fold cross-validation accuracy: {info['accuracy']:.3f} (+/- {info['spread']:.3f})")
    right, total, mistakes = held_out_check()
    print(f"Held-out test sentences: {right} of {total} right ({right / total:.0%})")
    for text, expected, guess in mistakes:
        print(f"   wrong: {text!r}  expected: {expected}  model says: {guess}")
