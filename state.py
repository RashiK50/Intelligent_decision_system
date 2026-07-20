from typing import Annotated, Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field

# ==========================================
# Reducers for parallel (fan-out/fan-in) writes
# ==========================================
# When the SQL branch and the tool branch run in parallel, both may write to
# the same state key in the same superstep. Without a reducer LangGraph raises
# InvalidUpdateError; with these reducers the writes merge deterministically.


def merge_dicts(left: Optional[Dict[str, Any]], right: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge parallel branch results. Right (newer) wins on key collisions."""
    return {**(left or {}), **(right or {})}


def merge_status(left: Optional[str], right: Optional[str]) -> Optional[str]:
    """'failed' is sticky: if any branch failed, the overall status is failed.

    The Output Agent still synthesizes partial results when possible; this
    flag just tells it that at least one branch had a problem.
    """
    if left == "failed" or right == "failed":
        return "failed"
    return right or left


def merge_errors(left: Optional[str], right: Optional[str]) -> Optional[str]:
    """Concatenate distinct error messages from parallel branches."""
    parts = [p for p in (left, right) if p]
    if not parts:
        return None
    seen: List[str] = []
    for p in parts:
        if p not in seen:
            seen.append(p)
    return " | ".join(seen)


# ==========================================
# Pydantic Schemas for Structured Outputs
# ==========================================

class GuardrailStateOutput(BaseModel):
    classification: str = Field(description="'domain_specific' or 'vague_or_out_of_scope'")
    is_allowed: bool = Field(description="True if query belongs to the business domain, False otherwise.")
    guardrail_reason: Optional[str] = Field(None, description="Explanation given to the user if blocked.")


class IntentStateOutput(BaseModel):
    intent: str = Field(description="Primary business intent (e.g., inventory_supply_analysis, sales_performance_analysis)")
    sub_intent: str = Field(description="Specific sub-category category")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted filter entities like dates, product IDs")


class JoinConditionOutput(BaseModel):
    left_table: str = Field(description="Left-hand table in the join")
    left_column: str = Field(description="Join column on the left table")
    right_table: str = Field(description="Right-hand table in the join")
    right_column: str = Field(description="Join column on the right table")
    join_type: str = Field(default="INNER", description="JOIN type: INNER, LEFT, RIGHT, FULL")


class PlannerStateOutput(BaseModel):
    tables: List[str] = Field(description="Tables required to satisfy the request")
    joins: List[JoinConditionOutput] = Field(default_factory=list, description="Explicit join keys connecting the tables")
    metrics: List[str] = Field(description="Calculations or KPIs requested")
    filters: List[Dict[str, Any]] = Field(description="SQL WHERE conditions mapped out")
    reasoning: str = Field(description="Step-by-step logic detailing how to structure the data approach")


class ValidationStateOutput(BaseModel):
    is_valid: bool = Field(description="True if query passes security and structural rules")
    corrected_sql: Optional[str] = Field(None, description="The adjusted valid SQL block if minor syntax changes occurred")
    issues: Optional[str] = Field(None, description="Description of rule failures if invalid")


# ==========================================
# Core LangGraph State Definition
# ==========================================

class PlatformState(TypedDict):
    """
    The global state dictionary passed through the LangGraph multi-agent workflow.
    """
    # Core User Metadata
    user_query: str
    schema_context: str

    # Guardrail Block
    is_allowed: Optional[bool]
    guardrail_reason: Optional[str]

    # Intent Elements
    intent: Optional[str]
    sub_intent: Optional[str]
    entities: Dict[str, Any]

    # Orchestrator decisions
    workflow: Optional[str]            # single_planner | parallel_planner | sequential_planners
    required_tasks: List[str]          # nodes to run: database_executor / tool_executor
    required_tools: List[str]          # specific tool names from the tool registry
    available_tools: Optional[str]

    # Plan Construction
    plan: Dict[str, Any]

    # SQL Target States
    sql_query: Optional[str]
    sql_validation: Dict[str, Any]
    sql_retry_count: int  # Keeps track of how many self-healing loops have executed

    # Shared Execution (Database Agent AND Tool Agent both write here)
    parallel_results: Annotated[Dict[str, Any], merge_dicts]
    execution_status: Annotated[Optional[str], merge_status]
    error_message: Annotated[Optional[str], merge_errors]

    # Final Output Delivery
    query_result: Optional[List[Dict[str, Any]]]
    formatted_response: Optional[str]

    # Legacy / metadata
    raw_db_result: Optional[List[Dict[str, Any]]]
    tool_results: Optional[str]


def build_initial_state(user_query: str) -> PlatformState:
    """Canonical initial state used by every API entrypoint."""
    return {
        "user_query": user_query,
        "schema_context": "",
        "is_allowed": None,
        "guardrail_reason": None,
        "intent": None,
        "sub_intent": None,
        "entities": {},
        "workflow": None,
        "required_tasks": [],
        "required_tools": [],
        "available_tools": None,
        "plan": {},
        "sql_query": "",
        "sql_validation": {},
        "sql_retry_count": 0,
        "parallel_results": {},
        "execution_status": "pending",
        "error_message": None,
        "query_result": None,
        "formatted_response": "",
        "raw_db_result": None,
        "tool_results": None,
    }
