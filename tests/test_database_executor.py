from agents.database_executor_agent import (
    database_executor_agent
)

state = {

    "sql_query": """
    SELECT
        p.product_id,
        COUNT(oi.order_id) AS sales_count
    FROM order_items oi
    JOIN products p
        ON oi.product_id = p.product_id
    GROUP BY p.product_id
    ORDER BY sales_count DESC
    LIMIT 10;
    """,

    "query_result": None
}

result = database_executor_agent(
    state
)

print(result["query_result"])