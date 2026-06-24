from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# CORS and thread models configured for modern frontend layout

# Import your compiled LangGraph from workflow.py
from graph.workflow import graph 
from state import PlatformState

app = FastAPI(
    title="Enterprise Decision Intelligence API",
    description="Natural Language to SQL Business Insights Platform",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production security as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Define Request / Response Models based on frontend specifications
class ChatRequest(BaseModel):
    user_query: str
    thread_id: str
    
class ChatResponse(BaseModel):
    formatted_response: str

# 2. Define the Endpoint
@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Accepts a natural language business question, processes it through the 
    LangGraph agent workflow, and returns the synthesized business insight.
    """
    # Initialize the starting state
    initial_state: PlatformState = {
        "user_query": request.user_query,
        "is_allowed": None,
        "guardrail_reason": None,
        "intent": None,
        "sub_intent": None,
        "entities": {},
        "schema_context": "",
        "plan": {},
        "sql_query": "",
        "sql_validation": {},
        "sql_retry_count": 0,
        "raw_db_result": None,
        "execution_status": "pending",
        "error_message": None,
        "formatted_response": "",
        "query_result": None,
        "workflow": None
    }

    try:
        # Execute the LangGraph workflow using thread memory config
        config = {"configurable": {"thread_id": request.thread_id}}
        final_state = await graph.ainvoke(initial_state, config=config)
        
        # In case the workflow encounters error but completes, bubble up error message format if needed
        response_text = final_state.get("formatted_response", "")
        if not response_text and final_state.get("error_message"):
            response_text = f"An error occurred during workflow execution: {final_state.get('error_message')}"
            
        return ChatResponse(
            formatted_response=response_text or "No response generated."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))