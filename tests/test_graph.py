from graph.workflow import graph


state = {

    "user_query":
    "What are the top selling products?",

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


result = graph.invoke(
    state
)

print(
    result["formatted_response"]
)