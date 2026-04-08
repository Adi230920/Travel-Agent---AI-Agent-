"""
backend/agents/planning_agent.py — AI Travel Agent
====================================================

Calls an LLM (Groq or OpenRouter) to produce a detailed day-by-day travel
itinerary for a given destination.

Follows:
  - Output schema from docs/itinerary_generation.md
  - Prompt design rules from docs/prompt_design.md
  - Temperature 0.5 (structured output, per prompt_design.md §Temperature)

Public API
----------
    generate_itinerary(destination: str, preferences: dict) -> dict

    preferences keys expected:
        country       – country of destination (str)
        budget        – "low" | "medium" | "high"
        duration      – trip length in days (int)
        travel_style  – "adventure" | "cultural" | "relaxation" | "balanced"

    Returns a dict:
    {
        "destination": "City, Country",
        "duration": <int>,
        "itinerary": {
            "Day 1": {
                "morning":   "...",
                "afternoon": "...",
                "evening":   "...",
                "tip":       "..."
            },
            ...
        }
    }
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load config lazily (same pattern as recommendation_agent)
# ---------------------------------------------------------------------------
def _get_config() -> dict[str, str]:
    """Return a dict with all required config values from .env."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        ))))
        from dotenv import load_dotenv
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        load_dotenv(os.path.join(_root, ".env"))
    except Exception:
        pass

    return {
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
        "GROQ_API_KEY":       os.getenv("GROQ_API_KEY", ""),
        "MODEL_PROVIDER":     os.getenv("MODEL_PROVIDER", "groq").strip().lower(),
        "MODEL_NAME":         os.getenv("MODEL_NAME", "").strip(),
    }


# ---------------------------------------------------------------------------
# Provider defaults
# ---------------------------------------------------------------------------
_PROVIDER_DEFAULTS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "model":    "llama-3.1-8b-instant",
        "key_env":  "GROQ_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "model":    "arcee-ai/trinity-large-preview:free",
        "key_env":  "OPENROUTER_API_KEY",
    },
}

# ---------------------------------------------------------------------------
# Prompts — delegated to backend.prompts.itinerary_prompt
# ---------------------------------------------------------------------------
try:
    from backend.prompts.itinerary_prompt import (
        SYSTEM_PROMPT as _SYSTEM_PROMPT,
        build_user_prompt as _build_user_prompt,
        build_retry_prompt as _build_retry_prompt,
    )
except ImportError:
    # Fallback for standalone execution
    _SYSTEM_PROMPT = (
        "You are a professional travel itinerary planner. "
        "You respond ONLY with valid JSON. "
        "No preamble, no explanation, no markdown code blocks. Raw JSON only. "
        "Do NOT wrap the output in ```json``` fences."
    )
    _build_user_prompt = None   # type: ignore
    _build_retry_prompt = None  # type: ignore


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------
def _call_llm(prompt: str, cfg: dict, temperature: float = 0.5) -> str:
    """
    Send a chat-completion request to the configured provider.
    Returns raw assistant message text.
    Raises RuntimeError on HTTP / network failure.
    """
    provider = cfg["MODEL_PROVIDER"]
    if provider not in _PROVIDER_DEFAULTS:
        logger.warning("Unknown MODEL_PROVIDER %r — falling back to 'groq'.", provider)
        provider = "groq"

    defaults = _PROVIDER_DEFAULTS[provider]
    base_url = defaults["base_url"]
    model    = cfg["MODEL_NAME"] or defaults["model"]
    api_key  = cfg[defaults["key_env"]]

    if not api_key:
        raise RuntimeError(
            f"No API key found for provider '{provider}'. "
            f"Set {defaults['key_env']} in your .env file."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://ai-travel-agent"
        headers["X-Title"]      = "AI Travel Agent"

    payload = {
        "model":       model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    }

    logger.info(
        "planning_agent: calling %s model=%s temp=%.1f",
        provider, model, temperature,
    )

    try:
        response = requests.post(base_url, headers=headers, json=payload, timeout=90)
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Network error calling LLM: {exc}") from exc

    if not response.ok:
        raise RuntimeError(
            f"LLM API returned HTTP {response.status_code}: {response.text[:300]}"
        )

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected LLM response shape: {exc}\n{data}") from exc

    return content


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------
def _extract_json(text: str) -> dict:
    """
    Extract a JSON object from raw LLM text.
    Strips markdown fences if present, then parses.
    Raises ValueError if no valid JSON found.
    """
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in LLM output:\n{text[:400]}")
    return json.loads(cleaned[start:end])


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _validate_itinerary(data: dict, expected_days: int) -> None:
    """
    Validate the parsed itinerary dict has the correct structure and
    exactly `expected_days` day entries with all required slots.

    Raises ValueError with a descriptive message on failure.
    """
    if "itinerary" not in data:
        raise ValueError("Missing 'itinerary' key in LLM response.")

    itinerary = data["itinerary"]
    if not isinstance(itinerary, dict):
        raise ValueError(
            f"'itinerary' must be a dict, got {type(itinerary).__name__}."
        )

    actual_days = len(itinerary)
    if actual_days != expected_days:
        raise ValueError(
            f"Expected {expected_days} day(s) in itinerary, got {actual_days}. "
            f"Keys present: {list(itinerary.keys())}"
        )

    required_slots = {"morning", "afternoon", "evening", "food_spots", "tip"}
    for day_label, slots in itinerary.items():
        if not isinstance(slots, dict):
            raise ValueError(
                f"{day_label}: expected a dict of slots, got {type(slots).__name__}."
            )
        missing = required_slots - slots.keys()
        if missing:
            raise ValueError(
                f"{day_label}: missing required slot(s): {missing}."
            )

    logger.info(
        "planning_agent: validation passed — %d day(s) with all required slots.",
        actual_days,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_itinerary(destination: str, preferences: dict, restaurant_context: str = "") -> dict:
    """
    Generate a detailed day-by-day travel itinerary for *destination*.

    Parameters
    ----------
    destination : str
        Name of the destination city / place.
    preferences : dict
        Keys: country, budget, duration, travel_style.

    Returns
    -------
    dict matching the schema in docs/itinerary_generation.md.

    Raises
    ------
    RuntimeError
        If the LLM call fails or returns invalid JSON after retry.
    """
    cfg           = _get_config()
    expected_days = int(preferences.get("duration", 5))

    prompts = {
        1: _build_user_prompt(destination, preferences, restaurant_context),
        2: _build_retry_prompt(destination, preferences, restaurant_context),
    }

    for attempt in (1, 2):
        logger.info("planning_agent: attempt %d/2 for '%s'", attempt, destination)

        try:
            raw = _call_llm(prompts[attempt], cfg, temperature=0.5)
        except RuntimeError:
            raise  # Network / auth failures are not retried

        logger.debug("planning_agent: raw response attempt %d:\n%s", attempt, raw)

        try:
            parsed = _extract_json(raw)
            _validate_itinerary(parsed, expected_days)

            # Fill in any missing top-level fields the LLM may have omitted
            if "destination" not in parsed:
                country = preferences.get("country", "")
                parsed["destination"] = (
                    f"{destination}, {country}" if country else destination
                )
            if "duration" not in parsed:
                parsed["duration"] = expected_days

            logger.info(
                "planning_agent: itinerary generated on attempt %d.", attempt
            )
            return parsed

        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.warning(
                "planning_agent: parse/validation failed on attempt %d: %s",
                attempt, exc,
            )
            if attempt == 2:
                raise RuntimeError(
                    f"Failed to generate a valid itinerary after 2 attempts.\n"
                    f"Last error: {exc}\n"
                    f"Last raw output:\n{raw[:600]}"
                ) from exc
            time.sleep(1.5)  # brief back-off before retry

    raise RuntimeError("Unexpected state in generate_itinerary.")  # pragma: no cover


# ---------------------------------------------------------------------------
# Quick manual test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import pprint

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s %(message)s",
    )

    test_destination = "Kyoto"
    test_preferences = {
        "country":      "Japan",
        "budget":       "medium",
        "duration":     3,
        "travel_style": "cultural",
    }

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║   🗺️  Planning Agent — Manual Test Run               ║")
    print("╚══════════════════════════════════════════════════════╝\n")
    print(f"Destination : {test_destination}")
    print("Preferences :")
    pprint.pprint(test_preferences, indent=4)
    print()

    try:
        result = generate_itinerary(test_destination, test_preferences)
        print(f"\n✅  {result.get('destination')} — {result.get('duration')}-day itinerary:\n")
        for day, slots in result["itinerary"].items():
            print(f"  {day}:")
            print(f"    🌅 Morning   : {slots.get('morning')}")
            print(f"    ☀️  Afternoon : {slots.get('afternoon')}")
            print(f"    🌙 Evening   : {slots.get('evening')}")
            print(f"    💡 Tip       : {slots.get('tip')}")
            print()
    except RuntimeError as err:
        print(f"\n❌  Error: {err}")
        sys.exit(1)
