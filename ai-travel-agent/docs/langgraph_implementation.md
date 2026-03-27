# LangGraph Implementation Guide

## Graph Structure
Nodes: input_node → recommendation_node → selection_node → planning_node
Edges: Linear with one conditional pause at selection_node

## State Schema
class TravelState(TypedDict):
    user_input: dict
    parsed_preferences: dict
    weather_data: dict
    recommendations: list
    selected_destination: str
    itinerary: dict
    error: str
    current_step: str

## Node Pattern (follow this for every node)
def node_name(state: TravelState) -> TravelState:
    try:
        # 1. Extract what you need from state
        # 2. Do the work (LLM call / API call)
        # 3. Update state with result
        # 4. Update current_step
        return state
    except Exception as e:
        state["error"] = f"node_name failed: {str(e)}"
        return state

## Interrupt Pattern (for user selection)
Use LangGraph's interrupt_before=["planning_node"] to pause
Resume graph with: graph.invoke(state, config, resume=selected_dest)

## Critical Rules
- Every node must update current_step (for frontend progress tracking)
- Every node must handle its own errors and write to state["error"]
- Never call LLM directly in graph file — delegate to agent modules
- State is the single source of truth — never use global variables