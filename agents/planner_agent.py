"""Planner Agent — produces the structured query blueprint (no SQL).

Self-correction loop: when the SQL Validator or Generator reports an issue,
the issue text is injected back into the prompt and sql_retry_count increments.
The workflow router stops the loop after 3 attempts.
"""

import json
import logging
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from langchain_core.prompts import PromptTemplate

from state import PlatformState
from registry.prompt_registry import get_prompt
from utils.llm import invoke_structured
from utils.logger import log_node

logger = logging.getLogger(__name__)

FALLBACK_PROMPT = """
You are the Master Query Planner for an Enterprise Decision Intelligence Platform.

USER QUERY: "{user_query}"
ORCHESTRATOR DIRECTIVE: "{directive}"
EXTRACTED ENTITIES: {entities}
{error_injection}

AVAILABLE SCHEMA CONTEXT:
{schema_context}

TASK:
Map the user's intent and entities directly to the provided schema.
Determine exactly which tables, joins, aggregations, and WHERE clause filters are required.
Output a precise, structured blueprint that a downstream SQL Generator can convert into Postgres SQL.
"""


class FilterCondition(BaseModel):
    column: str = Field(description="The exact database column name (e.g., 'order_date', 'product_category').")
    operator: str = Field(description="The SQL operator (e.g., '=', '>', '<=', 'ILIKE', 'IN').")
    value: str = Field(description="The value to filter by, formatted for SQL (e.g., '100', \"'Electronics'\", \"'2026-01-01'\").")


class JoinCondition(BaseModel):
    left_table: str = Field(description="The first table in the join (e.g., 'order_items').")
    left_column: str = Field(description="The join column on the left table, unqualified (e.g., 'product_id').")
    right_table: str = Field(description="The second table in the join (e.g., 'products').")
    right_column: str = Field(description="The join column on the right table, unqualified (e.g., 'product_id').")
    join_type: str = Field(default="INNER", description="JOIN type: INNER, LEFT, RIGHT, or FULL. Default INNER.")


class PlannerOutput(BaseModel):
    tables: List[str] = Field(description="List of tables that need to be joined or queried.")
    joins: List[JoinCondition] = Field(default_factory=list, description="Explicit join keys connecting the tables")
    metrics: List[str] = Field(default_factory=list, description="The columns or aliases to SELECT.")
    aggregations: List[str] = Field(default_factory=list, description="Mathematical operations needed (e.g., 'SUM(order_items.price)').")
    filters: List[FilterCondition] = Field(default_factory=list, description="Precise conditions for the WHERE clause.")
    group_by: List[str] = Field(default_factory=list, description="Columns to use in the GROUP BY clause.")
    sort_by: Optional[str] = Field(None, description="ORDER BY logic (e.g., 'total_revenue DESC').")
    limit: Optional[Union[int, str]] = Field(None, description="Number of rows to limit.")
    reasoning: str = Field(default="", description="Step-by-step logic explaining why these tables, joins, and filters were chosen.")

    @field_validator("limit", mode="before")
    @classmethod
    def coerce_limit_to_int(cls, v):
        """LLM tool-calling occasionally returns numeric fields as strings ('10').
        Coerce here rather than failing validation outright."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                return None
        return v


@log_node("planner")
def planner_agent(state: PlatformState) -> dict:
    print("\n==================================================")
    print(" [PLANNER NODE] Starting execution...")
    print("==================================================")

    user_query = state.get("user_query", "")
    entities = state.get("entities", {})
    schema_context = state.get("schema_context", "")
    plan_state = state.get("plan", {})
    directive = plan_state.get("directive", "Generate a plan based on the intent and schema.")

    # Self-correction: inject the previous validation failure, if any.
    validation_data = state.get("sql_validation", {})
    issues = validation_data.get("issues")
    is_valid = validation_data.get("is_valid", True)  # True on first pass

    error_injection = ""
    if not is_valid and issues:
        print(f"⚠️ [PLANNER NODE] Self-correction triggered. Issue: {issues}")
        error_injection = (
            "[SYSTEM ALERT: PREVIOUS EXECUTION FAILED]\n"
            f"The SQL generated from your previous plan failed with:\n{issues}\n"
            "Revise your plan (tables, columns, filters, or joins) to resolve this exact issue."
        )

    prompt = PromptTemplate.from_template(get_prompt("planner", fallback=FALLBACK_PROMPT))
    formatted_prompt = prompt.format(
        user_query=user_query,
        directive=directive,
        entities=json.dumps(entities, default=str),
        schema_context=schema_context,
        error_injection=error_injection,
    )

    try:
        print(" [PLANNER NODE] Analyzing schema and drafting query blueprint...")
        result: PlannerOutput = invoke_structured("planner", formatted_prompt, PlannerOutput)

        print("--------------------------------------------------")
        print(" [PLANNER NODE] Blueprint Generated:")
        print(f"   - Target Tables: {result.tables}")
        print(f"   - Joins:         {[(j.left_table, j.right_table) for j in result.joins]}")
        print(f"   - Aggregations:  {result.aggregations}")
        print(f"   - Filters:       {[f'{f.column} {f.operator} {f.value}' for f in result.filters]}")
        print(f"   - Sort / Limit:  {result.sort_by} / {result.limit}")
        print("--------------------------------------------------")

        updated_plan = {**plan_state, "blueprint": result.model_dump()}

        # Count this pass as a retry only when it was triggered by a failure.
        current_retry_count = state.get("sql_retry_count", 0)
        new_retry_count = current_retry_count + 1 if not is_valid else current_retry_count

        return {"plan": updated_plan, "sql_retry_count": new_retry_count}

    except Exception as e:
        logger.error("Planner failed after retries: %s", e)
        print(f"❌ [PLANNER NODE] CRITICAL ERROR: {e}")
        # Surface a structured failure so routing can send this to Output
        # instead of crashing the graph.
        return {
            "plan": plan_state,
            "sql_retry_count": state.get("sql_retry_count", 0) + 1,
            "sql_validation": {"is_valid": False, "issues": f"Planner LLM failure: {e}"},
            "execution_status": "failed",
            "error_message": f"Planner failure: {e}",
        }
