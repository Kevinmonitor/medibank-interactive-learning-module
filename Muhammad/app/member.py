"""
Look up a student's cover balance from the member database.
"""
import os
import re
import pandas as pd
from functools import lru_cache

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def _get_url():
    try:
        import streamlit as st
        url = st.secrets.get("MEMBER_SHEET_URL", "")
        if url:
            return url
    except Exception:
        pass
    return os.getenv("MEMBER_SHEET_URL", "")


def _clean_money(val):
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


@lru_cache(maxsize=1)
def _load_members():
    url = _get_url()
    if not url:
        return pd.DataFrame()
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        return df
    except Exception as e:
        print(f"  could not load member sheet: {e}")
        return pd.DataFrame()


def lookup(member_id):
    df = _load_members()
    if df.empty:
        return None
    matches = df[df["member_id"].str.strip().str.upper() == member_id.strip().upper()]
    if matches.empty:
        return None
    row = matches.iloc[0]
    result = {
        "member_id": str(row.get("member_id", "")),
        "name": str(row.get("name", "")),
        "product": str(row.get("product", "")),
        "campus": str(row.get("campus", "")),
        "cover_start": str(row.get("cover_start", "")),
        "cover_end": str(row.get("cover_end", "")),
    }
    for cat in ["medicine", "psych", "ambulance"]:
        used = _clean_money(row.get(f"{cat}_used", 0))
        limit = row.get(f"{cat}_limit", 0)
        if str(limit).strip().lower() in ("unlimited", ""):
            result[f"{cat}_used"] = used
            result[f"{cat}_limit"] = "unlimited"
            result[f"{cat}_remaining"] = "unlimited"
        else:
            limit = _clean_money(limit)
            result[f"{cat}_used"] = used
            result[f"{cat}_limit"] = limit
            result[f"{cat}_remaining"] = max(0, limit - used)
    result["medical_used"] = _clean_money(row.get("medical_used", 0))
    result["medical_limit"] = "unlimited"
    result["medical_remaining"] = "unlimited"
    return result



def _extract_amount(question):
    """Pull a dollar amount from the question."""
    nums = re.findall(r"\$?\s*(\d+(?:\.\d{1,2})?)\s*\$?", question)
    amounts = [float(x) for x in nums if 10 <= float(x) <= 50000]
    return amounts[0] if amounts else None


# Maps question keywords to which category the student is asking about
CATEGORY_MAP = {
    "medicine": "medicine", "medicines": "medicine", "meds": "medicine",
    "prescription": "medicine", "pharmaceutical": "medicine",
    "scripts": "medicine", "pharmacy": "medicine", "obat": "medicine",
    "resep": "medicine",
    "psychologist": "psych", "psychology": "psych", "psych": "psych",
    "counselling": "psych", "counseling": "psych", "mental": "psych",
    "therapy": "psych", "jiwa": "psych",
    "doctor": "medical", "gp": "medical", "medical": "medical",
    "dokter": "medical", "consultation": "medical",
    "ambulance": "ambulance", "amb": "ambulance", "ambo": "ambulance",
}

CATEGORY_LABELS = {
    "medicine": "Prescription medicines",
    "psych": "Psychology and counselling",
    "medical": "Doctor visits",
    "ambulance": "Ambulance",
}


def detect_category(question):
    """What specific category is the student asking about?"""
    q = question.lower()
    for word, cat in CATEGORY_MAP.items():
        if word in q:
            return cat
    return None


def format_balance(member, question=""):
    """Answer the specific question, not dump everything."""
    if not member:
        return None

    name = member.get("name", "")
    cat = detect_category(question) if question else None

    # If they asked about a specific category, answer just that
    if cat == "medical":
        used = member.get("medical_used", 0)
        greeting = f"Hi {name}. " if name else ""
        return (f"{greeting}Doctor visits have no annual limit on your "
                f"{member['product'].title()} OSHC. "
                f"You have used ${used:.0f} so far this year. "
                f"There is no cap on how much you can claim for doctors.")

    if cat in ("medicine", "psych"):
        used = member.get(f"{cat}_used", 0)
        limit = member.get(f"{cat}_limit", 0)
        remaining = member.get(f"{cat}_remaining", 0)
        label = CATEGORY_LABELS.get(cat, cat)
        greeting = f"Hi {name}. " if name else ""

        if isinstance(limit, str) or limit == 0:
            if limit == 0 or limit == "0":
                return (f"{greeting}{label} is not included in your "
                        f"{member['product'].title()} product.")
            return f"{greeting}{label} has no annual limit."

        return (f"{greeting}Your annual limit for {label.lower()} is "
                f"${limit:.0f}. You have used ${used:.0f} so far. "
                f"That leaves ${remaining:.0f} remaining this year.\n\n"
                f"To see the full breakdown, log into medibank.com.au/oshc "
                f"or call 1800 887 283.")

    if cat == "ambulance":
        limit = member.get("ambulance_limit", 0)
        greeting = f"Hi {name}. " if name else ""
        if _clean_money(limit) >= 1:
            return (f"{greeting}Ambulance is covered on your "
                    f"{member['product'].title()} OSHC. "
                    f"No annual limit applies.")
        return (f"{greeting}Ambulance is not included in your "
                f"{member['product'].title()} product.")

    # Hypothetical deduction
    spent = _extract_amount(question) if question else None
    if spent is not None:
        target_cat = cat or "medicine"
        used = member.get(f"{target_cat}_used", 0)
        limit = member.get(f"{target_cat}_limit", 0)
        remaining = member.get(f"{target_cat}_remaining", 0)
        label = CATEGORY_LABELS.get(target_cat, target_cat)
        if isinstance(limit, (int, float)) and limit > 0:
            after = max(0, remaining - spent)
            greeting = f"Hi {name}. " if name else ""
            return (
                f"{greeting}Your annual limit for {label.lower()} is "
                f"${limit:.0f}. You have used ${used:.0f} so far, "
                f"leaving ${remaining:.0f} remaining.\n\n"
                f"If you spend another ${spent:.0f}, you would have "
                f"${after:.0f} left.\n\n"
                f"Note: this is based on our records. Your actual "
                f"balance may differ if recent claims have not been "
                f"processed yet."
            )

        # General balance question, no specific category detected
    lines = []
    if name:
        lines.append(f"Hi {name}.")
    lines.append(f"Your {member['product'].title()} OSHC runs until "
                 f"{member['cover_end']}.")
    lines.append("")
    med_used = member.get("medical_used", 0)
    lines.append(f"Doctor visits: no annual limit. "
                 f"Used ${med_used:.0f} so far.")
    for cat_key, label in [("medicine", "Prescription medicines"),
                           ("psych", "Psychology and counselling")]:
        used = member.get(f"{cat_key}_used", 0)
        limit = member.get(f"{cat_key}_limit", 0)
        remaining = member.get(f"{cat_key}_remaining", 0)
        if isinstance(limit, str):
            continue
        if limit == 0:
            lines.append(f"{label}: not included.")
            continue
        lines.append(f"{label}: ${remaining:.0f} remaining "
                     f"out of ${limit:.0f}.")
    lines.append("")
    lines.append("Log into medibank.com.au/oshc or call 1800 887 283 "
                 "for the full breakdown.")
    return "\n".join(lines)
