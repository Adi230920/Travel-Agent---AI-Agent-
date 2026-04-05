# RapidAPI Tool Integration Analysis

This document analyzes the issues encountered with the flight and restaurant data fetching tools (implemented via RapidAPI/TripAdvisor) and provides suggestions for improvement.

## Identified Issues

### 1. Critical Backend Bug: Missing JSON Import
The most immediate issue is a Python `NameError` in the backend code. 

- **File**: `backend/graph/travel_graph.py`
- **Error**: `name 'json' is not defined`
- **Detail**: The `planning_node` attempts to use `json.dumps()` to format restaurant data for the AI planning agent. Because `import json` is missing at the top of this file, the entire data-fetching block fails silently (caught by a generic `try-except`) and continues with an empty context.

### 2. Destination Specificity (IATA Code Resolution)
The flight search tool relies on **IATA codes** (3-letter airport codes like BOM, CDG, LHR). 

- **Scenario**: In your last run, "Hallstatt" was selected as the destination.
- **Problem**: Hallstatt is a small village and does not have an IATA airport code. The tool tries to resolve "Hallstatt" into an airport code, and when it fails (or returns a non-IATA string like "Upper Austria"), the flight search function either returns no results or is skipped.
- **Scenario**: "Germany" was provided as an origin.
- **Problem**: "Germany" is a country, not a city. The tool expects a specific departure city to find the correct origin airport.

### 3. API Key & Rate Limits
If the `RAPIDAPI_KEY` is invalid, missing, or has reached its free-tier limit, the tool enters a "Mock Mode" or returns empty results.

---

## Suggested Fixes

### Phase 1: Technical Repairs (Immediate)
1.  **Add `import json`**: Fix the `NameError` in `backend/graph/travel_graph.py`.
2.  **Harden IATA Lookup**: Update `backend/tools/rapidapi_tool.py` to only trigger a flight search if a valid 3-letter uppercase IATA code is found. If no code is found, it should log a clearer warning.

### Phase 2: UX Improvements
1.  **Origin City Guidance**: Update the frontend or input agent to nudge users to provide a **City** (e.g., "Berlin" instead of "Germany").
2.  **Nearest Airport Fallback**: (Future improvement) If a small village like Hallstatt is selected, the system could automatically look up the nearest major city with an airport (e.g., "Salzburg").

---

## How to Test the Fix
Once the `json` import is fixed, try planning a trip between two major cities (e.g., **"London" to "Paris"**). These cities have unambiguous IATA codes (LHR/LCY and CDG/ORY), which will allow the tool to fetch real flight and restaurant data successfully.
