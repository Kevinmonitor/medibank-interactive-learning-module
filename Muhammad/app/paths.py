"""
Where the data files live.

The app used to open "data/chunks.json" relative to the folder it was
started from. That works for `streamlit run app/main.py`, but breaks the
moment the chatbot is imported by another app (Tala) that starts from a
different folder. Resolving the path from this file's own location fixes
it in every case.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # .../Muhammad
DATA = ROOT / "data"
