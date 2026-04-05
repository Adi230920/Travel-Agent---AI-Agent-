"""
config.py — Centralised configuration loader.

Loads environment variables from .env using python-dotenv and
exposes them as module-level constants.  Raises ValueError on startup
if any required key is absent so the application fails fast with a
clear error message rather than at the point of use.
"""

import os
from dotenv import load_dotenv

# Load .env from the project root (two levels above this file)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

# ---------------------------------------------------------------------------
# Required keys — all must be present in .env (or the real environment).
# ---------------------------------------------------------------------------
_REQUIRED_KEYS = [
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "WEATHER_API_KEY",
    "RAPIDAPI_KEY",
    "UNSPLASH_ACCESS_KEY",
    "MODEL_PROVIDER",
]

_missing = [key for key in _REQUIRED_KEYS if not os.getenv(key)]
if _missing:
    raise ValueError(
        f"Missing required environment variable(s): {', '.join(_missing)}. "
        "Please add them to your .env file (see .env.example)."
    )

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY: str = os.environ["OPENROUTER_API_KEY"]
GROQ_API_KEY: str = os.environ["GROQ_API_KEY"]
WEATHER_API_KEY: str = os.environ["WEATHER_API_KEY"]
RAPIDAPI_KEY: str = os.environ["RAPIDAPI_KEY"]
UNSPLASH_ACCESS_KEY: str = os.environ["UNSPLASH_ACCESS_KEY"]
MODEL_PROVIDER: str = os.environ["MODEL_PROVIDER"].strip().lower()  # "groq" or "openrouter"
MODEL_NAME: str = os.getenv("MODEL_NAME", "").strip()  # optional override
