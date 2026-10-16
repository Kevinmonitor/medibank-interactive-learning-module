"""
Optional Google Sheet backend for the interaction log.

When a service account and a sheet URL are configured in st.secrets, every
logged interaction and prompt is appended to the sheet, and the insights
pages read from the sheet. Without that configuration the app silently uses
the local SQLite file, so nothing breaks in development or offline.

Sheet layout: two worksheets (tabs), named exactly "interactions" and
"prompt_log", each with a header row matching the columns below.

secrets needed (in .streamlit/secrets.toml, or Streamlit Cloud secrets):

    SHEET_URL = "https://docs.google.com/spreadsheets/d/.../edit"

    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
    client_email = "...@...iam.gserviceaccount.com"
    ... (the rest of the downloaded JSON key)
"""
import sqlite3

LAST_ERROR = None   # set by the append helpers when a Sheet write fails

INTERACTION_COLS = ["ts", "topic", "confidence", "page", "source",
                    "routed_to_nurse"]
PROMPT_COLS = ["ts", "raw", "corrected", "expanded", "topic", "confidence",
               "product", "was_corrected", "correction_count", "synonym_hit",
               "word_count", "routed"]


from functools import lru_cache


@lru_cache(maxsize=1)
def _file_secrets():
    """Read Muhammad/.streamlit/secrets.toml directly. Streamlit only loads
    secrets next to the app that was launched, so when the chatbot is embedded
    in Tala (launched from Tala/) st.secrets never sees these. Reading the file
    by its own location fixes it for every entry point."""
    try:
        import tomllib
        from app.paths import ROOT
        p = ROOT / ".streamlit" / "secrets.toml"
        if p.exists():
            with open(p, "rb") as f:
                return tomllib.load(f)
    except Exception:
        pass
    return {}


def _get(name, default=None):
    """Prefer this project's own .streamlit/secrets.toml, read by absolute
    path, so a leftover GLOBAL ~/.streamlit/secrets.toml (a different project)
    can't shadow it when the app is launched from another folder. Fall back to
    st.secrets for Streamlit Cloud, where the local file is not present."""
    fs = _file_secrets()
    if name in fs:
        return fs[name]
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return default


def sheet_enabled():
    """True only when both the sheet URL and the service account are set."""
    try:
        return bool(_get("SHEET_URL")) and bool(_get("gcp_service_account"))
    except Exception:
        return False


def _book():
    """The gspread Spreadsheet, or None if anything is missing or wrong."""
    if not sheet_enabled():
        return None
    try:
        import gspread
        gc = gspread.service_account_from_dict(dict(_get("gcp_service_account")))
        return gc.open_by_url(_get("SHEET_URL"))
    except Exception:
        return None


def _ws(name):
    book = _book()
    if book is None:
        return None
    try:
        return book.worksheet(name)
    except Exception:
        return None


# ------------------------------------------------------------------ writes
def append_interaction(ts, topic, confidence, page, source, routed):
    global LAST_ERROR
    ws = _ws("interactions")
    if ws is None:
        LAST_ERROR = "worksheet 'interactions' not reachable"
        return
    try:
        ws.append_row([ts, topic, confidence, page, source, int(routed)],
                      value_input_option="RAW")
        LAST_ERROR = None
    except Exception as e:
        LAST_ERROR = f"{type(e).__name__}: {e}"


def append_prompt(row):
    """row is a dict keyed by PROMPT_COLS."""
    global LAST_ERROR
    ws = _ws("prompt_log")
    if ws is None:
        LAST_ERROR = "worksheet 'prompt_log' not reachable"
        return
    try:
        ws.append_row([row.get(c, "") for c in PROMPT_COLS],
                      value_input_option="RAW")
        LAST_ERROR = None
    except Exception as e:
        LAST_ERROR = f"{type(e).__name__}: {e}"


# ------------------------------------------------------------------ reads
def _records(name):
    ws = _ws(name)
    if ws is None:
        return None
    try:
        return ws.get_all_records()   # list of dicts, keyed by the header row
    except Exception:
        return None


_FLOAT_COLS = {"confidence"}
_INT_COLS = {"routed_to_nurse", "was_corrected", "correction_count",
             "synonym_hit", "word_count", "routed"}


def _num(v):
    """Parse a number from a cell, tolerating a comma decimal separator
    (some Google Sheet locales write 0,026 instead of 0.026) and blanks."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return None


def _coerce(col, v):
    if col in _FLOAT_COLS:
        return _num(v)
    if col in _INT_COLS:
        n = _num(v)
        return int(n) if n is not None else None
    return v


def connection(local_factory):
    """Return a sqlite3 connection the insights pages can query with their
    existing SQL. When the sheet is configured, build an in-memory database
    from it so the pages read live cloud data; otherwise return the local
    file connection unchanged."""
    if not sheet_enabled():
        return local_factory()

    inter = _records("interactions")
    prompts = _records("prompt_log")
    if inter is None and prompts is None:
        # Sheet configured but unreachable: fall back rather than crash.
        return local_factory()

    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE interactions (ts TEXT, topic TEXT, "
                "confidence REAL, page TEXT, source TEXT, "
                "routed_to_nurse INTEGER)")
    con.execute("CREATE TABLE prompt_log (ts TEXT, raw TEXT, corrected TEXT, "
                "expanded TEXT, topic TEXT, confidence REAL, product TEXT, "
                "was_corrected INTEGER, correction_count INTEGER, "
                "synonym_hit INTEGER, word_count INTEGER, routed INTEGER)")
    if inter:
        con.executemany(
            "INSERT INTO interactions VALUES (?,?,?,?,?,?)",
            [[_coerce(c, r.get(c)) for c in INTERACTION_COLS] for r in inter])
    if prompts:
        con.executemany(
            "INSERT INTO prompt_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [[_coerce(c, r.get(c)) for c in PROMPT_COLS] for r in prompts])
    con.commit()
    return con
