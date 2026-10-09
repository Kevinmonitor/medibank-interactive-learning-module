"""Counts which practice card the model suggested (for the admin dashboard).

PRIVACY: this stores only a number per card, for example
    {"I feel homesickness": 12, "I need medication": 3}
and, for the learning quiz, only how many answers were right or wrong per question, for example
    {"claim_all": {"right": 7, "wrong": 5}}
It does NOT store the sentence, the voice, the time, the name or any ID.
If this ever changes, the privacy note in voice_section.py (HOW_IT_WORKS) must change too.
"""

import json
import os
from pathlib import Path

COUNTS_FILE = Path(__file__).parent / "data" / "card_counts.json"

# The 8 cards, in the same words as the Question page
CARDS = [
    "I feel homesickness",
    "I need to go to hospital",
    "I get sick",
    "I need medication",
    "I need to find a health provider",
    "Comprehensive OSHC coverage",
    "I need to make a claim",
    "Nothing, just here to learn",
]


def read_counts() -> dict:
    """Count per card (0 for cards never suggested)."""
    counts = {card: 0 for card in CARDS}
    try:
        saved = json.loads(COUNTS_FILE.read_text(encoding="utf-8"))
        for card, number in saved.items():
            if card in counts:
                counts[card] = int(number)
    except (FileNotFoundError, ValueError):
        pass
    return counts


def log_card(card: str) -> None:
    """Add 1 to the card the model suggested. Never stops the app if saving fails."""
    if card not in CARDS:
        return
    try:
        counts = read_counts()
        counts[card] += 1
        COUNTS_FILE.parent.mkdir(exist_ok=True)
        temp = COUNTS_FILE.with_suffix(".tmp")
        temp.write_text(json.dumps(counts, indent=2), encoding="utf-8")
        os.replace(temp, COUNTS_FILE)      # replace in one step, so the file is never half-written
    except OSError:
        pass


def clear_counts() -> None:
    try:
        COUNTS_FILE.unlink()
    except FileNotFoundError:
        pass


# ---------- Learning quiz (page "Nothing, just here to learn") ----------
# Only counts per question: how many answers were right and how many were wrong.

QUIZ_FILE = Path(__file__).parent / "data" / "quiz_counts.json"

# question id -> short label shown on the dashboard
QUIZ_QUESTIONS = {
    "pays_all": "Medibank pays whatever the doctor charges",
    "gp_rate": "GP visits are paid at 100% of the MBS fee",
    "glasses": "Glasses are covered by Comprehensive OSHC",
    "claim_now": "You can claim for everything straight after you join",
    "rx_free": "A prescribed medicine is free at the pharmacy",
    "psych_hosp": "Hospital psychiatric services are open to you straight away",
    "cosmetic": "Cosmetic treatment is paid",
    "ivf": "IVF is covered",
    "counselling": "Counselling is paid up to $70 per consultation",
    "ambulance": "Eligible emergency ambulance is covered across Australia",
}


def read_quiz() -> dict:
    """{question id: {"right": n, "wrong": n}} for every question (0 if never answered)."""
    result = {q: {"right": 0, "wrong": 0} for q in QUIZ_QUESTIONS}
    try:
        saved = json.loads(QUIZ_FILE.read_text(encoding="utf-8"))
        for q, c in saved.items():
            if q in result:
                result[q] = {"right": int(c.get("right", 0)), "wrong": int(c.get("wrong", 0))}
    except (FileNotFoundError, ValueError, AttributeError):
        pass
    return result


def log_quiz(question: str, correct: bool) -> None:
    """Add 1 to right or wrong for this question. Never stops the app if saving fails."""
    if question not in QUIZ_QUESTIONS:
        return
    try:
        counts = read_quiz()
        counts[question]["right" if correct else "wrong"] += 1
        QUIZ_FILE.parent.mkdir(exist_ok=True)
        temp = QUIZ_FILE.with_suffix(".tmp")
        temp.write_text(json.dumps(counts, indent=2), encoding="utf-8")
        os.replace(temp, QUIZ_FILE)
    except OSError:
        pass


def clear_quiz() -> None:
    try:
        QUIZ_FILE.unlink()
    except FileNotFoundError:
        pass
