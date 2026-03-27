import uuid
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from langgraph.checkpoint.memory import MemorySaver
from backend.graph.travel_graph import build_graph
from backend.state.session_state import create_initial_state

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Travel Agent API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared checkpointer and graph instance
# MemorySaver stores checkpoints in memory keyed by thread_id
checkpointer = MemorySaver()
travel_graph = build_graph(checkpointer=checkpointer)

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
class PlanRequest(BaseModel):
    origin_city: str
    budget: str
    duration: int
    travel_style: str
    weather_preference: str

class ItineraryRequest(BaseModel):
    session_id: str
    selected_destination: str

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    """Sanity check to verify the API is running."""
    return {"status": "ok"}

@app.post("/api/plan")
async def plan_trip(request: PlanRequest):
    """
    Initialise a travel planning session and run the graph until the interrupt.
    Returns recommendations.
    """
    # ── Guardrail: reject bad input before any LLM call ────
    if not request.origin_city or not request.origin_city.strip():
        raise HTTPException(status_code=422, detail="origin_city is required and must be non-empty.")
    if request.duration < 1 or request.duration > 30:
        raise HTTPException(status_code=422, detail="duration must be between 1 and 30 days.")

    try:
        session_id = str(uuid.uuid4())
        initial_input = request.dict()
        
        # 1. Initialize state
        state = create_initial_state(initial_input)
        
        # 2. Configure the thread (session)
        config = {"configurable": {"thread_id": session_id}}
        
        # 3. Run graph until interrupt
        # The graph is compiled with interrupt_before=["planning_node"]
        # so it will run input_node -> recommendation_node -> selection_node and then stop.
        result = travel_graph.invoke(state, config=config)
        
        # 4. Handle internal graph errors
        if result.get("error"):
            logger.warning("Graph error in /api/plan: %s", result["error"])
            raise HTTPException(
                status_code=500,
                detail=str(result["error"]),
            )
            
        return {
            "session_id": session_id,
            "recommendations": result.get("recommendations", [])
        }
        
    except HTTPException:
        raise  # re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error("Error in /api/plan: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail="A backend error occurred while planning.",
        )

@app.post("/api/itinerary")
async def get_itinerary(request: ItineraryRequest):
    """
    Resume a travel planning session with a selected destination.
    Returns the final itinerary.
    """
    if not request.selected_destination or not request.selected_destination.strip():
        raise HTTPException(status_code=422, detail="selected_destination is required.")

    try:
        session_id = request.session_id
        config = {"configurable": {"thread_id": session_id}}
        
        # 1. Verify session exists by trying to get state
        current_state = travel_graph.get_state(config)
        if not current_state.values:
            raise HTTPException(
                status_code=404,
                detail="Session not found or expired.",
            )
            
        # 2. Inject selected_destination into the state
        travel_graph.update_state(config, {"selected_destination": request.selected_destination})
        
        # 3. Resume execution
        result = travel_graph.invoke(None, config=config)
        
        # 4. Handle internal graph errors
        if result.get("error"):
            logger.warning("Graph error in /api/itinerary: %s", result["error"])
            raise HTTPException(
                status_code=500,
                detail=str(result["error"]),
            )
            
        return {"itinerary": result.get("itinerary", {})}
        
    except HTTPException:
        raise  # re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error("Error in /api/itinerary: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail="A backend error occurred while generating itinerary.",
        )
