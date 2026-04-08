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
      "food_spots": [
        {"name": "<Restaurant Name>", "type": "Lunch/Dinner", "rating": "<e.g. 4.5/5 or N/A>", "reason": "<6 words>"},
        {"name": "<Restaurant Name>", "type": "Lunch/Dinner", "rating": "<e.g. 4.5/5 or N/A>", "reason": "<6 words>"}
      ],
      "tip":       "<practical tip: transport / cost / timing, ≤15 words>"
    }
  }
}"""

# ---------------------------------------------------------------------------
# Few-shot example
# ---------------------------------------------------------------------------
FEW_SHOT_EXAMPLE = """\
Example — 2-day medium-budget trip to Bali, Indonesia (Relaxed pace):
{
  "destination": "Bali, Indonesia",
  "duration": 2,
  "itinerary": {
    "Day 1": {
      "morning":   "Watch sunrise at Tanah Lot temple on the coast",
      "afternoon": "Explore Ubud Monkey Forest and Sacred Art Market",
      "evening":   "Attend Kecak fire dance at Uluwatu temple",
      "food_spots": [
        {"name": "Ibu Oka", "type": "Lunch", "rating": "4.8/5", "reason": "Famous suckling pig (Babi Guling)"},
        {"name": "Potato Head", "type": "Dinner", "rating": "4.6/5", "reason": "Beachfront dining and sunset cocktails"}
      ],
      "tip":       "Rent a scooter for ~50,000 IDR/day for mobility"
    },
    "Day 2": {
      "morning":   "Hike Mount Batur for volcanic sunrise views",
      "afternoon": "Soak in natural hot springs at Toya Devasya",
      "evening":   "Relax at Seminyak Beach with live jazz music",
      "food_spots": [
        {"name": "Sisterfields", "type": "Lunch", "rating": "4.5/5", "reason": "Modern Australian-style cafe hub"},
        {"name": "La Lucciola", "type": "Dinner", "rating": "4.2/5", "reason": "Elegant beachfront Italian dining"}
      ],
      "tip":       "Book the Batur guide in advance (2 AM start)"
    }
  }
}"""


def build_user_prompt(destination: str, preferences: dict, restaurant_context: str = "") -> str:
    """
    Build the user prompt following the
    [ROLE] → [CONTEXT] → [CONSTRAINTS] → [OUTPUT FORMAT] → [EXAMPLE]
    pattern from docs/prompt_design.md.
    """
    country      = preferences.get("country", "")
    duration     = int(preferences.get("duration", 5))
    budget       = preferences.get("budget", "medium")
    travel_style = preferences.get("travel_style", "balanced")
    travel_pace  = preferences.get("travel_pace", "balanced")

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
- Travel pace  : {travel_pace}
- Real TripAdvisor Dining Data: {restaurant_context if restaurant_context else "Not available (use high-quality local estimates)"}

[CONSTRAINTS]
- Generate EXACTLY {duration} day(s) with labels: {day_labels}. No more, no fewer.
- Each day MUST contain EXACTLY these 5 keys: "morning", "afternoon", "evening", "food_spots", "tip".
- **Food Spots constraint**: Include exactly 2 food spots per day (one lunch, one dinner) with a rating if available in the context (otherwise "N/A").
- **Real-World Data**: If "Real TripAdvisor Dining Data" is provided above, you MUST prioritize selecting restaurants from that list for your "food_spots" entries and include their respective ratings.
- Each activity field (morning / afternoon / evening): ≤ 15 words, specific and actionable.
- **Pace Constraint**: Adjust the intensity of activities to a "{travel_pace}" pace.
- "tip" field: one practical tip about transport, timing, or cost (≤ 15 words).
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


def build_retry_prompt(destination: str, preferences: dict, restaurant_context: str = "") -> str:
    """
    Stricter prompt used on the second attempt when JSON parsing fails.
    """
    base = build_user_prompt(destination, preferences, restaurant_context)
    return (
        "CRITICAL: Your previous response could not be parsed as JSON. "
        "You MUST return ONLY a raw JSON object. "
        "Do NOT include markdown code fences (```), explanations, or any text "
        "before the opening { or after the closing }. "
        "Begin your response with { and end with }.\n\n"
        + base
    )
