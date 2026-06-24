from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Import your compiled LangGraph from workflow.py
# Adjust the import path based on exactly where you defined 'graph = builder.compile()'
from graph.workflow import graph 
from state import PlatformState

app = FastAPI(
    title="Enterprise Decision Intelligence API",
    description="Natural Language to SQL Business Insights Platform",
    version="1.0.0"
)

# 1. Define Request / Response Models for Swagger UI
class ChatRequest(BaseModel):
    query: str
    
class ChatResponse(BaseModel):
    insight: str
    execution_status: str
    error_message: Optional[str] = None

# 2. Define the Endpoint
@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Accepts a natural language business question, processes it through the 
    LangGraph agent workflow, and returns the synthesized business insight.
    """
    # Initialize the starting state
    initial_state: PlatformState = {
        "user_query": request.query,
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
        "formatted_response": ""
    }

    try:
        # Execute the LangGraph workflow
        # .invoke() runs the graph synchronously. Use .ainvoke() if your graph is fully async.
        final_state = await graph.ainvoke(initial_state)
        
        return ChatResponse(
            insight=final_state.get("formatted_response", "No response generated."),
            execution_status=final_state.get("execution_status", "unknown"),
            error_message=final_state.get("error_message")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))