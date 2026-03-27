"""
backend/prompts/recommendation_prompt.py — AI Travel Agent
===========================================================

Centralised prompt strings for the Recommendation Agent.

All prompt construction lives here so that:
  1. Prompts can be reviewed/tested independently of the agent logic.
  2. Edge-case tightening happens in one place.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# System prompt  (forces JSON-only, no prose)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a travel planning expert. You respond ONLY with valid JSON. "
    "No preamble, no explanation, no markdown code blocks. Raw JSON only. "
    "Do NOT wrap the output in ```json``` fences."
)

# ---------------------------------------------------------------------------
# Output schema  (shown inside the user prompt)
# ---------------------------------------------------------------------------
OUTPUT_SCHEMA = """\
{
  "recommendations": [
    {
      "rank": 1,
      "destination": "City Name",
      "country": "Country Name",
      "reason": "Eight to twenty words explaining why this fits the traveller",
      "weather_score": 7,
      "budget_fit": "medium"
    }
  ]
}"""

# ---------------------------------------------------------------------------
# Few-shot example
# ---------------------------------------------------------------------------
FEW_SHOT_EXAMPLE = """\
Example output (follow this schema exactly — 5 items, valid JSON):
{
  "recommendations": [
    {
      "rank": 1,
      "destination": "Bali",
      "country": "Indonesia",
      "reason": "Warm beaches and temples perfect for relaxed 5-day escapes",
      "weather_score": 9,
      "budget_fit": "medium"
    },
    {
      "rank": 2,
      "destination": "Chiang Mai",
      "country": "Thailand",
      "reason": "Affordable cultural hub ideal for budget-conscious adventurers",
      "weather_score": 8,
      "budget_fit": "low"
    }
  ]
}"""


def build_user_prompt(preferences: dict, weather_data: dict) -> str:
    """
    Build the user prompt following the
    [ROLE] → [CONTEXT] → [CONSTRAINTS] → [OUTPUT FORMAT] → [EXAMPLE]
    pattern from docs/prompt_design.md.
    """
    origin       = preferences.get("origin_city", "unknown")
    budget       = preferences.get("budget", "medium")
    duration     = preferences.get("duration", 7)
    travel_style = preferences.get("travel_style", "balanced")
    weather_pref = preferences.get("weather_preference", "any")

    # Summarise weather context (may be empty dict)
    if weather_data:
        weather_lines = []
        for dest, w in weather_data.items():
            score = w.get("weather_score", 5)
            temp  = w.get("temp_celsius")
            cond  = w.get("condition", "unknown")
            temp_str = f"{temp}°C" if temp is not None else "n/a"
            weather_lines.append(
                f"  - {dest}: {temp_str}, {cond}, weather_score={score}/10"
            )
        weather_context = "Weather data for candidate destinations:\n" + "\n".join(weather_lines)
    else:
        weather_context = "Weather data: unavailable (use weather_score=5 as neutral)."

    prompt = f"""\
[ROLE]
You are an expert travel planner recommending destinations to a traveller.

[CONTEXT]
- Travelling FROM: {origin}
- Budget level: {budget}
- Trip duration: {duration} day(s)
- Travel style: {travel_style}
- Weather preference: {weather_pref}

{weather_context}

[CONSTRAINTS]
- Return EXACTLY 5 destinations ranked 1–5. No more, no fewer.
- Each destination must be a real city or place name.
- Do NOT recommend the origin city ({origin}) or any city in the same country if origin is well-known.
- budget_fit must be one of: "low", "medium", "high" — matching the traveller's budget "{budget}".
- reason field: minimum 8 words, maximum 20 words. Plain text, no markdown.
- weather_score: integer 0–10, reflecting how well the destination's weather matches the preference "{weather_pref}".
- If weather data is provided above, use those scores; otherwise estimate.
- Duration fit: only recommend places feasible in {duration} day(s).
- rank must be an integer from 1 to 5, with 1 being the best match.

[OUTPUT FORMAT]
Return ONLY this JSON structure, nothing else. No text before the opening {{ or after the closing }}.
{OUTPUT_SCHEMA}

[EXAMPLE]
{FEW_SHOT_EXAMPLE}

Now generate EXACTLY 5 recommendations for the traveller described above. Begin your response with {{ and end with }}.\
"""
    return prompt
