"""Project-wide settings. Import this before soccerdata so its cache lands inside the project."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

os.environ.setdefault("SOCCERDATA_DIR", str(DATA_DIR / "cache"))

CURRENT_SEASON = "2627"  # soccerdata format: 2026/27
