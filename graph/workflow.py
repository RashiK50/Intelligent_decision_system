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
from agents.tool_agent import tool_executor_agent # Ensure this is imported
from langgraph.constants import Send

def route_after_guardrail(state: PlatformState) -> str:
    if state.get("is_allowed") is True:
        return "intent"
    return "output"

def route_after_validation(state: PlatformState) -> str:
    validation_data = state.get("sql_validation", {})
    is_valid = validation_data.get("is_valid", False)
    retry_count = state.get("sql_retry_count", 0)
    if is_valid:
        return "database_executor"
    if retry_count >= 3:
        return "output"
    return "planner"

builder = StateGraph(PlatformState)

def route_after_orchestrator(state: PlatformState) -> str:
    intent = state.get("intent")
    workflow_type = state.get("workflow_type", state.get("workflow", "single_planner"))
    
    print(f"\n🚦 [ROUTER] Evaluated Intent: {intent} | Orchestrator Suggested: {workflow_type}")
    
    # 🚨 CHANGE 1: Look for the new Sales intent, not inventory
    if intent == "sales_performance_analysis":
        print("🚦 [ROUTER] Override triggered! Forcing route to Python Sales Tool Node...")
        return "tool_node"
        
    elif workflow_type == "tool_execution":
        print("🚦 [ROUTER] Routing to Python Tool Node...")
        return "tool_node" 
        
    else:
        print("🚦 [ROUTER] Routing to SQL Planner...")
        return "planner"

# --- NODES ---
builder.add_node("guardrail", guardrail_agent)
builder.add_node("intent", intent_agent)
builder.add_node("orchestrator", orchestrator_agent)
builder.add_node("planner", planner_agent)
builder.add_node("sql_generator", sql_generator_agent)
builder.add_node("sql_validator", sql_validator_agent)
builder.add_node("database_executor", database_executor_agent)
builder.add_node("output", output_agent)
builder.add_node("tool_node", tool_executor_agent) # 1. Registered Node

# --- EDGES ---
builder.set_entry_point("guardrail")

builder.add_conditional_edges(
    "guardrail", route_after_guardrail,
    {"intent": "intent", "output": "output"}
)

builder.add_edge("intent", "orchestrator")

# 2. Updated conditional edge mapping
builder.add_conditional_edges(
    "orchestrator", route_after_orchestrator,
    {"planner": "planner", "tool_node": "tool_node"}
)

# 3. Fixed Typo "sql_gfenerator" -> "sql_generator"
builder.add_edge("planner", "sql_generator") 

def route_after_generation(state: PlatformState) -> str:
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
    "sql_generator", route_after_generation,
    {"sql_validator": "sql_validator", "planner": "planner", "output": "output"}
)

builder.add_conditional_edges(
    "sql_validator", route_after_validation,
    {"database_executor": "database_executor", "planner": "planner", "output": "output"}
)

# 4. Added missing edge for the tool path
builder.add_edge("tool_node", "output")
builder.add_edge("database_executor", "output")
builder.add_edge("output", END)

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

def parallel_router(state: PlatformState):
    """
    Orchestrator's decision logic: Fan-out to multiple nodes.
    """
    tasks = []
    # If the LLM Orchestrator planned a tool call, add it
    if "tool_executor" in state.get("required_tools", []):
        tasks.append(Send("tool_node", state))
        
    # If the LLM Orchestrator planned a SQL query, add it
    if "database_executor" in state.get("required_sql", False):
        tasks.append(Send("database_executor", state))
        
    return tasks

# In your builder definition:
# Remove the old add_edge("orchestrator", "planner")
# Replace with:
builder.add_conditional_edges("orchestrator", parallel_router)

# Ensure both nodes lead back to the Output Node for 'Fan-In'
builder.add_edge("tool_node", "output")
builder.add_edge("database_executor", "output")