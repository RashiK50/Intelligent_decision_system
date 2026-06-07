from agents.sql_validator_agent import sql_validator_agent


state = {
    "sql_query": """
    SELECT p.product_id,
           p.product_category_name,
           COUNT(oi.order_id) AS sales_count
    FROM products p
    JOIN order_items oi
    ON p.product_id = oi.product_id
    GROUP BY p.product_id,
             p.product_category_name
    ORDER BY sales_count DESC
    LIMIT 10;
    """,

    "sql_validation": {}
}

result = sql_validator_agent(state)

print(result["sql_validation"])