from typing import TypedDict, Optional, List, Dict, Any
from pydantic import BaseModel, Field

# ==========================================
# Pydantic Schema for Structured Outputs
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
    
    # Plan Construction
    plan: Dict[str, Any]
    
    # SQL Target States
    sql_query: Optional[str]
    sql_validation: Dict[str, Any]
    sql_retry_count: int  # Keeps track of how many self-healing loops have executed
    raw_db_result: Optional[List[dict[str, Any]]]
    execution_status: Optional[str]
    error_message: Optional[str]
    
    # Raw Results & Delivery
    query_result: Optional[List[Dict[str, Any]]]
    formatted_response: Optional[str]

    workflow: Optional[str] # single_planner, parallel_planners, sequential_planners