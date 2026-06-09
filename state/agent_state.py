from typing import TypedDict, Optional


class AgentState(TypedDict):

    user_query: str

    intent: Optional[str]

    sub_intent: Optional[str]

    entities: dict

    workflow: Optional[str]

    plan: dict

    sql_query: Optional[str]

    query_result: Optional[list]

    formatted_response: Optional[str]

    sql_validation: dict

    is_allowed: bool | None = None

    guardrail_reason: str | None = None