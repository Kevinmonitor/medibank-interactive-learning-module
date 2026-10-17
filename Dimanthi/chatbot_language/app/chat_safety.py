"""
Safety words in 5 languages for the OSHC chatbot - Dimi's part

The chatbot's own safety checks (app/pipeline.py) know English, Indonesian, Chinese and
Vietnamese with accents. This file adds Sinhala, Farsi, Vietnamese typed WITHOUT accents and
more Indonesian, including the way students type in English letters
("mata husma ganna amaruyi", "nafasam bala nemiad").

It runs on the student's ORIGINAL words, before any translation,
so safety never depends on the AI translation working.

Order (same as pipeline.py):  crisis -> emergency -> wellbeing -> clinical (nurse line)
"""

import unicodedata

# ---------- Crisis (self-harm) -> Lifeline ----------
CRISIS = [
    # Sinhala
    "මැරෙන්න ඕන", "මැරෙන්න හිතෙනවා", "මැරෙන්න හිතෙනවා", "දිවි නසා", "සියදිවි", "ජීවිතේ එපා", "ජීවිතය එපා",
    "මට මැරෙන්න", "මාව මරාගන්න", "marenna one", "marenna hithenawa", "maarenna hithenawa",
    "diwi nasa", "siyadivi", "jeewithe epa", "jivithe epa", "mawa maraganna",
    # Farsi
    "خودکشی", "میخوام بمیرم", "می خواهم بمیرم", "میخواهم بمیرم", "می خوام بمیرم", "خودمو بکشم",
    "به خودم آسیب", "khodkoshi", "mikham bemiram", "mikhaam bemiram", "khodamo bokosham",
    # Vietnamese
    "tự tử", "tu sat", "tự sát", "muon chet", "muốn chết", "khong muon song", "không muốn sống",
    "lam hai ban than", "làm hại bản thân",
    # Indonesian
    "bunuh diri", "ingin mati", "pengen mati", "mau mati", "menyakiti diri", "melukai diri", "akhiri hidup",
]

# ---------- Emergency -> 000 ----------
EMERGENCY = [
    # Sinhala
    "හුස්ම ගන්න බැහැ", "හුස්ම ගන්න බෑ", "හුස්ම ගන්න අමාරු", "පපුවේ වේදනාව", "පපුව රිදෙනවා", "සිහිය නැති",
    "ලේ ගලනවා", "husma ganna bae", "husma ganna be", "husma ganna amaru", "husma ganna amaruyi",
    "papuwa ridenawa", "papuwe wedanawa", "sihiya nathi", "le galanawa",
    # Farsi
    "نمی توانم نفس بکشم", "نمیتونم نفس بکشم", "نمی تونم نفس بکشم", "نفسم بالا نمیاد", "درد قفسه سینه",
    "سینه ام درد", "بیهوش", "خونریزی شدید", "nafas nemitoonam bekesham", "nafasam bala nemiad",
    "dard ghafase sine", "sinam dard", "bihoosh",
    # Vietnamese (with and without accents)
    "kho tho", "khó thở", "khong tho duoc", "không thở được", "dau nguc", "đau ngực", "bat tinh",
    "bất tỉnh", "chay mau nhieu", "chảy máu nhiều", "dot quy", "đột quỵ",
    # Indonesian
    "sesak napas", "tidak bisa bernapas", "susah bernapas", "nyeri dada", "sakit dada", "pingsan",
    "pendarahan hebat",
]

# ---------- Wellbeing -> free counselling ----------
WELLBEING = [
    # Sinhala
    "තනිකම", "තනියම", "ගෙදර මතක්", "දුකයි", "ආතතිය", "බයයි", "කලකිරිලා", "thanikama", "thaniyama",
    "gedara mathak", "dukai", "athathiya", "bayai", "kalakirila", "kalakirilla",
    # Farsi
    "تنهام", "تنها هستم", "دلتنگ", "دلم برای خانواده", "غمگین", "استرس دارم", "اضطراب", "tanham",
    "deltangam", "deltang", "ghamgin", "esteres daram",
    # Vietnamese
    "co don", "cô đơn", "nho nha", "nhớ nhà", "rat buon", "rất buồn", "buồn quá", "buon qua",
    "cang thang", "căng thẳng", "lo au", "lo âu",
    # Indonesian
    "kangen rumah", "rindu keluarga", "tertekan", "gelisah", "kesepian", "sedih",
]

# ---------- Symptoms -> nurse line ----------
CLINICAL = [
    # Sinhala
    "රිදෙනවා", "වේදනාව", "උණ", "කැස්ස", "හෙම්බිරිස්සාව", "ඔක්කාරය", "වමනය", "කැසීම", "ridenawa",
    "riddenawa", "wedanawa", "unai", "una thiyenawa", "kassa", "hembirissawa", "okkaraya", "wamanaya",
    "kasanawa",
    # Sinhala "I feel unwell" (many spellings students use)
    "අමාරුයි", "අමාරු", "අසනීපයි", "අසනීප", "සනීප නැහැ", "සනීප නෑ", "amarui", "amaruyi", "amaruy",
    "amrui", "amaruwak", "asaneepai", "asanipai", "asaneepa", "asanipa", "sanipa na", "sanipa nae",
    "saneepa na", "saneepa nae", "kanthoru", "ladai",
    # Farsi
    "درد", "دردم", "تب", "تبم", "تب دارم", "سرفه", "سرماخوردگی", "حالت تهوع", "استفراغ", "سرگیجه",
    "dard", "dardam", "tab daram", "sorfe", "sarmakhordegi", "halat tahavo", "sargije",
    # Vietnamese
    "dau dau", "đau đầu", "sot", "sốt", "buon non", "buồn nôn", "chong mat", "chóng mặt", "dau bung",
    "đau bụng", "dau rang", "đau răng", "cam cum", "cảm cúm",
    # Indonesian
    "demam", "batuk", "pilek", "pusing", "mual", "muntah", "sakit kepala", "sakit perut", "sakit gigi",
]

# A question about cover that names a symptom is not a symptom report (same idea as pipeline.py)
COVERAGE = ["cover", "covered", "claim", "oshc", "policy", "benefit", "ආවරණ", "awarana", "පොලිසිය",
            "පොලිසිය", "پوشش", "بیمه", "poshesh", "bime", "bao hiem", "bảo hiểm", "chi tra", "chi trả",
            "ditanggung", "tercover", "klaim", "asuransi"]
FIRST_PERSON = ["i", "im", "my", "me", "මට", "මම", "මගේ", "mata", "mama", "mage", "من", "دارم", "man",
                "daram", "toi", "tôi", "minh", "mình", "em", "saya", "aku"]


# ---------- NLP: clean the text the same way for words and messages ----------

def _clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "").lower().replace("‌", " ").replace("’", "'")
    text = "".join(ch if unicodedata.category(ch)[0] in "LMN" or ch == "'" else " " for ch in text)
    return " ".join(text.split())


def _no_accents(text: str) -> str:
    """Vietnamese without accents: 'đau ngực' -> 'dau nguc' (Sinhala and Farsi are left as they are)."""
    out = []
    for ch in unicodedata.normalize("NFD", text):
        if unicodedata.category(ch) == "Mn" and ord(ch) < 0x0370:
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out)).replace("đ", "d")


def _has(words, text):
    """Whole-word match. Sinhala words can take endings (රිදෙනවා -> රිදෙනවාද), so Sinhala only
    needs the start of the word to match."""
    hay = " " + _clean(text) + " "
    plain = " " + _no_accents(_clean(text)) + " "
    for w in words:
        word = _clean(w)
        if not word:
            continue
        sinhala = any("඀" <= ch <= "෿" for ch in word)
        if sinhala:
            if " " + word in hay:
                return w
        elif " " + word + " " in hay or (word.isascii() and " " + word + " " in plain):
            return w
    return None


def crisis(text: str):
    """'crisis', 'emergency' or None."""
    if _has(CRISIS, text):
        return "crisis"
    if _has(EMERGENCY, text):
        return "emergency"
    return None


def wellbeing(text: str):
    if _has(COVERAGE, text) and not _has(FIRST_PERSON, text):
        return None
    return _has(WELLBEING, text)


def clinical(text: str):
    """(True, word) when the student describes a symptom, otherwise None."""
    word = _has(CLINICAL, text)
    if not word:
        return None
    if _has(COVERAGE, text) and not _has(FIRST_PERSON, text):
        return None
    return True, word


if __name__ == "__main__":
    tests = [
        ("mata marenna hithenawa", "crisis"), ("මට මැරෙන්න හිතෙනවා", "crisis"), ("میخوام بمیرم", "crisis"),
        ("toi muon chet", "crisis"), ("saya ingin bunuh diri", "crisis"),
        ("mata husma ganna amaruyi", "emergency"), ("نمی‌توانم نفس بکشم", "emergency"),
        ("toi bi dau nguc", "emergency"), ("teman saya pingsan", "emergency"),
        ("mata gedara mathak wenawa", "wellbeing"), ("خیلی دلتنگ خانواده‌ام هستم", "wellbeing"),
        ("toi thay co don", "wellbeing"), ("saya kangen rumah", "wellbeing"),
        ("mage dath ridenawa", "clinical"), ("mata amrui", "clinical"), ("mata asaneepai", "clinical"),
        ("මට අමාරුයි", "clinical"), ("මට උණයි", "clinical"), ("تب دارم", "clinical"),
        ("toi bi sot", "clinical"), ("saya demam", "clinical"),
        # must NOT be blocked
        ("dath dosthara cover wenawada", None), ("دندانپزشکی پوشش داده می‌شود", None),
        ("dau rang co duoc bao hiem khong", None), ("apakah sakit gigi ditanggung", None),
        ("kitabam ra gom kardam", None), ("من کتاب دارم", None), ("tu tu thoi", None),
    ]
    ok = 0
    for text, want in tests:
        got = crisis(text) or ("wellbeing" if wellbeing(text) else None) or ("clinical" if clinical(text) else None)
        ok += got == want
        print(("OK " if got == want else "!! ") + f"{text!r}: {got} (expected {want})")
    print(f"\n{ok}/{len(tests)} correct")
