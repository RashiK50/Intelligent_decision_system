from registry.prompt_registry import get_prompt
from state.agent_state import AgentState


def guardrail_agent(state: AgentState):

    query = state["user_query"]

    # Placeholder logic
    # LLM logic will come next

    allowed_keywords = [
        "sales",
        "revenue",
        "product",
        "customer",
        "seller",
        "review",
        "forecast",
        "order"
    ]

    if not any(
        keyword in query.lower()
        for keyword in allowed_keywords
    ):
        raise ValueError(
            "Query outside supported business domain."
        )

    return state