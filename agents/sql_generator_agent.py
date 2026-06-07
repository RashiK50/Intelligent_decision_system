from registry.prompt_registry import load_prompt
from state.sql_schema import SQLGeneratorOutput
from tools.llm import get_llm


def sql_generator_agent(state):

    llm = get_llm()

    structured_llm = llm.with_structured_output(
        SQLGeneratorOutput
    )

    prompt = load_prompt("sql_generator")

    result = structured_llm.invoke(
        f"""
        {prompt}

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