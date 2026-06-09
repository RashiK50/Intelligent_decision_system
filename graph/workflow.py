from langgraph.graph import StateGraph, END
from agents.intent_agent import intent_agent
from agents.planner_agent import planner_agent
from agents.sql_generator_agent import sql_generator_agent
from agents.sql_validator_agent import sql_validator_agent
from agents.database_executor_agent import database_executor_agent
from agents.output_agent import output_agent
from state.agent_state import AgentState

builder = StateGraph(AgentState)

builder.add_node(
    "intent",
    intent_agent
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
    "intent"
)

builder.add_edge(
    "intent",
    "planner"
)

builder.add_edge(
    "planner",
    "sql_generator"
)

builder.add_edge(
    "sql_generator",
    "sql_validator"
)

builder.add_edge(
    "sql_validator",
    "database_executor"
)

builder.add_edge(
    "database_executor",
    "output"
)

builder.add_edge(
    "output",
    END
)

graph = builder.compile()