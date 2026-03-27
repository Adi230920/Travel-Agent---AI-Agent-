"""
backend/agents/input_agent.py — AI Travel Agent
================================================

Responsible for validating and normalising the raw ``user_input`` dict that
arrives at the graph.  This is a *pure* function — no LLM, no I/O.

Public API
----------
    parse_inputs(user_input: dict) -> dict

    Returns a ``parsed_preferences`` dict with validated, normalised fields
    that every downstream agent can safely consume.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid values
# ---------------------------------------------------------------------------
_VALID_BUDGETS          = {"low", "medium", "high"}
_VALID_TRAVEL_STYLES    = {"adventure", "cultural", "relaxation", "balanced"}
_VALID_WEATHER_PREFS    = {"cold", "warm", "tropical", "any"}
_MIN_DURATION           = 1
_MAX_DURATION           = 30


def parse_inputs(user_input: dict) -> dict:
    """
    Validate and normalise raw user input.

    Parameters
    ----------
    user_input : dict
        Expected keys: origin_city, budget, duration, travel_style,
        weather_preference.

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
        errors.append("'origin_city' is required and must be a non-empty string.")

    # --- budget ---
    budget = str(user_input.get("budget", "")).strip().lower()
    if budget not in _VALID_BUDGETS:
        # Normalise unknown/negative budget to "low" per testing_cases.md
        logger.warning("input_agent: invalid budget %r — normalised to 'low'.", budget)
        budget = "low"

    # --- duration ---
    raw_duration = user_input.get("duration")
    try:
        duration = int(raw_duration)
        if not (_MIN_DURATION <= duration <= _MAX_DURATION):
            errors.append(
                f"'duration' must be between {_MIN_DURATION} and {_MAX_DURATION} days, "
                f"got: {duration}"
            )
    except (TypeError, ValueError):
        errors.append(
            f"'duration' must be an integer, got: {raw_duration!r}"
        )
        duration = 5  # placeholder so the rest of validation can continue

    # --- travel_style ---
    travel_style = str(user_input.get("travel_style", "")).strip().lower()
    if travel_style not in _VALID_TRAVEL_STYLES:
        # Default missing/unknown travel_style to "balanced" per testing_cases.md
        logger.warning("input_agent: invalid travel_style %r — defaulting to 'balanced'.", travel_style)
        travel_style = "balanced"

    # --- weather_preference ---
    weather_preference = str(user_input.get("weather_preference", "")).strip().lower()
    if weather_preference not in _VALID_WEATHER_PREFS:
        errors.append(
            f"'weather_preference' must be one of {sorted(_VALID_WEATHER_PREFS)}, "
            f"got: {weather_preference!r}"
        )

    if errors:
        raise ValueError(
            "Input validation failed:\n" + "\n".join(f"  • {e}" for e in errors)
        )

    parsed = {
        "origin_city":        origin_city,
        "budget":             budget,
        "duration":           duration,
        "travel_style":       travel_style,
        "weather_preference": weather_preference,
    }

    logger.info("input_agent: parsed inputs successfully — %s", parsed)
    return parsed
