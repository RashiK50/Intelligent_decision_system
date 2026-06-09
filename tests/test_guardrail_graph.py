from graph.workflow import graph

queries = [

    "What are the top selling products?",

    "Which sellers generated the highest revenue?",

    "Tell me a joke",

    "Who won IPL 2025?"
]

for q in queries:

    print("\n" + "=" * 50)
    print(q)

    state = {

        "user_query": q,

        "intent": None,
        "sub_intent": None,

        "entities": {},

        "workflow": None,

        "plan": {},

        "sql_query": None,

        "sql_validation": {},

        "query_result": None,

        "formatted_response": None,

        "is_allowed": None,

        "guardrail_reason": None
    }

    result = graph.invoke(state)

    print(result.get("is_allowed"))
    print(result.get("guardrail_reason"))