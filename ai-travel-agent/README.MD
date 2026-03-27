# ✈️ AI Travel Agent — VoyagerAI

An AI-powered travel planning application that generates personalised destination recommendations and day-by-day itineraries using LLM agents orchestrated by [LangGraph](https://langchain-ai.github.io/langgraph/).

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![LangGraph](https://img.shields.io/badge/LangGraph-stateful_graph-purple)

---

## 🏗️ Architecture

```
User Input  →  InputAgent (validate)
            →  WeatherTool (score destinations)
            →  RecommendationAgent (LLM → 5 ranked options)
            →  [User selects a destination]
            →  PlanningAgent (LLM → day-by-day itinerary)
```

The pipeline is modelled as a **LangGraph state graph** with an interrupt before the planning node, allowing the user to select a destination before itinerary generation.

### Project Structure

```
ai-travel-agent/
├── backend/
│   ├── agents/
│   │   ├── input_agent.py          # Input validation & normalisation
│   │   ├── recommendation_agent.py # LLM-based destination recommendations
│   │   └── planning_agent.py       # LLM-based itinerary generation
│   ├── graph/
│   │   └── travel_graph.py         # LangGraph pipeline orchestration
│   ├── prompts/
│   │   ├── recommendation_prompt.py # Prompt templates for recommendations
│   │   └── itinerary_prompt.py      # Prompt templates for itineraries
│   ├── state/
│   │   └── session_state.py        # TravelState schema & factory
│   ├── tools/
│   │   └── weather_tool.py         # OpenWeatherMap integration
│   ├── api.py                      # FastAPI REST endpoints
│   └── config.py                   # Environment config loader
├── cli/
│   └── main.py                     # Terminal-based interactive CLI
├── frontend/
│   ├── index.html                  # Single-page app
│   ├── style.css                   # Design system & styles
│   └── app.js                      # Client-side logic
├── docs/                           # Design documents & specs
├── tests/
│   └── test_cases.py               # Test suite
├── .env.example                    # Environment template
├── requirements.txt                # Python dependencies
└── README.md                       # ← You are here
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** installed
- At least one LLM API key: [Groq](https://console.groq.com/) (free) or [OpenRouter](https://openrouter.ai/)
- *(Optional)* [OpenWeatherMap](https://openweathermap.org/api) API key for weather scoring

### 1. Clone & Install

```bash
git clone https://github.com/[your-username]/ai-travel-agent.git
cd ai-travel-agent

pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys:

```env
OPENROUTER_API_KEY=sk-or-v1-...      # Required if MODEL_PROVIDER=openrouter
GROQ_API_KEY=gsk_...                  # Required if MODEL_PROVIDER=groq
WEATHER_API_KEY=your_owm_key_here     # Optional — fallback scores used if missing
MODEL_PROVIDER=groq                   # "groq" or "openrouter"
MODEL_NAME=                           # Optional — override default model
```

### 3. Run the Backend API

```bash
uvicorn backend.api:app --reload
```

The API will start at **http://127.0.0.1:8000**. Verify it's running:

```bash
curl http://127.0.0.1:8000/api/health
# → {"status": "ok"}
```

### 4. Open the Frontend

Open `frontend/index.html` in your browser. The frontend connects to `http://127.0.0.1:8000` automatically when opened locally.

> **Tip:** For the best experience, use a local HTTP server:
> ```bash
> python -m http.server 5500 --directory frontend
> ```
> Then visit **http://localhost:5500**.

### 5. (Alternative) Use the CLI

```bash
python cli/main.py
```

Follow the interactive prompts to plan your trip entirely from the terminal.

---

## 📡 API Endpoints

| Method | Endpoint         | Description                                    |
|--------|------------------|------------------------------------------------|
| GET    | `/api/health`    | Health check                                   |
| POST   | `/api/plan`      | Submit preferences → get 5 recommendations     |
| POST   | `/api/itinerary` | Select a destination → get day-by-day itinerary |

### POST `/api/plan`

**Request:**
```json
{
  "origin_city": "Mumbai",
  "budget": "medium",
  "duration": 5,
  "travel_style": "cultural",
  "weather_preference": "warm"
}
```

**Response:**
```json
{
  "session_id": "uuid-here",
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
```

### POST `/api/itinerary`

**Request:**
```json
{
  "session_id": "uuid-from-plan-response",
  "selected_destination": "Bali"
}
```

**Response:**
```json
{
  "itinerary": {
    "destination": "Bali, Indonesia",
    "duration": 5,
    "itinerary": {
      "Day 1": {
        "morning": "Watch sunrise at Tanah Lot temple",
        "afternoon": "Explore Ubud Monkey Forest",
        "evening": "Dinner at a local warung",
        "tip": "Rent a scooter for easy mobility"
      }
    }
  }
}
```

---

## ⚙️ Configuration

| Variable             | Required | Default  | Description                          |
|----------------------|----------|----------|--------------------------------------|
| `OPENROUTER_API_KEY` | Yes*     | —        | OpenRouter API key                   |
| `GROQ_API_KEY`       | Yes*     | —        | Groq API key                         |
| `WEATHER_API_KEY`    | Yes      | —        | OpenWeatherMap API key               |
| `MODEL_PROVIDER`     | Yes      | `groq`   | `"groq"` or `"openrouter"`           |
| `MODEL_NAME`         | No       | auto     | Override default model for provider  |

*At minimum, the key for your chosen `MODEL_PROVIDER` must be set.

---

## 🛡️ Guardrails & Error Handling

- **Input validation** runs before any LLM call — rejects empty city, `duration < 1`, and out-of-range values.
- **Invalid budget** values are normalised to `"low"` (not rejected) for graceful degradation.
- **Weather API failure** does not block recommendations — a neutral score of 5/10 is used as fallback.
- **LLM JSON parsing** retries once with a stricter prompt if the first attempt returns malformed JSON.
- **Frontend** validates all fields client-side before submitting, and displays auto-hiding error banners.

---

## 🧪 Testing

See [`docs/testing_cases.md`](docs/testing_cases.md) for the full test matrix.

```bash
# Run tests
python -m pytest tests/
```

---

## 📄 License

This project is for educational purposes (college project).
