from agents.planner_agent import planner_agent


state = {
    "user_query": "What are the top selling products?",
    "intent": "product_analysis",
    "sub_intent": "top_products",
    "entities": {},
    "workflow": None,
    "plan": {},
    "sql_query": None,
    "query_result": None,
    "formatted_response": None
}

result = planner_agent(state)

print(result["plan"])