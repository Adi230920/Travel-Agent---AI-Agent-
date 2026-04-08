# ✈️ GulliverAI — Intelligent Travel Agent

An AI-powered travel planning ecosystem that transforms vague travel desires into detailed, actionable itineraries. Built with a modular, multi-agent architecture using **LangGraph** and **FastAPI**.

---

## 🎯 Objective
The primary goal of GulliverAI is to simplify the complex process of trip planning. By leveraging Large Language Models (LLMs) and real-time external data (Weather, TripAdvisor), the system provides personalized, context-aware destination recommendations and comprehensive day-by-day travel plans, ensuring every trip is optimized for the user's preferences, budget, and local conditions.

## 🛠️ Tools / Technologies Used

### Backend Stack
- **Language**: Python 3.10+
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (High-performance REST API)
- **Agent Orchestration**: [LangGraph](https://langchain-ai.github.io/langgraph/) (Stateful, multi-agent workflows)
- **AI Models**: Support for OpenAI, Groq (Llama 3), and OpenRouter
- **Environment**: Pydantic, Python-dotenv

### APIs & Integrations
- **TripAdvisor (via RapidAPI)**: Provides real-time venue recommendations and popularity data.
- **OpenWeatherMap**: Fetches current weather data for dynamic destination scoring.
- **Unsplash API**: Sources high-quality, relevant imagery for recommended locations.

### Frontend
- **Structure**: Semantic HTML5
- **Styling**: Modern Vanilla CSS3 (Dark-mode, Glassmorphism, Micro-animations)
- **Logic**: Vanilla JavaScript (ES6+), Fetch API

---

## 🧠 Methodology / Approach

GulliverAI utilizes an **Agentic Workflow** modeled as a directed graph. This allows for stateful transitions, error handling, and human-in-the-loop decision-making.

1.  **State Management**: A centralized `TravelState` object tracks user preferences, recommended options, and the final itinerary throughout the session.
2.  **Multi-Agent Pipeline**:
    -   **Input Agent**: Sanitizes and validates user queries (e.g., origin city, budget constraints).
    -   **Recommendation Agent**: A "Brain" node that combines LLM reasoning with weather/popularity scores to suggest the top 5 uniquely suited destinations.
    -   **Planning Agent**: Generates a rich, chronologically structured itinerary for the user's chosen destination.
3.  **Human-in-the-loop**: The graph execution interrupts after the recommendation phase, waiting for the user's specific selection via the API/UI before proceeding to generate the itinerary.

---

## 🚀 Implementation Steps

### 1. Repository & Environment Setup
Initialize the project structure and install dependencies.
```bash
git clone https://github.com/[your-username]/ai-travel-agent.git
cd ai-travel-agent
pip install -r requirements.txt
```

### 2. Agent Development
Implementation of specialized agents in `backend/agents/` to handle validation, reasoning, and planning logic independently.

### 3. Workflow Orchestration
Building the `travel_graph.py` to define nodes and edges, implementing the logic that connects agents to external tools and manages session transitions.

### 4. API Layer Integration
Developing FastAPI endpoints in `api.py` to bridge the LangGraph backend with the frontend/CLI, handling CORS and session persistence.

### 5. UI/UX Design
Creating a premium, responsive interface in `frontend/` that provides a seamless "Chat-to-Plan" experience with real-time feedback.

---

## 📊 Results / Output Screenshots

### 🖥️ Dashboard View
*The main interface where users input their travel desires.*
![Dashboard Placeholder](https://via.placeholder.com/800x450/1e1e2e/ffffff?text=GulliverAI+Dashboard+Interface)

### 🗺️ Destination Recommendations
*Personalized suggestions with weather scores and high-quality imagery.*
![Recommendations Placeholder](https://via.placeholder.com/800x450/2a2a3e/ffffff?text=AI+Recommendations+Panel)

### 🗓️ Itinerary Generation
*A detailed, day-by-day plan ready for the user's adventure.*
![Itinerary Placeholder](https://via.placeholder.com/800x450/161622/ffffff?text=Dynamic+Itinerary+View)

---

## 🏁 Conclusion
GulliverAI successfully demonstrates how specialized AI agents can collaborate to solve complex, multi-step problems like travel planning. By integrating real-world data with LLM reasoning, it provides a tool that is not just a chatbot, but a practical, context-aware travel consultant.

## 🔮 Future Scope
-   **Live Booking**: Integration with flight and hotel booking APIs (e.g., Amadeus, Skyscanner).
-   **Social Integration**: Allow users to share generated itineraries with tripmates.
-   **PDF Export**: Feature to download itineraries for offline access.
-   **Voice Commands**: Implementation of AI voice interactions for hands-free planning.

---

## 📄 Setup Guide
For full setup instructions, please refer to the [.env.example](.env.example) and the **Quick Start** section in the repository.

*This project was developed for educational purposes (College Project).*
