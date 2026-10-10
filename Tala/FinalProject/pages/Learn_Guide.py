"""
"Nothing, just here to learn": learning page (OSHC Compass)

Two tabs:
  1. A Myth or fact quiz. Each answer is counted for the admin dashboard.
     ONLY counts are saved (right or wrong per question, see analytics.py):
     no names, no times, no sentences.
  2. A picture glossary of the words students hear in Australia (GP, MBS, Rx, ...).

The facts in the quiz answers and the glossary are READ FROM THE PDF every time the PDF changes.
If a part can no longer be found, the saved text (FALLBACK below) is used for it and this
page shows a warning. A question is skipped if its fact is missing in both places.
Words that are NOT in the brochure are marked "General knowledge" in the glossary.

Folder layout:
    oshc_welcome.py
    pages/Learn_Guide.py           <- this file
    learn_guide.html               <- the glossary (main folder, or next to this file)
    analytics.py                   <- counts the quiz answers
    OSHC_Brochure.pdf
"""

import json
import re
from pathlib import Path
from urllib.parse import quote

import pdfplumber
import streamlit as st
import streamlit.components.v1 as components

import analytics
import auth


# ---------- Settings ----------

HOME_PAGE = "pages/1_Question.py"
ROOT = Path(__file__).parent.parent          # the main project folder
PDF_FILE = ROOT / "OSHC_Brochure.pdf"
GLOSSARY_HEIGHT = 900


def find_html() -> Path:
    """Find the glossary file (main folder, this folder, "assets" or "images")."""
    here = Path(__file__).parent
    for folder in (ROOT, here, ROOT / "assets", ROOT / "images"):
        found = sorted(folder.glob("learn_guide*.html"))
        if found:
            return found[0]
    return ROOT / "learn_guide.html"


HTML_FILE = find_html()

# What we read from the PDF.
# (key used in the HTML, label, where it is, pattern). Group 1 of the pattern is the value
# (if there is no group, the whole match is used).
(INTRO, HOSP, HOSPTBL, MEDICAL, RX, EXTRAS, MENTAL, MORE, LIMITS, CONTACT, AMB) = (
    "intro", "hosp", "hosptbl", "medical", "rx", "extras", "mental", "more", "limits", "contact", "amb")

READ_FROM_PDF = [
    ("pbs", "What the PBS is", "pbs",
     r"(The government.s Pharmaceutical Benefits Scheme \(PBS\) provides Australian residents.*?subsidised prices\.)"),
    ("directBilling", "What direct billing is", "dbill",
     r"(A direct billing GP provider sends your).*?(bill directly to us at the time of your).*?(appointment\.)"),
    ("membersChoice", "Members' Choice hospitals", "mc",
     r"(We also pay towards accommodation at a Non-Members.\s?Choice private hospital, but the benefits we pay will generally be lower and we may not pay towards all services \(e\.g\. theatre fees and private rooms\)\.)"),
    ("intro", "What Comprehensive OSHC helps pay", INTRO,
     r"(Comprehensive OSHC can help pay towards the cost of a range of in-hospital procedures.*?Australia-wide\.)"),
    ("who1", "Who it is for: not a permanent resident", INTRO, r"• (Do not hold permanent resident status in Australia)"),
    ("who2", "Who it is for: not eligible for Medicare", INTRO, r"• (Are not eligible for full Medicare benefits)"),
    ("who3", "Who it is for: 500 Student visa", INTRO,
     r"• (Are/will be in Australia on a 500 Student visa subclass as): º (An Overseas Student), or º (An eligible Dependant of an Overseas Student)"),
    ("hospitalIntro", "Hospital cover", HOSP,
     r"Hospital cover can help pay towards your treatment when you.re admitted to hospital as a private patient\. It also helps pay towards the cost of accommodation and medical services for Included services provided in hospital\."),
    ("waitNote", "Waiting periods and pregnancy", HOSP,
     r"It.s important to be aware that waiting periods may apply to some services, including Pre-existing Conditions and Pregnancy and birth services\."),
    ("cosmetic", "No cosmetic treatment", HOSP,
     r"Medibank does not pay towards cosmetic treatment or services without an MBS item\."),
    ("pharmaLimited", "Limited benefits for pharmaceuticals", HOSP,
     r"Under Comprehensive OSHC, we pay limited benefits towards pharmaceuticals\. You may have large out-of-pocket expenses if you require high-cost drugs, such as those used in oncology \(cancer treatment\)\."),
    ("waitingPeriods", "Waiting periods", HOSP,
     r"A waiting period applies when you join Medibank, or change your cover to include new or upgraded services\. We won.t pay benefits for any items purchased or services received while you are serving a waiting period\."),
    ("extrasSeparate", "Extras are bought separately", HOSP,
     r"You can purchase a Medibank Extras cover separately to help towards the cost of everyday health services, like dental and optical\."),
    ("mbsDef", "What the MBS fee is", MEDICAL,
     r"The Medicare Benefits Schedule \(MBS\) is a list.*?known as the MBS fee\."),
    ("mustPayDiff", "You pay the difference", MEDICAL,
     r"You must pay any difference between the benefit we pay and the actual fee charged for the service\."),
    ("eligible", "Only prescribed medicines are paid", RX,
     r"Benefits are payable only for prescription medicines prescribed by a doctor \(GP or specialist\) to treat an illness, injury or condition\."),
    ("contribution", "Medicines: member contribution", RX, r"Member contribution (\$[\d,]+)"),
    ("pct", "Medicines: amount Medibank pays", RX, r"Amount we.ll pay \(maximum per item\) (\d+% of cost)"),
    ("annualSingle", "Medicines: annual limit, single", RX, r"Annual limit . Single membership (\$[\d,]+)"),
    ("annualFamily", "Medicines: annual limit, family", RX,
     r"Annual limit . Couple/Family membership (\$[\d,]+ per member / \$[\d,]+ per membership)"),
    ("notCovered", "Medicines: cosmetic and Excluded", RX,
     r"We don.t pay benefits towards prescription medicines for cosmetic purposes or for prescription medicines that relate to an Excluded service\."),
    ("highCost", "Medicines: high-cost medicines", RX,
     r"It.s important to note that you may have large out-of-pocket expenses.*?cancer treatment\)\."),
    ("ambulanceHelp", "Emergency ambulance", AMB, r"(eligible emergency ambulance services Australia-wide)"),
    ("ambulanceNote", "When the ambulance is covered", AMB,
     r"# (For ambulance attendance or transportation.*?any other way\.)"),
    ("mentalIntro", "Mental health support", MENTAL,
     r"(Comprehensive OSHC provides benefits towards psychology, counselling and mental health social workers services received from recognised providers and billed without an MBS item number\.)"),
    ("psychiatric", "Hospital psychiatric services", MENTAL,
     r"With Medibank OSHC, you.ll have immediate access to hospital psychiatric services even if it.s treatment for a pre-existing condition\."),
    ("repatriation", "Repatriation: travel", MORE, r"we may arrange and pay the reasonable cost of travel with the appropriate medical supervision \(up to a maximum of (\$[\d,]+)\)"),
    ("remains", "Repatriation: mortal remains", MORE, r"repatriation of mortal remains of you \(or anyone else on your membership\) to your home country \(up to a maximum of (\$[\d,]+)\)"),
    ("repatNote", "Repatriation: conditions", MORE,
     r"The provision of any repatriation benefit is at our discretion and is payable only once per member per lifetime\. Conditions apply, including waiting periods\."),
    ("boarder", "Family stay in hospital (boarder fee)", MORE, r"up to (\$\d+) per admission"),
    ("annualLimit", "What an annual limit is", LIMITS,
     r"An annual limit is the maximum amount of benefits payable per member and/or per membership, within a calendar year \(1 January to 31 December\)\."),
    ("phoneAu", "Phone (in Australia)", CONTACT, r"(134 148) \(from within Australia\)"),
    ("hours", "Phone hours", CONTACT, r"Available (Monday to Friday 8am-8pm AEST)"),
]

# A phrase that is only on that page
PAGE_MARKERS = {
    INTRO: "Comprehensive OSHC is intended for people who",
    HOSP: "Hospital cover can help pay towards your treatment",
    MEDICAL: "Medical cover pays towards",
    RX: "Member contribution",
    EXTRAS: "Prescription pharmaceuticals (non-PBS)",
    MENTAL: "mental health social workers services received from recognised providers",
    MORE: "Repatriation.",
    LIMITS: "An annual limit is the maximum amount",
    CONTACT: "to find your nearest Medibank store",
    AMB: "eligible emergency ambulance services",
    "pbs": "Pharmaceutical Benefits Scheme (PBS) provides",
    "dbill": "A direct billing GP provider sends",
    "mc": "Non-Members’ Choice private hospital",
}
PLAN_KEYS = ["healthy", "essential", "top60", "top75", "top90"]
MARKS = "*^+†‡~#&"


# ---------- Reading the PDF ----------

@st.cache_data
def read_pdf(pdf_path: str, modified_time: float) -> dict:
    """The text and the tables of every PDF page (reloads when the PDF changes)."""
    with pdfplumber.open(pdf_path) as pdf:
        return {
            "pages": [p.extract_text() or "" for p in pdf.pages],
            "tables": [p.extract_tables() for p in pdf.pages],
        }


def _flat(text) -> str:
    """One line, single spaces."""
    return " ".join((text or "").split())


def _page_label(index: int, pages: list) -> str:
    """'page 5' (the printed number; a spread shows 'left middle right', use the middle), or a cover."""
    last = pages[index].strip().split("\n")[-1].split()
    if last and all(w.isdigit() for w in last):
        return f"page {last[len(last) // 2]}"
    if index >= len(pages) - 1:
        return "the back cover"
    return "the inside front cover" if index <= 1 else f"PDF page {index + 1}"


def read_rates(tables: list) -> dict:
    """The 'We pay 100% / 85% of the MBS fee for' table: which service gets which percentage."""
    rates, current = {}, None
    for table in tables:
        if not table or not table[0] or "Included services" not in (table[0][0] or ""):
            continue
        for left, right in (r for r in table[1:] if len(r) >= 2):
            percent = re.search(r"(\d+)%", left or "")
            current = percent.group(1) + "%" if percent else current
            text = _flat(right).lower()
            if current and "general practitioner" in text:
                rates["gpRate"] = current
            elif current and "other medical services" in text:
                rates["specRate"] = current
    return rates


def read_mental(tables: list) -> dict:
    """The mental health table: Psychology / Counselling and social workers, and the annual limits."""
    for table in tables:
        flat = [[_flat(c) for c in row] for row in table if row]
        if len(flat) >= 4 and "Psychology" in flat[0] and "maximum per consultation" in flat[1][0]:
            return {"psychology": flat[1][1], "social": flat[1][2],
                    "limitSingle": flat[2][1], "limitFamily": flat[3][1]}
    return {}


def read_hospital(data: dict, flat: list):
    """The Included / Excluded list of in-hospital services (a tick = Included, a cross = Excluded)."""
    for i, tables in enumerate(data["tables"]):
        for table in tables:
            if table and table[0] and "Services that are Included or Excluded" in (table[0][0] or ""):
                notes = {}
                for mark, pattern in (("*", r"\* (We will only pay.*?under your cover\.)"),
                                      ("^", r"\^ (For Dental surgery.*?medical charges\.)"),
                                      ("+", r"\+ (For Podiatric surgery.*?out-of-pocket expenses\.)")):
                    found = re.search(pattern, flat[i])
                    if found:
                        notes[mark] = found.group(1)
                items = []
                for name, symbol in ((_flat(r[0]), _flat(r[1])) for r in table[1:] if len(r) >= 2):
                    if not name or symbol not in ("c", "b"):
                        continue
                    mark = name[-1] if name[-1] in MARKS else ""
                    items.append({"name": name.rstrip(MARKS).strip(),
                                  "in": symbol == "c", "note": notes.get(mark, "")})
                return i, items
    return None, []


def read_extras(tables: list) -> dict:
    """The Extras table. Blank cells in the PDF are merged cells: they repeat the cell above."""
    for table in tables:
        if not table or len(table[0]) < 8 or "Waiting period" not in _flat(table[0][2]):
            continue
        header = [(c or "").split("\n") for c in table[0]]
        plans = [{"key": k, "name": _flat(header[3 + n][0]) if header[3 + n] else k,
                  "about": _flat(" ".join(header[3 + n][1:]))} for n, k in enumerate(PLAN_KEYS)]
        rows, above, previous_name = [], [""] * 8, ""
        for raw in table[1:]:
            cells = [_flat(c).strip() for c in raw]
            name = cells[0].split(" Members")[0].rstrip(MARKS + " ")
            if not name:
                name = previous_name
            for c in range(2, 8):                      # blank = merged with the cell above
                cells[c] = cells[c] or above[c]
            above = cells
            previous_name = name
            vals = [("not covered" if v == "b" else v.rstrip(MARKS + " ")) for v in cells[3:8]]
            rows.append({"name": name, "desc": cells[1].rstrip("~ "), "wait": cells[2], "vals": vals})
        return {"plans": plans, "rows": rows}
    return {}


def read_facts(data: dict):
    """Return (payload for the HTML, parts that were not found)."""
    pages, flat = data["pages"], [_flat(t) for t in data["pages"]]
    found = {name: next((i for i, t in enumerate(flat) if phrase in t), None)
             for name, phrase in PAGE_MARKERS.items()}

    facts, missing = {}, []
    for key, label, where, pattern in READ_FROM_PDF:
        i = found[where]
        match = re.search(pattern, flat[i], re.S) if i is not None else None
        if not match:
            missing.append(label)
            continue
        value = " ".join(g for g in match.groups() if g) if match.groups() else match.group(0)
        if key == "who3":
            value = f"{match.group(1)} an Overseas Student, or an eligible Dependant of an Overseas Student"
        facts[key] = re.sub(r"[\^#&]+(?=[\s,.]|$)", "", value.strip())

    i = found[MEDICAL]
    rates = read_rates(data["tables"][i]) if i is not None else {}
    for key, label in (("gpRate", "GP consultations: % of MBS fee"),
                       ("specRate", "Specialists, pathology, x-rays: % of MBS fee")):
        if key in rates:
            facts[key] = rates[key]
        else:
            missing.append(label)

    i = found[MENTAL]
    mental = read_mental(data["tables"][i]) if i is not None else {}
    if mental:
        facts.update(mental)
    else:
        missing.append("Mental health table (Psychology / Counselling)")

    h_index, hospital = read_hospital(data, flat)
    if not hospital:
        missing.append("List of Included and Excluded hospital services")
    if h_index is not None and found[HOSP] is not None:
        if "Included c or Excluded b" not in flat[found[HOSP]]:
            missing.append("The meaning of the tick and cross (page changed: check the hospital list)")

    i = found[EXTRAS]
    extras = read_extras(data["tables"][i]) if i is not None else {}
    if not extras:
        missing.append("Extras table")

    labels = {name: _page_label(i, pages) for name, i in found.items() if i is not None}
    if h_index is not None:
        labels["hosptbl"] = _page_label(h_index, pages)
    payload = {"facts": facts, "pages": labels, "hospital": hospital, "extras": extras}
    return payload, missing





# ---------- Saved copy (used for any part the PDF no longer has) ----------

FALLBACK_FACTS = {
    "pbs": "The government’s Pharmaceutical Benefits Scheme (PBS) provides Australian residents, as well as certain international visitors covered by a Reciprocal Health Care Agreement with access to many prescription medicines at subsidised prices.",
    "directBilling": "A direct billing GP provider sends your bill directly to us at the time of your appointment.",
    "membersChoice": "We also pay towards accommodation at a Non-Members’ Choice private hospital, but the benefits we pay will generally be lower and we may not pay towards all services (e.g. theatre fees and private rooms).",
    "intro": "Comprehensive OSHC can help pay towards the cost of a range of in-hospital procedures as well as out-of-hospital medical services, such as visits to a general practitioner (GP) or specialist services like x-rays. It can also help with the cost of a range of prescription medicines and eligible emergency ambulance services Australia-wide.",
    "who1": "Do not hold permanent resident status in Australia",
    "who2": "Are not eligible for full Medicare benefits",
    "who3": "Are/will be in Australia on a 500 Student visa subclass as an Overseas Student, or an eligible Dependant of an Overseas Student",
    "hospitalIntro": "Hospital cover can help pay towards your treatment when you’re admitted to hospital as a private patient. It also helps pay towards the cost of accommodation and medical services for Included services provided in hospital.",
    "waitNote": "It’s important to be aware that waiting periods may apply to some services, including Pre-existing Conditions and Pregnancy and birth services.",
    "cosmetic": "Medibank does not pay towards cosmetic treatment or services without an MBS item.",
    "pharmaLimited": "Under Comprehensive OSHC, we pay limited benefits towards pharmaceuticals. You may have large out-of-pocket expenses if you require high-cost drugs, such as those used in oncology (cancer treatment).",
    "waitingPeriods": "A waiting period applies when you join Medibank, or change your cover to include new or upgraded services. We won’t pay benefits for any items purchased or services received while you are serving a waiting period.",
    "extrasSeparate": "You can purchase a Medibank Extras cover separately to help towards the cost of everyday health services, like dental and optical.",
    "mbsDef": "The Medicare Benefits Schedule (MBS) is a list of all the medical services subsidised by the government for Australian residents, including visiting a GP or seeing a specialist, as well as the recommended fees for those services, known as the MBS fee.",
    "mustPayDiff": "You must pay any difference between the benefit we pay and the actual fee charged for the service.",
    "eligible": "Benefits are payable only for prescription medicines prescribed by a doctor (GP or specialist) to treat an illness, injury or condition.",
    "contribution": "$30",
    "pct": "100% of cost",
    "annualSingle": "$1,000",
    "annualFamily": "$1,000 per member / $2,000 per membership",
    "notCovered": "We don’t pay benefits towards prescription medicines for cosmetic purposes or for prescription medicines that relate to an Excluded service.",
    "highCost": "It’s important to note that you may have large out-of-pocket expenses if you need treatment that uses high-cost prescription medicines (e.g. prescription medicines used in cancer treatment).",
    "ambulanceHelp": "eligible emergency ambulance services Australia-wide",
    "ambulanceNote": "For ambulance attendance or transportation to a hospital where immediate medical attention is required and your condition is such that you couldn’t be transported any other way.",
    "mentalIntro": "Comprehensive OSHC provides benefits towards psychology, counselling and mental health social workers services received from recognised providers and billed without an MBS item number.",
    "psychiatric": "With Medibank OSHC, you’ll have immediate access to hospital psychiatric services even if it’s treatment for a pre-existing condition.",
    "repatriation": "$100,000",
    "remains": "$10,000",
    "repatNote": "The provision of any repatriation benefit is at our discretion and is payable only once per member per lifetime. Conditions apply, including waiting periods.",
    "boarder": "$150",
    "annualLimit": "An annual limit is the maximum amount of benefits payable per member and/or per membership, within a calendar year (1 January to 31 December).",
    "phoneAu": "134 148",
    "hours": "Monday to Friday 8am-8pm AEST",
    "gpRate": "100%",
    "specRate": "85%",
    "psychology": "$100",
    "social": "$70",
    "limitSingle": "$200",
    "limitFamily": "$400"
}

FALLBACK_PAGES = {
    "pbs": "page 5",
    "dbill": "page 1",
    "mc": "page 4",
    "intro": "page 2",
    "hosp": "page 6",
    "medical": "page 8",
    "rx": "page 8",
    "extras": "page 10",
    "mental": "page 13",
    "more": "page 13",
    "limits": "page 13",
    "contact": "the back cover",
    "amb": "page 2",
    "hosptbl": "page 7"
}

# Is each hospital service Included? (only the ones the quiz asks about)
FALLBACK_HOSPITAL = {
    "Assisted reproductive services": False
}


# ---------- The quiz ----------
# Each question: id (must exist in analytics.QUIZ_QUESTIONS), the statement, whether it is a FACT,
# the explanation, and the page where it is in the brochure. The answer is worked out from
# the PDF text where it can be, so a changed brochure changes the answer.

def build_questions(F: dict, P: dict, H: dict) -> list:
    """The quiz questions we can ask with the facts we have (others are skipped)."""
    def has(*keys):
        return all(F.get(k) for k in keys)

    qs = []
    if has("mbsDef", "mustPayDiff", "gpRate", "specRate"):
        qs.append(dict(id="pays_all", text="Medibank pays whatever the doctor charges.", fact=False,
                       why=f"Medibank pays a percentage of the MBS fee, not of the price the doctor sets. "
                           f"{F['mbsDef']} {F['mustPayDiff']}", page=P.get("medical")))
    if has("gpRate"):
        qs.append(dict(id="gp_rate", text="For a GP visit with an MBS item, Medibank pays 100% of the MBS fee.",
                       fact=F["gpRate"] == "100%",
                       why=f"The brochure says GP consultations are paid at {F['gpRate']} of the MBS fee. "
                           f"Specialists, pathology (blood tests), x-rays and Allied Health are paid at {F.get('specRate', '?')}.",
                       page=P.get("medical")))
    if has("extrasSeparate"):
        qs.append(dict(id="glasses", text="New glasses are covered by Comprehensive OSHC.", fact=False,
                       why=f"Optical items are an Extras service. {F['extrasSeparate']}", page=P.get("extras")))
    if has("waitingPeriods"):
        qs.append(dict(id="claim_now", text="You can claim for every service straight after you join.", fact=False,
                       why=F["waitingPeriods"], page=P.get("hosp")))
    if has("contribution", "eligible", "annualSingle"):
        qs.append(dict(id="rx_free", text="If your doctor prescribes a medicine, it is free at the pharmacy.", fact=False,
                       why=f"You pay a {F['contribution']} contribution for each item. {F['eligible']} "
                           f"There is also an annual limit ({F['annualSingle']} for a single membership).",
                       page=P.get("rx")))
    if has("psychiatric"):
        qs.append(dict(id="psych_hosp", text="You can use hospital psychiatric services straight away, even for a pre-existing condition.",
                       fact=True, why=F["psychiatric"], page=P.get("mental")))
    if has("cosmetic"):
        qs.append(dict(id="cosmetic", text="Medibank pays for cosmetic treatment even when it has no MBS item number.", fact=False,
                       why=F["cosmetic"], page=P.get("hosp")))
    if "Assisted reproductive services" in H:
        covered = H["Assisted reproductive services"]
        qs.append(dict(id="ivf", text="IVF (assisted reproductive services) is covered by Comprehensive OSHC.", fact=covered,
                       why="In the brochure's list of hospital services, “Assisted reproductive services” is "
                           + ("Included." if covered else "Excluded."), page=P.get("hosptbl")))
    if has("social"):
        qs.append(dict(id="counselling", text=f"Counselling is paid up to {F['social']} for each consultation.", fact=True,
                       why=f"Counselling and mental health social workers: {F['social']} for each consultation. "
                           f"Psychology: {F.get('psychology', '?')}. Annual limit: {F.get('limitSingle', '?')} (single) "
                           f"or {F.get('limitFamily', '?')} (couple or family).", page=P.get("mental")))
    if has("ambulanceHelp", "ambulanceNote"):
        qs.append(dict(id="ambulance", text="Comprehensive OSHC can help with eligible emergency ambulance services across Australia.",
                       fact=True, why=f"It helps with {F['ambulanceHelp']}. {F['ambulanceNote']}", page=P.get("amb")))
    return [q for q in qs if q["id"] in analytics.QUIZ_QUESTIONS]


def page_text(page) -> str:
    return f"Brochure: {page}" if page else "Brochure"


def start_quiz(total: int) -> None:
    st.session_state.update(quiz_i=0, quiz_score=0, quiz_picked=None, quiz_total=total)


def show_quiz(questions: list) -> None:
    """One question at a time. Counts the answer (right or wrong) for the dashboard."""
    if "quiz_i" not in st.session_state or st.session_state.get("quiz_total") != len(questions):
        start_quiz(len(questions))
    i, total = st.session_state.quiz_i, len(questions)

    st.markdown(
        """<style>
        .quiz-card{border:1.5px solid #d7dbe1;border-radius:16px;padding:1.4rem 1.6rem;margin:.6rem 0 1rem;background:#fff}
        .quiz-card .q-no{color:#C8322E;font:700 .75rem ui-monospace,Menlo,monospace;letter-spacing:.08em;text-transform:uppercase}
        .quiz-card .q-text{color:#143a5a;font-size:1.35rem;font-weight:700;line-height:1.3;margin-top:.3rem}
        .quiz-result{border-radius:12px;padding:.9rem 1.1rem;margin:.4rem 0 .8rem}
        .quiz-result.ok{background:#E8F5EE;border:1.5px solid #1E8E4E}
        .quiz-result.no{background:#FCEDEC;border:1.5px solid #C8322E}
        .quiz-result b{font-size:1.05rem}
        .quiz-result .src{color:#5E6B7A;font-size:.8rem;margin-top:.4rem}
        </style>""",
        unsafe_allow_html=True,
    )

    # The end
    if i >= total:
        score = st.session_state.quiz_score
        st.markdown(f"### Your score: {score} out of {total}")
        st.progress(score / total if total else 0)
        if score == total:
            st.success("Perfect. You know your cover very well.")
        elif score >= total * 0.6:
            st.info("Good job. Open the words tab to learn the ones you missed.")
        else:
            st.warning("Many students think some of these are true. Read the words tab, then try again.")
        if st.button("Try again", key="quiz_again"):
            start_quiz(total)
            st.rerun()
        return

    q = questions[i]
    st.progress(i / total, text=f"Question {i + 1} of {total}")
    st.markdown(
        f'<div class="quiz-card"><div class="q-no">Myth or fact?</div>'
        f'<div class="q-text">{q["text"]}</div></div>',
        unsafe_allow_html=True,
    )

    picked = st.session_state.quiz_picked
    if picked is None:
        left, right = st.columns(2)
        choice = None
        if left.button("🙅 Myth", key=f"myth_{i}", use_container_width=True):
            choice = False
        if right.button("✅ Fact", key=f"fact_{i}", use_container_width=True):
            choice = True
        if choice is not None:
            correct = choice == q["fact"]
            analytics.log_quiz(q["id"], correct)            # only a count, no name
            st.session_state.quiz_picked = choice
            st.session_state.quiz_score += int(correct)
            st.rerun()
    else:
        correct = picked == q["fact"]
        verdict = "✅ Right!" if correct else "❌ Not quite."
        label = "It is a FACT." if q["fact"] else "It is a MYTH."
        st.markdown(
            f'<div class="quiz-result {"ok" if correct else "no"}"><b>{verdict} {label}</b><br>'
            f'{q["why"]}<div class="src">{page_text(q["page"])}</div></div>',
            unsafe_allow_html=True,
        )
        if st.button("See my score" if i + 1 >= total else "Next question →", key=f"next_{i}"):
            st.session_state.quiz_i += 1
            st.session_state.quiz_picked = None
            st.rerun()


# ---------- Other helpers ----------

@st.cache_data
def load_html(modified_time: float) -> str:
    """Cached, but reloads when the HTML file changes."""
    return HTML_FILE.read_text(encoding="utf-8")


# ---------- Page ----------

st.set_page_config(page_title="Nothing, just here to learn", layout="wide")
auth.require_login()

back_col, title_col = st.columns([1, 5])

with back_col:
    if st.button("← Back"):
        st.switch_page(HOME_PAGE)

with title_col:
    st.markdown("### Just here to learn")
    st.caption("Test what you think you know about OSHC, then look up the words you will hear in Australia. "
               "This is general information.")

# Read the facts from the PDF (anything missing comes from the saved copy)
live, missing = {}, []
if PDF_FILE.exists():
    try:
        live, missing = read_facts(read_pdf(str(PDF_FILE), PDF_FILE.stat().st_mtime))
        if missing:
            st.warning(
                "Some parts could not be found in the brochure PDF any more (maybe the brochure changed). "
                "The page shows its saved text for these parts, so please check them: " + "; ".join(missing)
            )
    except Exception as error:
        live = {}
        st.warning(f"Couldn't read the brochure PDF. The page is showing its saved text. ({error})")
else:
    st.warning(f"Brochure PDF not found. Put it here: {PDF_FILE}")

facts = {**FALLBACK_FACTS, **live.get("facts", {})}
pages = {**FALLBACK_PAGES, **live.get("pages", {})}
hospital = {**FALLBACK_HOSPITAL, **{h["name"]: h["in"] for h in live.get("hospital", [])}}

quiz_tab, words_tab = st.tabs(["🎯 Myth or fact quiz", "📖 Words you will hear"])

with quiz_tab:
    questions = build_questions(facts, pages, hospital)
    if questions:
        show_quiz(questions)
        st.caption("Your answers are only counted (right or wrong, for each question) so the team can see "
                   "which myths are most common. Your name is not saved.")
    else:
        st.info("The quiz has no questions right now.")

with words_tab:
    if HTML_FILE.exists():
        data = {"facts": facts, "pages": pages, "live": bool(live.get("facts"))}
        html = load_html(HTML_FILE.stat().st_mtime)
        html = html.replace("__PDF_DATA__", quote(json.dumps(data, ensure_ascii=False), safe=""))
        components.html(html, height=GLOSSARY_HEIGHT, scrolling=True)
    else:
        st.error(f"Can't find the glossary file (learn_guide.html). Put it here: {HTML_FILE}")
