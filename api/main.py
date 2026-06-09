from fastapi import FastAPI

from api.request_models import QueryRequest

from graph.workflow import graph


app = FastAPI(
    title="Enterprise Decision Intelligence Platform"
)


@app.post("/query")
def query(request: QueryRequest):

    state = {

        "user_query": request.query,

        "intent": None,
        "sub_intent": None,

        "entities": {},

        "workflow": None,

        "plan": {},

        "sql_query": None,

        "sql_validation": {},

        "query_result": None,

        "formatted_response": None
    }

    result = graph.invoke(state)

    return {
        "response": result["formatted_response"]
    }