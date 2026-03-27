"""
backend/state/session_state.py — AI Travel Agent
==================================================

Defines the single shared state schema used throughout the LangGraph pipeline.

All graph nodes receive and return a TravelState dict — it is the single source
of truth for the entire run.  No globals, no side-channels.

Public API
----------
    TravelState        — TypedDict schema
    create_initial_state(user_input: dict) -> TravelState
"""

from __future__ import annotations

from typing import TypedDict


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------
class TravelState(TypedDict):
    """Complete state for one travel-planning session."""

    # Raw input collected from the user (CLI or API)
    user_input: dict

    # Validated and normalised travel preferences (set by input_node)
    parsed_preferences: dict

    # Weather scores keyed by destination name (set by input_node)
    weather_data: dict

    # List of 5 ranked destination dicts (set by recommendation_node)
    recommendations: list

    # Name of the destination chosen by the user (set by the caller after interrupt)
    selected_destination: str

    # Full itinerary dict (set by planning_node)
    itinerary: dict

    # Human-readable error message from the most-recently-failed node (or "")
    error: str

    # Name of the node that most-recently completed (for progress tracking)
    current_step: str


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_initial_state(user_input: dict) -> TravelState:
    """
    Return a fresh TravelState initialised from *user_input*.

    All other fields start empty so each node can tell at a glance
    whether earlier work has been done.

    Parameters
    ----------
    user_input : dict
        Raw preferences collected from the user.
        Expected keys: origin_city, budget, duration,
                       travel_style, weather_preference.

    Returns
    -------
    TravelState
    """
    return TravelState(
        user_input=user_input,
        parsed_preferences={},
        weather_data={},
        recommendations=[],
        selected_destination="",
        itinerary={},
        error="",
        current_step="init",
    )
