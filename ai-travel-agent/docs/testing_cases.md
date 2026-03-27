# Testing Cases

## CLI Test Cases (Phase 1)

### Happy Path
Input: Mumbai, medium budget, 5 days, cultural, warm weather
Expected: 5 destinations returned, each with ≤20 word reason, valid JSON

### Edge Cases
- Budget: "low", Duration: 1 day → should still return 5 options
- Travel style not provided → defaults to "balanced"
- Weather API down → recommendations generated without weather score

### Guardrail Tests
- Duration: 0 days → error returned, no LLM call made
- Budget: negative → normalized to "low"
- City of origin: empty → error returned immediately

## Agent Unit Tests
- InputAgent: test normalization of all budget/style variants
- RecommendationAgent: test JSON schema compliance of output
- PlanningAgent: verify no day exceeds 3 activity slots

## Integration Tests
- Full pipeline: input → 5 recommendations → select #2 → itinerary
- Verify session_id persists state between /api/plan and /api/itinerary
- Verify error in RecommendationAgent does not crash PlanningAgent call

## UI Tests (manual)
- Submit form → loading spinner appears within 200ms
- 5 cards render with correct data from API
- Clicking card 3 → sends correct destination to itinerary endpoint
- Itinerary accordion: all days expand/collapse correctly
