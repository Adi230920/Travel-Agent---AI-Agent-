"""
backend/agents/recommendation_agent.py — AI Travel Agent
=========================================================

Calls an LLM (Groq or OpenRouter, selected by MODEL_PROVIDER in .env) to
produce exactly 5 ranked travel destination recommendations.

Public API
----------
    get_recommendations(preferences: dict, weather_data: dict) -> list[dict]

    preferences keys expected:
        origin_city, budget, duration, travel_style, weather_preference

    weather_data keys expected (dict of destination → weather result dicts,
    may be empty when weather API is unavailable):
        { "Paris": {"temp_celsius": 18.5, "condition": "Clear", "weather_score": 7}, ... }

    Returns a list of 5 dicts matching the schema in recommendation_logic.md:
        [{"rank": 1, "destination": "...", "country": "...",
          "reason": "...", "weather_score": 0-10, "budget_fit": "..."}, ...]
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load config lazily so the module is importable in isolation (tests, etc.)
# ---------------------------------------------------------------------------
def _get_config() -> dict[str, str]:
    """Return a dict with all required config values."""
    # Try the backend config module first
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
        "model":    "nvidia/nemotron-3-super-120b-a12b:free",
        "key_env":  "OPENROUTER_API_KEY",
    },
}

# ---------------------------------------------------------------------------
# Prompt construction — delegated to backend.prompts.recommendation_prompt
# ---------------------------------------------------------------------------
try:
    from backend.prompts.recommendation_prompt import (
        SYSTEM_PROMPT as _SYSTEM_PROMPT,
        build_user_prompt as _build_user_prompt,
    )
except ImportError:
    # Fallback for standalone execution (python -m backend.agents.recommendation_agent)
    _SYSTEM_PROMPT = (
        "You are a travel planning expert. You respond ONLY with valid JSON. "
        "No preamble, no explanation, no markdown code blocks. Raw JSON only. "
        "Do NOT wrap the output in ```json``` fences."
    )
    _build_user_prompt = None  # type: ignore


# ---------------------------------------------------------------------------
# LLM call (provider-agnostic via OpenAI-compatible REST)
# ---------------------------------------------------------------------------
def _call_llm(prompt: str, cfg: dict) -> str:
    """
    Send a chat-completion request to the configured provider.
    Returns the raw text content of the assistant message.
    Raises RuntimeError on HTTP or network failure.
    """
    provider = cfg["MODEL_PROVIDER"]
    if provider not in _PROVIDER_DEFAULTS:
        logger.warning("Unknown MODEL_PROVIDER %r — falling back to 'groq'.", provider)
        provider = "groq"

    defaults  = _PROVIDER_DEFAULTS[provider]
    base_url  = defaults["base_url"]
    model     = cfg["MODEL_NAME"] or defaults["model"]
    api_key   = cfg[defaults["key_env"]]

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
        "model": model,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    }

    logger.info("recommendation_agent: calling %s with model=%s", provider, model)

    try:
        response = requests.post(base_url, headers=headers, json=payload, timeout=60)
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
    Try to extract a JSON object from *text*.
    Strips markdown fences if present, then parses.
    Raises ValueError if no valid JSON is found.
    """
    # Strip common markdown code-fences
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    # Find outermost { … }
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in LLM output:\n{text[:400]}")
    return json.loads(cleaned[start:end])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Recommendation validation helper
# ---------------------------------------------------------------------------
_REQUIRED_REC_KEYS = {"rank", "destination", "country", "reason", "weather_score", "budget_fit"}


def _validate_recommendations(recs: list) -> list[dict]:
    """
    Validate and normalise recommendations list.
    Ensures exactly 5 dicts each containing all required keys.
    """
    if not isinstance(recs, list) or len(recs) == 0:
        raise ValueError("'recommendations' key is missing or empty.")

    # Truncate to 5 if LLM returned more; raise if fewer
    if len(recs) > 5:
        logger.warning("recommendation_agent: LLM returned %d recs — truncating to 5.", len(recs))
        recs = recs[:5]
    elif len(recs) < 5:
        raise ValueError(
            f"Expected exactly 5 recommendations, got {len(recs)}."
        )

    for i, rec in enumerate(recs):
        if not isinstance(rec, dict):
            raise ValueError(f"Recommendation #{i+1} is not a dict.")
        missing = _REQUIRED_REC_KEYS - rec.keys()
        if missing:
            raise ValueError(
                f"Recommendation #{i+1} missing keys: {missing}"
            )
        # Normalise types
        rec["rank"] = int(rec["rank"])  if rec.get("rank") is not None else i + 1
        rec["weather_score"] = int(rec["weather_score"]) if rec.get("weather_score") is not None else 5
        rec["weather_score"] = max(0, min(10, rec["weather_score"]))  # clamp 0-10

    return recs


def get_recommendations(preferences: dict, weather_data: dict) -> list[dict]:
    """
    Call the LLM to produce 5 ranked travel recommendations.

    Parameters
    ----------
    preferences : dict
        Keys: origin_city, budget, duration, travel_style, weather_preference.
    weather_data : dict
        Weather results keyed by destination name (may be empty).

    Returns
    -------
    list[dict]  — exactly 5 recommendation dicts.

    Raises
    ------
    RuntimeError  if the LLM call fails or returns unparseable JSON after retry.
    """
    cfg    = _get_config()
    prompt = _build_user_prompt(preferences, weather_data)

    for attempt in (1, 2):
        logger.info("recommendation_agent: attempt %d/2", attempt)
        raw = _call_llm(prompt, cfg)
        logger.debug("recommendation_agent: raw response:\n%s", raw)

        try:
            parsed = _extract_json(raw)
            recs   = parsed["recommendations"]
            recs   = _validate_recommendations(recs)
            logger.info(
                "recommendation_agent: parsed %d recommendations on attempt %d.",
                len(recs), attempt,
            )
            return recs
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.warning(
                "recommendation_agent: JSON parse failed on attempt %d: %s", attempt, exc
            )
            if attempt == 2:
                raise RuntimeError(
                    f"Failed to parse LLM response after 2 attempts.\n"
                    f"Last raw output:\n{raw[:600]}"
                ) from exc
            # Back off briefly before retry
            time.sleep(1.5)

    # Should never reach here
    raise RuntimeError("Unexpected state in get_recommendations.")  # pragma: no cover


# ---------------------------------------------------------------------------
# Quick manual test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import pprint

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s %(message)s",
    )

    test_preferences = {
        "origin_city":        "Mumbai",
        "budget":             "medium",
        "duration":           5,
        "travel_style":       "adventure",
        "weather_preference": "cold",
    }

    # Minimal weather data (simulating weather_tool output)
    test_weather = {
        "Paris":    {"temp_celsius": 14.2, "condition": "Cloudy",  "weather_score": 7},
        "Iceland":  {"temp_celsius":  2.1, "condition": "Snow",    "weather_score": 9},
        "Patagonia":{"temp_celsius":  8.0, "condition": "Windy",   "weather_score": 8},
    }

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║   🤖  Recommendation Agent — Manual Test Run         ║")
    print("╚══════════════════════════════════════════════════════╝\n")
    print("Preferences:")
    pprint.pprint(test_preferences, indent=4)
    print()

    try:
        results = get_recommendations(test_preferences, test_weather)
        print(f"\n✅  Got {len(results)} recommendations:\n")
        for rec in results:
            print(f"  #{rec.get('rank', '?')}  {rec.get('destination')}, {rec.get('country')}")
            print(f"       Reason      : {rec.get('reason')}")
            print(f"       Weather score: {rec.get('weather_score')}/10")
            print(f"       Budget fit   : {rec.get('budget_fit')}")
            print()
    except RuntimeError as err:
        print(f"\n❌  Error: {err}")
        sys.exit(1)
