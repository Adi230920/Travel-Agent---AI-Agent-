"""
backend/tools/weather_tool.py — Weather scoring tool for the AI Travel Agent.

Public API
----------
    get_weather_score(destination: str, preference: str) -> dict

Returns a dict with keys:
    destination    (str)   — echoed back as-is
    temp_celsius   (float) — current temperature
    condition      (str)   — short OpenWeatherMap condition string ("Clear", "Rain", …)
    weather_score  (int)   — 0-10 match score against the user's preference
    error          (str)   — only present when the API call failed

On any failure the function returns a safe fallback (score=5) rather than
raising, so the rest of the pipeline is never blocked by a weather API issue.
"""

from __future__ import annotations

import logging
import sys
import os

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenWeatherMap endpoint
# ---------------------------------------------------------------------------
_OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
_REQUEST_TIMEOUT = 8  # seconds

# ---------------------------------------------------------------------------
# Scoring tables
# ---------------------------------------------------------------------------
# Each preference maps to a scoring function: f(temp_celsius, condition) -> int (0-10)

def _score_warm(temp: float, condition: str) -> int:
    """User wants warm weather — ideally >25 °C and sunny/clear."""
    if temp >= 30:
        base = 10
    elif temp >= 25:
        base = 9
    elif temp >= 20:
        base = 7
    elif temp >= 15:
        base = 5
    elif temp >= 10:
        base = 3
    else:
        base = 1

    # Bonus/penalty for condition
    cond = condition.lower()
    if any(k in cond for k in ("clear", "sunny")):
        base = min(10, base + 1)
    elif any(k in cond for k in ("rain", "storm", "thunder", "drizzle")):
        base = max(0, base - 2)
    elif "snow" in cond:
        base = max(0, base - 3)

    return base


def _score_cold(temp: float, condition: str) -> int:
    """User wants cold weather — ideally <15 °C."""
    if temp <= 0:
        base = 10
    elif temp <= 5:
        base = 9
    elif temp <= 10:
        base = 8
    elif temp <= 15:
        base = 6
    elif temp <= 20:
        base = 4
    elif temp <= 25:
        base = 2
    else:
        base = 1

    # Bonus for snow/overcast (classic cold feel)
    cond = condition.lower()
    if "snow" in cond:
        base = min(10, base + 1)
    elif any(k in cond for k in ("clear", "sunny")) and temp > 15:
        base = max(0, base - 1)

    return base


def _score_tropical(temp: float, condition: str) -> int:
    """User wants tropical weather — hot + humid, rain is acceptable."""
    if temp >= 28:
        base = 10
    elif temp >= 24:
        base = 8
    elif temp >= 20:
        base = 5
    elif temp >= 15:
        base = 3
    else:
        base = 1

    cond = condition.lower()
    # Tropical showers are fine; heavy storms less so
    if any(k in cond for k in ("thunder", "storm")):
        base = max(0, base - 2)
    elif "clear" in cond and temp >= 28:
        base = min(10, base + 1)

    return base


def _score_any(_temp: float, _condition: str) -> int:
    """User has no preference — neutral score for everyone."""
    return 7


_SCORERS = {
    "warm": _score_warm,
    "cold": _score_cold,
    "tropical": _score_tropical,
    "any": _score_any,
}

# ---------------------------------------------------------------------------
# Fallback response
# ---------------------------------------------------------------------------
def _fallback(destination: str, reason: str) -> dict:
    logger.warning("weather_tool: returning fallback for %r — %s", destination, reason)
    return {
        "destination": destination,
        "temp_celsius": None,
        "condition": None,
        "weather_score": 5,
        "error": "API unavailable",
    }


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------
def get_weather_score(destination: str, preference: str) -> dict:
    """
    Fetch current weather for *destination* and return a scored dict.

    Parameters
    ----------
    destination : str
        City name (e.g. "Paris", "Tokyo").
    preference  : str
        One of "warm" | "cold" | "tropical" | "any".

    Returns
    -------
    dict with keys: destination, temp_celsius, condition, weather_score
    (plus 'error' key when the API call failed).
    """
    # Normalise preference; default to "any" for unknown values
    preference = (preference or "any").strip().lower()
    score_fn = _SCORERS.get(preference, _score_any)

    # Retrieve API key at call-time so the module can be imported even when
    # config vars aren't set (e.g. during unit tests with mocks).
    try:
        # Prefer config module; fall back to raw env var so the tool can be
        # used standalone without the full backend being configured.
        api_key = os.environ.get("WEATHER_API_KEY", "")
        if not api_key:
            from backend.config import WEATHER_API_KEY  # type: ignore
            api_key = WEATHER_API_KEY
    except Exception:
        api_key = os.environ.get("WEATHER_API_KEY", "")

    if not api_key:
        return _fallback(destination, "WEATHER_API_KEY not set")

    # ------------------------------------------------------------------ #
    # Call OpenWeatherMap current-weather endpoint                         #
    # ------------------------------------------------------------------ #
    params = {
        "q": destination,
        "appid": api_key,
        "units": "metric",   # °C
    }

    try:
        response = requests.get(_OWM_URL, params=params, timeout=_REQUEST_TIMEOUT)
    except requests.exceptions.ConnectionError:
        return _fallback(destination, "network unreachable")
    except requests.exceptions.Timeout:
        return _fallback(destination, "request timed out")
    except requests.exceptions.RequestException as exc:
        return _fallback(destination, str(exc))

    # ------------------------------------------------------------------ #
    # Parse response                                                       #
    # ------------------------------------------------------------------ #
    if response.status_code == 401:
        return _fallback(destination, "invalid API key (401)")
    if response.status_code == 404:
        return _fallback(destination, f"destination not found (404): {destination!r}")
    if not response.ok:
        return _fallback(
            destination,
            f"HTTP {response.status_code}: {response.text[:120]}",
        )

    try:
        data = response.json()
        temp_celsius: float = round(data["main"]["temp"], 1)
        condition: str = data["weather"][0]["main"]          # e.g. "Clear", "Rain"
        condition_desc: str = data["weather"][0]["description"]  # e.g. "light rain"
    except (KeyError, IndexError, ValueError) as exc:
        return _fallback(destination, f"unexpected response shape: {exc}")

    weather_score: int = score_fn(temp_celsius, condition)

    logger.info(
        "weather_tool: %s → %.1f°C, %s (%s), preference=%s, score=%d",
        destination, temp_celsius, condition, condition_desc, preference, weather_score,
    )

    return {
        "destination": destination,
        "temp_celsius": temp_celsius,
        "condition": f"{condition} ({condition_desc})",
        "weather_score": weather_score,
    }


# ---------------------------------------------------------------------------
# Quick manual test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    # Allow running from the project root:  python backend/tools/weather_tool.py
    # Make sure .env is loaded so WEATHER_API_KEY is available.
    _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_project_root, ".env"))

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    test_cases = [
        ("Paris", "warm"),
        ("Reykjavik", "cold"),
        ("Bali", "tropical"),
        ("New York", "any"),
    ]

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║       🌤  Weather Tool — Manual Test Run         ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    for city, pref in test_cases:
        result = get_weather_score(city, pref)
        print(f"  [{pref.upper():8s}] {city}")
        print(json.dumps(result, indent=6))
        print()
