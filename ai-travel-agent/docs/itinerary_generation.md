# Itinerary Generation

## Input Requirements
- destination: string
- country: string
- duration: int (days)
- budget: low | medium | high
- travel_style: string

## Output Schema (strict)
{
  "destination": "Bali, Indonesia",
  "duration": 5,
  "itinerary": {
    "Day 1": {
      "morning": "Visit Tanah Lot temple at sunrise",
      "afternoon": "Explore Ubud Monkey Forest",
      "evening": "Dinner at local warung in Ubud",
      "tip": "Hire a scooter for ₹500/day for easy travel"
    }
  }
}

## Content Rules
- Each activity: ≤ 15 words, specific (no generic filler)
- One local food tip per day (mandatory)
- One practical tip per day (transport, timing, cost)
- Budget-appropriate activities:
    low: free sites, street food, public transport
    medium: mix of paid attractions, local restaurants
    high: premium experiences, curated dining

## Never Generate
- Vague activities ("explore the city", "see the sights")
- Expensive activities for low-budget users
- More than 4 activities per day slot