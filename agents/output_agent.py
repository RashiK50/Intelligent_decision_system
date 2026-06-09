from registry.prompt_registry import get_prompt
from state.output_schema import OutputAgentResponse
from tools.llm import get_llm

def output_agent(state):

    llm = get_llm()

    structured_llm = llm.with_structured_output(
        OutputAgentResponse
    )

    prompt = get_prompt("output")

    result = structured_llm.invoke(
        f"""
        {prompt}

        User Query:
        {state['user_query']}

        Query Result:
        {state['query_result']}
        """
    )

    state["formatted_response"] = result.answer

    return state