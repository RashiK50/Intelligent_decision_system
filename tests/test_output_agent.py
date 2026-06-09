from agents.output_agent import output_agent

state = {

    "user_query":
    "What are the top selling products?",

    "query_result": [
        {
            "product_id":
            "aca2eb7d00ea1a7b8ebd4e68314663af",
            "sales_count": 527
        },
        {
            "product_id":
            "99a4788cb24856965c36a24e339b6058",
            "sales_count": 488
        }
    ]
}

result = output_agent(state)

print(
    result["formatted_response"]
)