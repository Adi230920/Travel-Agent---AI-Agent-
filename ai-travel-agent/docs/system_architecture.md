# System Architecture

## Stack
- Frontend: HTML + CSS + JS (vanilla, no frameworks)
- Backend: Python (FastAPI)
- LLM: Openrouter or Groq (free tier)
- Weather: OpenWeatherMap API (free tier)
- Orchestration: LangGraph
- State: In-memory session dict (no DB in V1)

## Request Flow
1. User fills form → JS sends POST to /api/plan
2. FastAPI receives input → triggers LangGraph graph
3. Graph runs: InputAgent → RecommendationAgent → [wait] → PlanningAgent
4. Response streamed or returned as JSON
5. Frontend renders structured output

## API Endpoints
POST /api/plan         ← full pipeline trigger
POST /api/itinerary    ← itinerary only (after selection)
GET  /api/health       ← sanity check

## Environment Variables
OPENROUTER_API_KEY=
GROQ_API_KEY=
WEATHER_API_KEY=
MODEL_NAME=openai/gpt-3.5-turbo   ← or groq/llama3

## Critical Rules
- Never expose API keys to frontend
- All LLM calls happen server-side only
- Session state lives in backend memory, keyed by session_id