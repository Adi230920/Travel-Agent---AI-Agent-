# UI Flow Design

## Screen States (single page, state-driven)
State 1: INPUT FORM (default)
State 2: LOADING (agent thinking)
State 3: RECOMMENDATIONS (5 cards shown)
State 4: LOADING (itinerary generating)
State 5: ITINERARY (day-wise display)

## Component Map
- InputForm: city, budget slider, duration, travel style dropdown
- LoadingSpinner: with step label ("Finding destinations...")
- RecommendationCard: destination name, country, reason, weather badge
- DestinationSelector: click to select from 5 cards
- ItineraryView: accordion per day, morning/afternoon/evening slots
- ErrorBanner: shown if backend returns error

## API Contract (what JS expects)
POST /api/plan → { session_id, recommendations: [...] }
POST /api/itinerary → { session_id, destination } → { itinerary: {...} }

## UX Rules
- Only one screen visible at a time (hide others with CSS class)
- Show loading state immediately on form submit (don't wait for response)
- Recommendation cards: hover highlight, click to select (no submit button)
- Itinerary: day accordion, collapsed by default, expand on click
- Never show raw JSON to user under any condition

## Style Constraints
- Font: Inter or system-ui
- Colors: White background, #1a1a2e dark text, #0066FF accent
- Cards: subtle shadow, 8px border-radius, clean padding
- No heavy animations — transitions max 200ms
- Mobile responsiveness: not required for V1