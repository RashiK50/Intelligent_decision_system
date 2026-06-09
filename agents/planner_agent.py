from registry.prompt_registry import get_prompt
from state.planner_schema import PlannerOutput
from tools.llm import get_llm
from registry.schema_loader import get_schema_context

def planner_agent(state):

    llm = get_llm()

    schema_context = get_schema_context()

    structured_llm = llm.with_structured_output(
        PlannerOutput
    )

    prompt = get_prompt("planner")
    
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
        """
    )

    state["plan"] = result.model_dump()

    return state