from registry.prompt_registry import get_prompt
from state.sql_validator_schema import SQLValidatorOutput
from tools.llm import get_llm


def sql_validator_agent(state):

    llm = get_llm()

    structured_llm = llm.with_structured_output(
        SQLValidatorOutput
    )

    prompt = get_prompt("sql_validator")

    result = structured_llm.invoke(
        f"""
        {prompt}

        SQL Query:

        {state['sql_query']}
        """
    )

    state["sql_validation"] = result.model_dump()

    if result.is_valid:
        state["sql_query"] = result.corrected_sql

    return state