from agents.intent_agent import intent_agent

state = {
    "user_query": "What are the top selling products?",
    "intent": None,
    "sub_intent": None,
    "entities": {},
    "workflow": None,
    "plan": {},
    "sql_query": None,
    "query_result": None,
    "formatted_response": None
}

result = intent_agent(state)

print(result)