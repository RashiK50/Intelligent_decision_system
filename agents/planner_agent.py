from registry.prompt_registry import load_prompt
from state.planner_schema import PlannerOutput
from tools.llm import get_llm


def planner_agent(state):

    llm = get_llm()

    structured_llm = llm.with_structured_output(
        PlannerOutput
    )

    prompt = load_prompt("planner")

    result = structured_llm.invoke(
        f"""
        {prompt}

        User Query:
        {state['user_query']}

        Intent:
        {state['intent']}

        Sub Intent:
        {state['sub_intent']}
        """
    )

    state["plan"] = result.model_dump()

    return state