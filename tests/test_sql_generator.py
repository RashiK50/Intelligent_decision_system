from agents.sql_generator_agent import sql_generator_agent


state = {
    "user_query": "What are the top selling products?",
    "intent": "product_analysis",
    "sub_intent": "top_products",
    "entities": {},
    "workflow": None,
    "plan": {
        "tables": ["order_items", "products"],
        "metrics": ["sales_count"],
        "filters": [],
        "group_by": ["product_id"],
        "aggregations": ["COUNT(order_id)"],
        "sort_by": "sales_count DESC",
        "limit": 10
    },
    "sql_query": None,
    "query_result": None,
    "formatted_response": None
}

result = sql_generator_agent(state)

print(result["sql_query"])