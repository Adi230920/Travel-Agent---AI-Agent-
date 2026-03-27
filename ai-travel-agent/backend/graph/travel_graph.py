"""
backend/graph/travel_graph.py — AI Travel Agent
================================================

Assembles the LangGraph pipeline.

Graph topology
--------------
    input_node → recommendation_node → [interrupt_before=planning_node]
               → planning_node

All LLM logic is delegated to the agent modules.  This file contains NO
direct LLM calls.  State is the single source of truth — no globals.

Public API
----------
    build_graph() -> CompiledGraph
        Returns a compiled LangGraph ready to invoke or stream.

Node responsibilities
---------------------
    input_node
        • Calls input_agent.parse_inputs() to validate user_input
        • Fetches weather data for seed destinations
        • Writes parsed_preferences, weather_data, current_step

    recommendation_node
        • Calls recommendation_agent.get_recommendations()
        • Writes recommendations, current_step

    selection_node  ← exists only to surface current_step="selection"
        • No LLM work; marks the pause point so the front-end / CLI
          knows the graph is waiting for the user's choice.
        • Writes current_step="selection"
        • The *actual* pause is interrupt_before=["planning_node"]

    planning_node
        • Reads selected_destination (supplied by the caller after resume)
        • Calls planning_agent.generate_itinerary()
        • Writes itinerary, current_step
"""

from __future__ import annotations

import logging
import sys
import os

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so backend / cli imports work
# regardless of from where the module is imported.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from langgraph.graph import StateGraph, END

from backend.state.session_state import TravelState
from backend.agents import input_agent, recommendation_agent, planning_agent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed destinations for weather pre-fetch (same set as the legacy CLI)
# ---------------------------------------------------------------------------
_SEED_DESTINATIONS = [
    "Paris", "Tokyo", "Bali", "Reykjavik", "New York",
    "Cape Town", "Bangkok", "Patagonia", "Queenstown", "Santorini",
]


# ===========================================================================
# Node definitions  (each follows the Node Pattern from langgraph_implementation.md)
# ===========================================================================

def input_node(state: TravelState) -> TravelState:
    """Validate user input and pre-fetch weather data."""
    try:
        # 1. Parse & validate
        parsed = input_agent.parse_inputs(state["user_input"])
        state["parsed_preferences"] = parsed

        # 2. Fetch weather for seed destinations
        from backend.tools.weather_tool import get_weather_score

        weather_pref = parsed.get("weather_preference", "any")
        weather_data: dict = {}
        for dest in _SEED_DESTINATIONS:
            try:
                weather_data[dest] = get_weather_score(dest, weather_pref)
            except Exception as we:
                logger.warning("input_node: weather fetch failed for %s: %s", dest, we)
                weather_data[dest] = {"weather_score": 5, "temp_celsius": None, "condition": "unavailable"}

        state["weather_data"] = weather_data

        # 4. Mark step
        state["current_step"] = "input_complete"
        logger.info("input_node: completed — preferences parsed, weather fetched.")

    except Exception as e:
        state["error"] = f"input_node failed: {e}"
        state["current_step"] = "input_error"
        logger.error("input_node: %s", e)

    return state


def recommendation_node(state: TravelState) -> TravelState:
    """Call the recommendation agent to produce 5 ranked destinations."""
    try:
        # 1. Extract
        preferences = state["parsed_preferences"]
        weather_data = state["weather_data"]

        # 2. Delegate to agent
        recommendations = recommendation_agent.get_recommendations(preferences, weather_data)

        # 3. Update state
        state["recommendations"] = recommendations

        # 4. Mark step
        state["current_step"] = "recommendations_ready"
        logger.info(
            "recommendation_node: %d recommendations received.", len(recommendations)
        )

    except Exception as e:
        state["error"] = f"recommendation_node failed: {e}"
        state["current_step"] = "recommendation_error"
        logger.error("recommendation_node: %s", e)

    return state


def selection_node(state: TravelState) -> TravelState:
    """
    Transition node that marks the graph as waiting for user selection.

    No LLM work happens here.  The real pause is enforced by
    interrupt_before=["planning_node"] on the compiled graph.
    This node exists so current_step accurately reflects 'awaiting_selection'
    for progress tracking.
    """
    try:
        # 1. Validate recommendations are present
        recs = state.get("recommendations", [])
        if not recs:
            raise ValueError("No recommendations available for selection.")

        # 3. Update state — signal to caller that selection is needed
        state["current_step"] = "awaiting_selection"
        logger.info("selection_node: graph paused, awaiting destination selection.")

    except Exception as e:
        state["error"] = f"selection_node failed: {e}"
        state["current_step"] = "selection_error"
        logger.error("selection_node: %s", e)

    return state


def planning_node(state: TravelState) -> TravelState:
    """Generate a detailed day-by-day itinerary for the selected destination."""
    try:
        # 1. Extract
        selected = state.get("selected_destination", "").strip()
        if not selected:
            raise ValueError(
                "selected_destination is empty. "
                "Supply it via graph.invoke(state, config) after the interrupt."
            )

        preferences = state["parsed_preferences"]

        # Build the subset of preferences that planning_agent expects
        planning_prefs = {
            "country":      _resolve_country(selected, state.get("recommendations", [])),
            "budget":       preferences.get("budget", "medium"),
            "duration":     preferences.get("duration", 5),
            "travel_style": preferences.get("travel_style", "balanced"),
        }

        # 2. Delegate to agent
        itinerary_data = planning_agent.generate_itinerary(selected, planning_prefs)

        # 3. Update state
        state["itinerary"] = itinerary_data

        # 4. Mark step
        state["current_step"] = "itinerary_ready"
        logger.info("planning_node: itinerary generated for '%s'.", selected)

    except Exception as e:
        state["error"] = f"planning_node failed: {e}"
        state["current_step"] = "planning_error"
        logger.error("planning_node: %s", e)

    return state


# ---------------------------------------------------------------------------
# Helper: try to look up the country for the selected destination
# from the recommendations list (so planning_agent gets full context).
# ---------------------------------------------------------------------------
def _resolve_country(destination: str, recommendations: list) -> str:
    """Return the country for *destination* from the recommendations list, or ''."""
    for rec in recommendations:
        if rec.get("destination", "").lower() == destination.lower():
            return rec.get("country", "")
    return ""


# ===========================================================================
# Graph factory
# ===========================================================================

def build_graph(checkpointer=None):
    """
    Build and compile the travel-planning LangGraph.

    Topology
    --------
        input_node → recommendation_node → selection_node → planning_node → END

    The graph pauses before planning_node so the caller can inject
    ``selected_destination`` via the resume mechanism.

    Parameters
    ----------
    checkpointer : BaseCheckpointSaver, optional
        A LangGraph checkpointer (e.g. MemorySaver) for session persistence.

    Returns
    -------
    CompiledGraph (langgraph.graph.CompiledStateGraph)
    """
    builder = StateGraph(TravelState)

    # Register nodes
    builder.add_node("input_node",          input_node)
    builder.add_node("recommendation_node", recommendation_node)
    builder.add_node("selection_node",      selection_node)
    builder.add_node("planning_node",       planning_node)

    # Wire edges
    builder.set_entry_point("input_node")
    builder.add_edge("input_node",          "recommendation_node")
    builder.add_edge("recommendation_node", "selection_node")
    builder.add_edge("selection_node",      "planning_node")
    builder.add_edge("planning_node",       END)

    # Compile with interrupt BEFORE planning_node so the caller can inject the
    # selected destination before the final node executes.
    graph = builder.compile(
        interrupt_before=["planning_node"],
        checkpointer=checkpointer
    )

    logger.info("build_graph: travel graph compiled successfully.")
    return graph
