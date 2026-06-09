from tools.database_executor import execute_query


def database_executor_agent(state):

    result = execute_query(
        state["sql_query"]
    )

    state["query_result"] = result

    return state