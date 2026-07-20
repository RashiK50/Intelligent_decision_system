"""Legacy /query endpoint.

Kept for backward compatibility; delegates to the same compiled graph as the
canonical app in main.py. The previous version called graph.invoke()
synchronously, which crashes on async nodes — this one awaits ainvoke.
"""

import uuid

from fastapi import FastAPI

from api.request_models import QueryRequest
from graph.workflow import graph
from state import build_initial_state

app = FastAPI(title="Enterprise Decision Intelligence Platform (legacy endpoint)")


@app.post("/query")
async def query(request: QueryRequest):
    state = build_initial_state(request.query)
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = await graph.ainvoke(state, config=config)
    return {"response": result.get("formatted_response") or "No response generated."}
