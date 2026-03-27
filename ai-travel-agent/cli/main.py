"""
cli/main.py — AI Travel Agent · CLI entry point  (Phase 3 — LangGraph)
========================================================================

Drives the LangGraph pipeline end-to-end from the terminal.

Workflow
--------
  1. Collect travel preferences from the terminal (unchanged)
  2. Build initial state and invoke the graph
     → input_node    : validate inputs + fetch weather
     → recommendation_node : ask LLM for 5 destinations
     → selection_node      : graph pauses (interrupt_before=planning_node)
  3. Show recommendations and ask the user to pick one
  4. Resume the graph with selected_destination injected into state
     → planning_node : generate full itinerary
  5. Display the itinerary

Usage
-----
    python cli/main.py
"""

from __future__ import annotations

import json
import logging
import sys
import os

# Make sure the project root is on the path so backend imports work.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Logging — keep it quiet at the CLI level
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.WARNING, format="%(levelname)s  %(message)s")

# ---------------------------------------------------------------------------
# Helpers — input prompts (identical to Phase 2)
# ---------------------------------------------------------------------------

def _prompt(label: str, default: str | None = None) -> str:
    """Display a prompt and return non-empty stripped input."""
    suffix = f" [{default}]" if default is not None else ""
    while True:
        value = input(f"  {label}{suffix}: ").strip()
        if not value and default is not None:
            return default
        if value:
            return value
        print("    ✗  This field is required. Please enter a value.")


def _prompt_choice(label: str, choices: list[str], default: str | None = None) -> str:
    """Prompt the user to pick from a fixed list of choices."""
    choices_str = "/".join(choices)
    suffix = f" [{default}]" if default is not None else ""
    while True:
        value = input(f"  {label} ({choices_str}){suffix}: ").strip().lower()
        if not value and default is not None:
            return default
        if value in choices:
            return value
        print(f"    ✗  Invalid choice. Please enter one of: {choices_str}")


def _prompt_int(label: str, min_val: int, max_val: int) -> int:
    """Prompt for an integer within [min_val, max_val]."""
    while True:
        raw = input(f"  {label} ({min_val}–{max_val}): ").strip()
        if not raw:
            print("    ✗  This field is required. Please enter a number.")
            continue
        try:
            value = int(raw)
        except ValueError:
            print(f"    ✗  Please enter a whole number between {min_val} and {max_val}.")
            continue
        if min_val <= value <= max_val:
            return value
        print(f"    ✗  Value must be between {min_val} and {max_val}.")


# ---------------------------------------------------------------------------
# Input collection
# ---------------------------------------------------------------------------

def collect_inputs() -> dict:
    """Interactively collect and validate travel planning inputs."""
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║          🌍  AI Travel Agent — Trip Planner          ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()
    print("Please answer the following questions to plan your trip.")
    print("Press Enter to accept the default value shown in [brackets].")
    print()

    origin_city        = _prompt("Origin city (where are you travelling FROM?)")
    budget             = _prompt_choice("Budget", ["low", "medium", "high"], default="medium")
    duration           = _prompt_int("Trip duration in days", 1, 30)
    travel_style       = _prompt_choice(
                             "Travel style",
                             ["adventure", "cultural", "relaxation", "balanced"],
                         )
    weather_preference = _prompt_choice(
                             "Weather preference",
                             ["cold", "warm", "tropical", "any"],
                         )

    return {
        "origin_city":        origin_city,
        "budget":             budget,
        "duration":           duration,
        "travel_style":       travel_style,
        "weather_preference": weather_preference,
    }


# ---------------------------------------------------------------------------
# Display helpers  (identical to Phase 2)
# ---------------------------------------------------------------------------
_DIVIDER = "─" * 58

def _print_preferences(prefs: dict) -> None:
    print()
    print(_DIVIDER)
    print("  ✅  Collected inputs:")
    print(_DIVIDER)
    formatted = json.dumps(prefs, indent=4)
    for line in formatted.splitlines():
        print(f"  {line}")
    print(_DIVIDER)


def _print_recommendations(recs: list[dict]) -> None:
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║              🏆  Top 5 Destinations                  ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()
    for rec in recs:
        rank        = rec.get("rank", "?")
        destination = rec.get("destination", "Unknown")
        country     = rec.get("country", "")
        reason      = rec.get("reason", "")
        score       = rec.get("weather_score", "n/a")
        budget_fit  = rec.get("budget_fit", "n/a")

        bar_len = int(score) if isinstance(score, (int, float)) else 5
        bar = "█" * bar_len + "░" * (10 - bar_len)

        print(f"  #{rank}  {destination}, {country}")
        print(f"       {reason}")
        print(f"       Weather : [{bar}] {score}/10   Budget fit: {budget_fit}")
        print()


def _print_itinerary(itinerary_data: dict) -> None:
    """Pretty-print the full itinerary from planning_agent."""
    destination = itinerary_data.get("destination", "Unknown")
    duration    = itinerary_data.get("duration", "?")
    itinerary   = itinerary_data.get("itinerary", {})

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print(f"║  🗺️  {destination} — {duration}-Day Itinerary".ljust(55) + "║")
    print("╚══════════════════════════════════════════════════════╝")

    for day_label, slots in itinerary.items():
        print()
        print(f"  ┌─────────────────────────────────────────────────────")
        print(f"  │  📅  {day_label}")
        print(f"  └─────────────────────────────────────────────────────")
        print(f"   🌅  Morning   : {slots.get('morning', 'n/a')}")
        print(f"   ☀️   Afternoon : {slots.get('afternoon', 'n/a')}")
        print(f"   🌙  Evening   : {slots.get('evening', 'n/a')}")
        print(f"   💡  Tip       : {slots.get('tip', 'n/a')}")

    print()
    print(_DIVIDER)


def _pick_destination(recommendations: list[dict]) -> dict:
    """
    Ask the user to choose one of the 5 recommended destinations.
    Returns the chosen recommendation dict.
    """
    print()
    print("  " + _DIVIDER)
    choice = _prompt_int("Enter the number of your chosen destination", 1, 5)
    chosen = next(
        (r for r in recommendations if r.get("rank") == choice),
        recommendations[choice - 1],  # fallback: index-based
    )
    print(
        f"\n  ✈️  Great choice! Planning your trip to "
        f"{chosen.get('destination')}, {chosen.get('country')}…"
    )
    return chosen


# ---------------------------------------------------------------------------
# Main — graph-driven flow
# ---------------------------------------------------------------------------

def main() -> None:
    # ── Step 1 : collect inputs ──────────────────────────────────────────
    try:
        user_input = collect_inputs()
    except KeyboardInterrupt:
        print("\n\n  Cancelled by user. Goodbye!")
        sys.exit(0)

    _print_preferences(user_input)

    # ── Step 2 : build initial state and graph ───────────────────────────
    from backend.state.session_state import create_initial_state
    from backend.graph.travel_graph  import build_graph

    state  = create_initial_state(user_input)
    graph  = build_graph()

    # LangGraph needs a thread config for checkpointing / interrupt support.
    config = {"configurable": {"thread_id": "cli-session-1"}}

    # ── Step 3 : run input_node → recommendation_node → selection_node ───
    print()
    print("  ⛅  Fetching weather and generating AI recommendations…", end="", flush=True)

    try:
        # graph.invoke runs until it hits interrupt_before=["planning_node"]
        state = graph.invoke(state, config)
        print(" done")
    except KeyboardInterrupt:
        print("\n\n  Cancelled by user. Goodbye!")
        sys.exit(0)
    except Exception as exc:
        print(f"\n\n  ❌  Graph error during recommendations: {exc}")
        sys.exit(1)

    # Surface any error reported inside the graph nodes
    if state.get("error"):
        print(f"\n  ⚠️  Warning from graph: {state['error']}")

    recommendations = state.get("recommendations", [])
    if not recommendations:
        print("\n  ❌  No recommendations returned. Cannot continue.")
        sys.exit(1)

    # ── Step 4 : display recommendations + ask user to pick ─────────────
    _print_recommendations(recommendations)

    try:
        chosen = _pick_destination(recommendations)
    except KeyboardInterrupt:
        print("\n\n  Cancelled by user. Goodbye!")
        sys.exit(0)

    # ── Step 5 : inject selection and resume graph ───────────────────────
    print()
    print("  🤖  Generating your personalised itinerary…", end="", flush=True)

    # Update state with the user's selection, then resume past the interrupt.
    state["selected_destination"] = chosen["destination"]

    try:
        state = graph.invoke(state, config)
        print(" done")
    except KeyboardInterrupt:
        print("\n\n  Cancelled by user. Goodbye!")
        sys.exit(0)
    except Exception as exc:
        print(f"\n\n  ❌  Graph error during planning: {exc}")
        sys.exit(1)

    if state.get("error"):
        print(f"\n  ⚠️  Warning from planning node: {state['error']}")

    itinerary_data = state.get("itinerary", {})
    if not itinerary_data:
        print("\n  ❌  No itinerary generated. Cannot display.")
        sys.exit(1)

    # ── Step 6 : display itinerary ───────────────────────────────────────
    _print_itinerary(itinerary_data)


if __name__ == "__main__":
    main()
