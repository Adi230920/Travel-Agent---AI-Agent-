"""
backend/agents/input_agent.py — AI Travel Agent
================================================

Responsible for validating and normalising the raw ``user_input`` dict that
arrives at the graph.  This is a *pure* function — no LLM, no I/O.
"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid values
# ---------------------------------------------------------------------------
_VALID_BUDGETS          = {"low", "medium", "high"}
_VALID_TRAVEL_STYLES    = {"adventure", "cultural", "relaxation", "balanced"}
_VALID_WEATHER_PREFS    = {"cold", "warm", "tropical", "any"}
_VALID_TRAVEL_TYPES     = {"domestic", "international"}
_VALID_PACES            = {"relaxed", "balanced", "fast"}
_MIN_DURATION           = 1
_MAX_DURATION           = 30


def parse_inputs(user_input: dict) -> dict:
    """
    Validate and normalise raw user input.

    Parameters
    ----------
    user_input : dict
        Expected keys: origin_city, travel_type, departure_date, return_date,
        budget, travel_style, travel_pace, weather_preference.

    Returns
    -------
    dict
        Parsed and validated preferences.

    Raises
    ------
    ValueError
        If any required field is missing or has an invalid value.
    """
    errors: list[str] = []

    # --- origin_city ---
    origin_city = str(user_input.get("origin_city", "")).strip()
    if not origin_city:
        errors.append("'origin_city' is required.")

    # --- travel_type ---
    travel_type = str(user_input.get("travel_type", "international")).strip().lower()
    if travel_type not in _VALID_TRAVEL_TYPES:
        travel_type = "international"

    # --- budget ---
    budget = str(user_input.get("budget", "")).strip().lower()
    if budget not in _VALID_BUDGETS:
        budget = "low"

    # --- dates & duration ---
    dep_date_str = user_input.get("departure_date")
    ret_date_str = user_input.get("return_date")
    duration = 5 # default

    if dep_date_str and ret_date_str:
        try:
            dep_date = datetime.strptime(dep_date_str, "%Y-%m-%d")
            ret_date = datetime.strptime(ret_date_str, "%Y-%m-%d")
            
            if ret_date < dep_date:
                errors.append("Return date cannot be before departure date.")
            else:
                duration = (ret_date - dep_date).days + 1
                if not (_MIN_DURATION <= duration <= _MAX_DURATION):
                    errors.append(f"Trip duration ({duration} days) must be between {_MIN_DURATION} and {_MAX_DURATION}.")
        except ValueError:
            errors.append("Dates must be in YYYY-MM-DD format.")
    else:
        # Fallback to manual duration if dates missing
        raw_duration = user_input.get("duration", 5)
        try:
            duration = int(raw_duration)
        except (TypeError, ValueError):
            duration = 5

    # --- travel_style ---
    travel_style = str(user_input.get("travel_style", "")).strip().lower()
    if travel_style not in _VALID_TRAVEL_STYLES:
        travel_style = "balanced"

    # --- travel_pace ---
    travel_pace = str(user_input.get("travel_pace", "balanced")).strip().lower()
    if travel_pace not in _VALID_PACES:
        travel_pace = "balanced"

    # --- weather_preference ---
    weather_preference = str(user_input.get("weather_preference", "")).strip().lower()
    if weather_preference not in _VALID_WEATHER_PREFS:
        weather_preference = "any"

    if errors:
        raise ValueError("Input validation failed:\n" + "\n".join(f"  • {e}" for e in errors))

    parsed = {
        "origin_city":        origin_city,
        "travel_type":        travel_type,
        "departure_date":     dep_date_str,
        "return_date":        ret_date_str,
        "duration":           duration,
        "travel_style":       travel_style,
        "travel_pace":        travel_pace,
        "budget":             budget,
        "weather_preference": weather_preference,
    }

    logger.info("input_agent: parsed inputs successfully — %s", parsed)
    return parsed
