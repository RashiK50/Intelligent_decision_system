from registry.prompt_registry import get_prompt
from state.sql_schema import SQLGeneratorOutput
from tools.llm import get_llm
from registry.schema_loader import get_schema_context

def sql_generator_agent(state):

    llm = get_llm()

    schema_context = get_schema_context()

    structured_llm = llm.with_structured_output(
        SQLGeneratorOutput
    )

    prompt = get_prompt("sql_generator")

    result = structured_llm.invoke(
        f"""
        {prompt}

        DATABASE SCHEMA:

        {schema_context}

        User Query:
        {state['user_query']}

        Intent:
        {state['intent']}

        Sub Intent:
        {state['sub_intent']}

        Planner Output:
        {state['plan']}
        """
    )

    state["sql_query"] = result.sql_query

    return state