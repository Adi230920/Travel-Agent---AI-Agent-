"""
backend/prompts/itinerary_prompt.py — AI Travel Agent
======================================================

Centralised prompt strings for the Planning Agent.

All prompt construction lives here so that:
  1. Prompts can be reviewed/tested independently of the agent logic.
  2. Edge-case tightening happens in one place.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# System prompt  (forces JSON-only, no prose)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a professional travel itinerary planner. "
    "You respond ONLY with valid JSON. "
    "No preamble, no explanation, no markdown code blocks. Raw JSON only. "
    "Do NOT wrap the output in ```json``` fences."
)

# ---------------------------------------------------------------------------
# Output schema  (shown inside the user prompt)
# ---------------------------------------------------------------------------
OUTPUT_SCHEMA = """\
{
  "destination": "<City>, <Country>",
  "duration": <int: number of days>,
  "itinerary": {
    "Day 1": {
      "morning":   "<specific activity, ≤15 words>",
      "afternoon": "<specific activity, ≤15 words>",
      "evening":   "<specific activity, ≤15 words>",
      "tip":       "<practical tip: transport / cost / timing, ≤15 words>"
    }
  }
}"""

# ---------------------------------------------------------------------------
# Few-shot example
# ---------------------------------------------------------------------------
FEW_SHOT_EXAMPLE = """\
Example — 2-day medium-budget trip to Bali, Indonesia:
{
  "destination": "Bali, Indonesia",
  "duration": 2,
  "itinerary": {
    "Day 1": {
      "morning":   "Watch sunrise at Tanah Lot temple on the western coast",
      "afternoon": "Explore Ubud Monkey Forest and Sacred Art Market stalls",
      "evening":   "Dinner at a local warung in Ubud, try nasi goreng",
      "tip":       "Rent a scooter for ~50,000 IDR/day for easy mobility"
    },
    "Day 2": {
      "morning":   "Hike Mount Batur for panoramic volcanic sunrise views",
      "afternoon": "Soak in natural hot springs at Toya Devasya resort",
      "evening":   "Kecak fire dance at Uluwatu temple on the clifftop",
      "tip":       "Book the Batur hike guide in advance, starts at 2 AM"
    }
  }
}"""


def build_user_prompt(destination: str, preferences: dict) -> str:
    """
    Build the user prompt following the
    [ROLE] → [CONTEXT] → [CONSTRAINTS] → [OUTPUT FORMAT] → [EXAMPLE]
    pattern from docs/prompt_design.md.
    """
    country      = preferences.get("country", "")
    duration     = int(preferences.get("duration", 5))
    budget       = preferences.get("budget", "medium")
    travel_style = preferences.get("travel_style", "balanced")

    location_str = f"{destination}, {country}" if country else destination

    budget_guide = {
        "low":    "free attractions, street food, public transport only",
        "medium": "mix of paid attractions, local restaurants, shared transport",
        "high":   "premium experiences, curated dining, private transport",
    }.get(budget, "mix of paid and free attractions")

    day_labels = ", ".join(f'"Day {i}"' for i in range(1, duration + 1))

    prompt = f"""\
[ROLE]
You are an expert travel itinerary planner building a day-by-day trip plan.

[CONTEXT]
- Destination  : {location_str}
- Duration     : {duration} day(s)
- Budget level : {budget}  ({budget_guide})
- Travel style : {travel_style}

[CONSTRAINTS]
- Generate EXACTLY {duration} day(s) with labels: {day_labels}. No more, no fewer.
- Each day MUST contain EXACTLY these 4 keys: "morning", "afternoon", "evening", "tip".
- Each activity field (morning / afternoon / evening): ≤ 15 words, specific and actionable.
- "tip" field: one practical tip about transport, timing, or cost (≤ 15 words).
- Include at least one local food experience somewhere in each day.
- Only recommend activities appropriate for a {budget} budget.
- NEVER write vague activities like "explore the city" or "see the sights".
- Do NOT add markdown fences, commentary, or text outside the JSON object.

[OUTPUT FORMAT]
Return ONLY this JSON structure (fill in real content for the destination).
No text before the opening {{ or after the closing }}.
{OUTPUT_SCHEMA}

[EXAMPLE]
{FEW_SHOT_EXAMPLE}

Now generate a {duration}-day itinerary for {location_str}. Begin your response with {{ and end with }}.\
"""
    return prompt


def build_retry_prompt(destination: str, preferences: dict) -> str:
    """
    Stricter prompt used on the second attempt when JSON parsing fails.
    """
    base = build_user_prompt(destination, preferences)
    return (
        "CRITICAL: Your previous response could not be parsed as JSON. "
        "You MUST return ONLY a raw JSON object. "
        "Do NOT include markdown code fences (```), explanations, or any text "
        "before the opening { or after the closing }. "
        "Begin your response with { and end with }.\n\n"
        + base
    )
