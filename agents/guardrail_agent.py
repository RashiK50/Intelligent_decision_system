from state.agent_state import AgentState


def guardrail_agent(state: AgentState):

    query = state["user_query"].lower()

    allowed_keywords = [
        "sales",
        "revenue",
        "product",
        "products",
        "customer",
        "customers",
        "seller",
        "sellers",
        "review",
        "reviews",
        "forecast",
        "order",
        "orders",
        "payment",
        "payments",
        "category",
        "categories",
        "analytics",
        "business",
        "trend",
        "trends",
        "kpi",
        "kpis"
    ]

    is_allowed = any(
        keyword in query
        for keyword in allowed_keywords
    )

    state["is_allowed"] = is_allowed

    if not is_allowed:

        state["guardrail_reason"] = (
            "Query outside supported business analytics domain."
        )

    else:

        state["guardrail_reason"] = (
            "Query belongs to supported business analytics domain."
        )

    return state