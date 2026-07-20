"""LangGraph workflow.

Guardrail -> Intent -> Orchestrator -> Execution (fan-out/fan-in) -> Output

Execution paths (decided by the Orchestrator, never hardcoded per tool):
  - SQL only:        orchestrator -> planner -> sql_generator -> sql_validator
                     -> database_executor -> output
  - Tool only:       orchestrator -> tool_node -> output
  - Parallel:        orchestrator -> {planner-branch, tool_node} -> output
  - Sequential:      orchestrator -> planner-branch -> database_executor
                     -> tool_node -> output   (tools consume SQL rows)

The Output node is declared with defer=True: LangGraph delays it until every
active branch has finished, giving a correct fan-in regardless of branch
length. The Planner<->Validator self-correction loop is capped at 3 retries.

This module compiles the graph exactly once — no post-compile mutations.
"""

from typing import List

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agents.database_executor_agent import database_executor_agent
from agents.guardrail_agent import guardrail_agent
from agents.intent_agent import intent_agent
from agents.orchestrator_agent import orchestrator_agent
from agents.output_agent import output_agent
from agents.planner_agent import planner_agent
from agents.sql_generator_agent import sql_generator_agent
from agents.sql_validator_agent import sql_validator_agent
from agents.tool_agent import tool_executor_agent
from state import PlatformState

MAX_SQL_RETRIES = 3


# ==========================================
# Routers (pure functions -> unit-testable)
# ==========================================

def route_after_guardrail(state: PlatformState) -> str:
    if state.get("is_allowed") is True:
        return "intent"
    # Guardrail already wrote the user-facing rejection into formatted_response.
    return END


def route_after_orchestrator(state: PlatformState) -> List[str]:
    """Fan-out: return every branch that must run now."""
    tasks = state.get("required_tasks") or ["database_executor"]
    workflow = state.get("workflow") or "single_planner"

    branches: List[str] = []
    if "database_executor" in tasks:
        branches.append("planner")
    if "tool_executor" in tasks:
        # Sequential: the tool branch waits until the SQL branch finishes.
        if workflow == "sequential_planners" and "database_executor" in tasks:
            pass
        else:
            branches.append("tool_node")

    print(f"\n🚦 [ROUTER] Workflow: {workflow} | Tasks: {tasks} -> Branches: {branches or ['planner']}")
    return branches or ["planner"]


def route_after_generation(state: PlatformState) -> str:
    validation = state.get("sql_validation", {})
    if validation.get("is_valid", False) and state.get("sql_query"):
        return "sql_validator"
    if state.get("sql_retry_count", 0) >= MAX_SQL_RETRIES:
        return "output"
    return "planner"


def route_after_validation(state: PlatformState) -> str:
    validation = state.get("sql_validation", {})
    if validation.get("is_valid", False):
        return "database_executor"
    if state.get("sql_retry_count", 0) >= MAX_SQL_RETRIES:
        return "output"
    return "planner"


def route_after_database_executor(state: PlatformState) -> str:
    """Sequential mode: hand SQL rows to the tool branch; otherwise fan in."""
    workflow = state.get("workflow") or "single_planner"
    tasks = state.get("required_tasks") or []
    tools_already_ran = "tools" in (state.get("parallel_results") or {})

    if (
        workflow == "sequential_planners"
        and "tool_executor" in tasks
        and not tools_already_ran
        and state.get("execution_status") != "failed"
    ):
        return "tool_node"
    return "output"


# ==========================================
# Graph assembly (single compile)
# ==========================================

builder = StateGraph(PlatformState)

builder.add_node("guardrail", guardrail_agent)
builder.add_node("intent", intent_agent)
builder.add_node("orchestrator", orchestrator_agent)
builder.add_node("planner", planner_agent)
builder.add_node("sql_generator", sql_generator_agent)
builder.add_node("sql_validator", sql_validator_agent)
builder.add_node("database_executor", database_executor_agent)
builder.add_node("tool_node", tool_executor_agent)
# defer=True -> proper fan-in: output waits for all active branches.
builder.add_node("output", output_agent, defer=True)

builder.set_entry_point("guardrail")

builder.add_conditional_edges("guardrail", route_after_guardrail, {"intent": "intent", END: END})
builder.add_edge("intent", "orchestrator")
builder.add_conditional_edges(
    "orchestrator", route_after_orchestrator, {"planner": "planner", "tool_node": "tool_node"}
)
builder.add_edge("planner", "sql_generator")
builder.add_conditional_edges(
    "sql_generator", route_after_generation,
    {"sql_validator": "sql_validator", "planner": "planner", "output": "output"},
)
builder.add_conditional_edges(
    "sql_validator", route_after_validation,
    {"database_executor": "database_executor", "planner": "planner", "output": "output"},
)
builder.add_conditional_edges(
    "database_executor", route_after_database_executor,
    {"tool_node": "tool_node", "output": "output"},
)
builder.add_edge("tool_node", "output")
builder.add_edge("output", END)

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
