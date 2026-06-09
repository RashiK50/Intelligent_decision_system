from agents.intent_agent import intent_agent
from agents.planner_agent import planner_agent
from agents.sql_generator_agent import sql_generator_agent
from agents.sql_validator_agent import sql_validator_agent
from agents.database_executor_agent import database_executor_agent
from agents.output_agent import output_agent


TEST_QUERIES = [

    # "What are the top selling products?",

    # "Which sellers generated the highest revenue?",

    # "What is the average review score by product category?",

    # "Which product categories generated the highest revenue?",

    # "Predict next month's sales.",

    # "Which states have the highest number of customers?",

    "Which orders experienced the longest delivery times?",

    # "What are the most popular payment methods?",

    # "Which products should be discontinued?",

    # "Which product categories generate high revenue but receive poor customer reviews?"
]


for i, query in enumerate(TEST_QUERIES, start=1):

    print("\n" + "=" * 80)
    print(f"TEST {i}")
    print("=" * 80)

    try:

        state = {

            "user_query": query,

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

        state = intent_agent(state)

        state = planner_agent(state)

        state = sql_generator_agent(state)

        state = sql_validator_agent(state)

        state = database_executor_agent(state)

        state = output_agent(state)

        print("\nQUERY:")
        print(query)

        print("\nINTENT:")
        print(state["intent"])

        print("\nSUB INTENT:")
        print(state["sub_intent"])

        print("\nPLAN:")
        print(state["plan"])

        print("\nSQL:")
        print(state["sql_query"])

        print("\nROWS RETURNED:")
        print(len(state["query_result"]))

        print("\nFINAL RESPONSE:")
        print(state["formatted_response"])

    except Exception as e:

        print(f"\nFAILED: {query}")
        print(e)