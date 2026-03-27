# Recommendation Logic

## Input Requirements
- origin_city: string
- budget: low | medium | high
- duration: int (days)
- travel_style: adventure | cultural | relaxation | balanced
- weather_preference: cold | warm | tropical | any

## Weather Integration
1. Call OpenWeatherMap for candidate destinations
2. Score each destination: weather_match_score (0-10)
3. Pass scores to LLM as context, not as decision-maker

## Scoring Priority
1. Budget feasibility (hard filter — exclude impossibles)
2. Duration fit (e.g., don't recommend Tokyo for 2 days)
3. Weather match score
4. Travel style alignment

## Output Schema (strict)
{
  "recommendations": [
    {
      "rank": 1,
      "destination": "Bali",
      "country": "Indonesia",
      "reason": "Warm beaches and temples perfect for relaxed 5-day escapes",
      "weather_score": 9,
      "budget_fit": "medium"
    }
  ]
}

## Guardrails
- Maximum 5 recommendations always
- Minimum reason length: 8 words
- Maximum reason length: 20 words
- If weather API fails: proceed without score, log warning