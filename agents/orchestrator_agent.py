"""Orchestrator Agent.

Decides the execution plan for a query:
  - workflow type: single_planner | parallel_planner | sequential_planners
  - which nodes run (required_tasks): database_executor and/or tool_executor
  - which registry tools run (required_tools)
  - which tables the Planner should see (required_tables)

BLOCKER FIX: every LLM-produced field now has a safe default, so a partially
formed LLM response can no longer fail Pydantic validation and halt the graph.
The output is then normalized against the schema/tool registries, and a
deterministic fallback plan is used if the LLM is unreachable entirely.
"""

import logging
from typing import List

from pydantic import BaseModel, Field, field_validator

from langchain_core.prompts import PromptTemplate

from state import PlatformState
from database.schema_registry import schema_registry
from registry.prompt_registry import get_prompt
from registry.tool_registry import registry as tool_registry
from utils.llm import invoke_structured
from utils.logger import log_node

logger = logging.getLogger(__name__)

VALID_WORKFLOWS = ("single_planner", "parallel_planner", "sequential_planners")

# ==========================================
# 1. Pydantic Model — all fields have safe defaults (never hard-fails)
# ==========================================

class OrchestratorOutput(BaseModel):
    workflow_type: str = Field(
        default="single_planner",
        description="Execution path: 'single_planner', 'parallel_planner', or 'sequential_planners'.",
    )
    required_tables: List[str] = Field(
        default_factory=list, description="The exact database tables required. Use [] if none."
    )
    required_tasks: List[str] = Field(
        default_factory=list,
        description="Nodes to run: 'database_executor' and/or 'tool_executor'. Use [] if unsure.",
    )
    required_tools: List[str] = Field(
        default_factory=list,
        description="Exact tool names from the available tools list. Use [] when no tool is needed.",
    )
    execution_plan: str = Field(default="", description="A brief directive for downstream nodes.")

    @field_validator("workflow_type", mode="before")
    @classmethod
    def normalize_workflow(cls, v):
        if not isinstance(v, str):
            return "single_planner"
        v = v.strip().lower()
        aliases = {
            "parallel_planners": "parallel_planner",
            "sequential_planner": "sequential_planners",
            "tool_execution": "single_planner",
        }
        v = aliases.get(v, v)
        return v if v in VALID_WORKFLOWS else "single_planner"


# ==========================================
# 2. Deterministic normalization / fallback
# ==========================================

def normalize_plan(result: OrchestratorOutput, intent: str) -> OrchestratorOutput:
    """Repair inconsistent LLM output so downstream routing is always sane."""
    known_tables = set(schema_registry.tables.keys())
    result.required_tables = [t for t in result.required_tables if t in known_tables]

    result.required_tools = [t for t in result.required_tools if tool_registry.has(t)]

    valid_tasks = {"database_executor", "tool_executor"}
    result.required_tasks = [t for t in result.required_tasks if t in valid_tasks]

    # Tools selected but tool_executor task forgotten (or vice versa)
    if result.required_tools and "tool_executor" not in result.required_tasks:
        result.required_tasks.append("tool_executor")
    if "tool_executor" in result.required_tasks and not result.required_tools:
        intent_tools = tool_registry.get_tools_for_intent(intent or "")
        if intent_tools:
            result.required_tools = [intent_tools[0].name]
        else:
            result.required_tasks.remove("tool_executor")

    # Nothing selected at all -> default to a plain SQL run
    if not result.required_tasks:
        result.required_tasks = ["database_executor"]

    # Any selected tool that consumes SQL rows forces SQL-first ordering
    if "tool_executor" in result.required_tasks and "database_executor" in result.required_tasks:
        needs_sql = any(
            tool_registry.get(t).needs_sql_data for t in result.required_tools if tool_registry.has(t)
        )
        if needs_sql:
            result.workflow_type = "sequential_planners"
        elif result.workflow_type == "single_planner":
            result.workflow_type = "parallel_planner"
    elif result.required_tasks == ["tool_executor"]:
        result.workflow_type = "single_planner"

    return result


def fallback_plan(intent: str) -> OrchestratorOutput:
    """Deterministic plan used when the Orchestrator LLM is unreachable."""
    logger.warning("Orchestrator LLM unavailable — using deterministic fallback plan.")
    return OrchestratorOutput(
        workflow_type="single_planner",
        required_tables=[],  # empty -> Planner receives the full schema menu
        required_tasks=["database_executor"],
        required_tools=[],
        execution_plan=f"Fallback plan: answer the query with SQL for intent '{intent}'.",
    )


# ==========================================
# 3. LangGraph Node Implementation
# ==========================================

@log_node("orchestrator")
def orchestrator_agent(state: PlatformState) -> dict:
    print("\n🚦 [ORCHESTRATOR NODE] Planning Execution...")

    user_query = state.get("user_query", "")
    intent = state.get("intent", "unknown")

    available_tables = "\n".join(f"- {name}" for name in schema_registry.tables.keys())
    available_tools_str = tool_registry.get_tool_descriptions_for_llm(intent)

    prompt_template_str = get_prompt("orchestrator")
    prompt = PromptTemplate.from_template(prompt_template_str)
    formatted_prompt = prompt.format(
        user_query=user_query,
        intent=intent,
        available_tables=available_tables,
        available_tools=available_tools_str,
    )

    try:
        result: OrchestratorOutput = invoke_structured("orchestrator", formatted_prompt, OrchestratorOutput)
    except Exception as e:
        logger.error("❌ [ORCHESTRATOR NODE] LLM error after retries: %s", e)
        result = fallback_plan(intent)

    result = normalize_plan(result, intent)

    print(
        f"✅ [ORCHESTRATOR NODE] Plan: {result.workflow_type} | "
        f"Tasks: {result.required_tasks} | Tools: {result.required_tools} | "
        f"Tables: {result.required_tables or 'ALL'}"
    )

    focused_schema_context = schema_registry.get_formatted_menu_for_intent(
        result.required_tables or None
    )

    return {
        "workflow": result.workflow_type,
        "required_tasks": result.required_tasks,
        "required_tools": result.required_tools,
        "plan": {
            "directive": result.execution_plan or "Answer the user's business question.",
            "tables": result.required_tables,
        },
        "schema_context": focused_schema_context,
        "available_tools": available_tools_str,
    }
