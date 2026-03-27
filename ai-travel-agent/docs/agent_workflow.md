# Agent Workflow

## Agent 1 — InputAgent
Role: Parse and validate user preferences
Input: Raw form data (city, budget, duration, travel style)
Output: Structured preference object
Rules:
  - Normalize budget to low/medium/high
  - Validate duration (1-30 days only)
  - Default travel style to "balanced" if not provided
  - NEVER proceed if city_of_origin is missing

## Agent 2 — RecommendationAgent
Role: Suggest top 5 destinations with one-line reasoning
Input: Preference object + weather data
Output: List of 5 destinations [{name, country, reason, weather_score}]
Rules:
  - Reason MUST be ≤ 20 words
  - Avoid destinations unreachable within budget
  - Weather score must factor in user's preference
  - Output must be valid JSON, no extra text

## Agent 3 — PlanningAgent
Role: Generate day-wise itinerary for selected destination
Input: Selected destination + original preferences
Output: {day: [morning, afternoon, evening]} for each day
Rules:
  - Each activity ≤ 15 words
  - Budget-appropriate activities only
  - Include 1 local food recommendation per day
  - No generic filler (no "visit the city", be specific)

## State Transitions
InputAgent → RecommendationAgent → [USER SELECTS] → PlanningAgent
If any agent fails: return error with which step failed