from langgraph.graph import StateGraph, END
from agents.intent_agent import intent_agent
from agents.planner_agent import planner_agent
from agents.sql_generator_agent import sql_generator_agent
from agents.sql_validator_agent import sql_validator_agent
from agents.database_executor_agent import database_executor_agent
from agents.output_agent import output_agent
from state import PlatformState
from agents.guardrail_agent import guardrail_agent
from agents.orchestrator_agent import orchestrator_agent

def route_after_guardrail(state: PlatformState) -> str:
    """Routes to intent agent if allowed, otherwise skips directly to output."""
    if state.get("is_allowed") is True:
        return "intent"
    return "output"

def route_after_validation(state: PlatformState) -> str:
    """Loops back to generator if SQL is invalid, unless max retries reached."""
    validation_data = state.get("sql_validation", {})
    is_valid = validation_data.get("is_valid", False)
    retry_count = state.get("sql_retry_count", 0)
    
    if is_valid:
        return "database_executor"
    
    # Fallback/Self-healing Loop constraint to prevent infinite API calling
    if retry_count >= 3:
        return "output" # Go to output to print failure details safely
        
    return "planner"

builder = StateGraph(PlatformState)

def route_after_orchestrator(state: PlatformState) -> str:
    """
    Reads the workflow_type decided by the Orchestrator and routes accordingly.
    """
    # Grab the correct state variable (ensure this matches what your Orchestrator outputs)
    workflow_type = state.get("workflow_type", state.get("workflow", "single_planner"))
    
    print(f"\n [ROUTER] Orchestrator selected workflow: {workflow_type}")
    
    # 1. THE NEW TOOL ROUTE
    if workflow_type == "tool_execution":
        print(" [ROUTER] Routing to Python Tool Node...")
        return "tool_node"  # <--- Note: Ensure your graph.add_node() uses this exact string!
        
    # 2. THE SQL PLANNER ROUTES
    elif workflow_type == "parallel_planners":
        print(" [ROUTER] Parallel planners selected (Defaulting to single planner for MVP)")
        return "planner"
    elif workflow_type == "sequential_planners":
        print(" [ROUTER] Sequential planners selected (Defaulting to single planner for MVP)")
        return "planner"
    else:
        print(" [ROUTER] Defaulting to single planner...")
        return "planner"

builder.add_node(
    "guardrail",
    guardrail_agent
)

builder.add_node(
    "intent",
    intent_agent
)

builder.add_node(
    "orchestrator",
    orchestrator_agent
)

builder.add_node(
    "planner",
    planner_agent
)

builder.add_node(
    "sql_generator",
    sql_generator_agent
)

builder.add_node(
    "sql_validator",
    sql_validator_agent
)

builder.add_node(
    "database_executor",
    database_executor_agent
)

builder.add_node(
    "output",
    output_agent
)

builder.set_entry_point(
    "guardrail"
)

builder.add_conditional_edges(
    "guardrail",
    route_after_guardrail,
    {
        "intent": "intent",
        "output": "output"
    }
)

builder.add_edge(
    "intent",
    "orchestrator"
)

builder.add_conditional_edges(
    "orchestrator",
    route_after_orchestrator,
    {
        "planner": "planner"
        # "parallel_planner": "parallel_planner" # Future scope
    }
)

builder.add_edge(
    "planner",
    "sql_generator"
)

def route_after_generation(state: PlatformState) -> str:
    """If SQL Generator failed to compile (empty query / is_valid False),
    skip the Validator entirely and route straight into the same
    retry/output logic used after validation failures."""
    validation_data = state.get("sql_validation", {})
    is_valid = validation_data.get("is_valid", False)
    sql_query = state.get("sql_query", "")

    if is_valid and sql_query:
        return "sql_validator"

    retry_count = state.get("sql_retry_count", 0)
    if retry_count >= 3:
        return "output"
    return "planner"

builder.add_conditional_edges(
    "sql_generator",
    route_after_generation,
    {
        "sql_validator": "sql_validator",
        "planner": "planner",
        "output": "output"
    }
)

builder.add_conditional_edges(
    "sql_validator",
    route_after_validation,
    {
        "database_executor": "database_executor",
        "planner": "planner",
        "output": "output"
    }
)

builder.add_edge(
    "database_executor",
    "output"
)

builder.add_edge(
    "output",
    END
)

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)