import json
import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph.workflow import graph
from state import build_initial_state

logger = logging.getLogger("api")

app = FastAPI(
    title="Enterprise Decision Intelligence API",
    description="Natural Language to SQL Business Insights Platform",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production security as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    user_query: str
    thread_id: str


class ChatResponse(BaseModel):
    formatted_response: str
    # Structured artifacts for the frontend (chart specs, export paths, ...).
    # Optional and additive: existing consumers that only read
    # formatted_response are unaffected.
    data: Optional[Dict[str, Any]] = None


def _extract_artifacts(final_state: dict) -> Optional[Dict[str, Any]]:
    """Pull renderable/structured artifacts out of the tool results."""
    tools = (final_state.get("parallel_results") or {}).get("tools") or {}
    artifacts: Dict[str, Any] = {}
    for name, result in tools.items():
        if isinstance(result, dict) and result.get("status") == "success":
            artifacts[name] = {k: v for k, v in result.items() if k not in ("status", "tool")}
    if not artifacts:
        return None
    # Ensure JSON-serializable payloads (Decimal, datetime, ...)
    return json.loads(json.dumps(artifacts, default=str))


@app.get("/health")
async def health():
    return {"status": "ok", "graph_nodes": list(graph.get_graph().nodes.keys())}


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Accepts a natural language business question, processes it through the
    LangGraph agent workflow, and returns the synthesized business insight.
    """
    initial_state = build_initial_state(request.user_query)

    try:
        config = {"configurable": {"thread_id": request.thread_id}}
        final_state = await graph.ainvoke(initial_state, config=config)

        response_text = final_state.get("formatted_response", "")
        if not response_text and final_state.get("error_message"):
            response_text = (
                f"An error occurred during workflow execution: {final_state.get('error_message')}"
            )

        return ChatResponse(
            formatted_response=response_text or "No response generated.",
            data=_extract_artifacts(final_state),
        )

    except Exception as e:
        logger.exception("Workflow execution failed")
        raise HTTPException(status_code=500, detail=str(e))
