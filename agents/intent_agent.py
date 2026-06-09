from registry.prompt_registry import get_prompt
from state.intent_schema import IntentOutput
from tools.llm import get_llm


def intent_agent(state):

    llm = get_llm()

    structured_llm = llm.with_structured_output(
        IntentOutput
    )

    prompt = get_prompt("intent")

    result = structured_llm.invoke(
        f"""
        {prompt}

        User Query:
        {state['user_query']}
        """
    )

    state["intent"] = result.intent
    state["sub_intent"] = result.sub_intent

    return state