"""Generic Tool Executor node.

Runs every tool the Orchestrator selected (state['required_tools']) through
the Tool Registry. Tool lookup is dynamic — registering a new tool makes it
available here with zero changes to this file or the graph.

Results are structured dicts merged into state['parallel_results']['tools'];
the Output Agent synthesizes the final narrative.
"""

from state import PlatformState
from registry.tool_registry import registry
from tools.common import ToolContext
from utils.logger import get_node_logger, log_node

logger = get_node_logger("tool_executor")


def _build_context(state: PlatformState) -> ToolContext:
    parallel_results = state.get("parallel_results") or {}
    return ToolContext(
        user_query=state.get("user_query", ""),
        intent=state.get("intent"),
        entities=state.get("entities") or {},
        rows=parallel_results.get("database_executor"),
        plan=state.get("plan") or {},
    )


def _select_tools(state: PlatformState) -> list:
    """Prefer the Orchestrator's explicit selection; fall back to intent mapping."""
    requested = [t for t in (state.get("required_tools") or []) if registry.has(t)]
    if requested:
        return requested

    intent = state.get("intent") or ""
    entities = state.get("entities") or {}
    # Heuristic fallback: user-supplied numbers -> comparison; otherwise KPIs.
    if entities.get("current_value") is not None and entities.get("previous_value") is not None:
        return ["compare_period_over_period"]
    fallback = registry.get_tools_for_intent(intent)
    return [fallback[0].name] if fallback else []


@log_node("tool_executor")
async def tool_executor_agent(state: PlatformState) -> dict:
    print("\n==================================================")
    print(" 🛠️ [TOOL EXECUTOR NODE] Executing Tools...")
    print("==================================================")

    context = _build_context(state)
    tool_names = _select_tools(state)

    if not tool_names:
        logger.warning("No tools selected or available for intent '%s'", state.get("intent"))
        return {
            "parallel_results": {"tools": {"_notice": "No applicable tool found for this request."}},
            "execution_status": "success",
        }

    tool_outputs = {}
    any_success = False
    for name in tool_names:
        print(f" 🛠️ [TOOL EXECUTOR NODE] Running '{name}'...")
        result = registry.execute(name, context)  # never raises
        tool_outputs[name] = result
        if result.get("status") == "success":
            any_success = True
            print(f"   ✅ '{name}' succeeded")
        else:
            print(f"   ⚠️ '{name}' reported: {result.get('error')}")

    print("--------------------------------------------------")

    return {
        "parallel_results": {"tools": tool_outputs},
        "execution_status": "success" if (any_success or not tool_outputs) else "failed",
        "error_message": None if any_success else "; ".join(
            f"{n}: {r.get('error')}" for n, r in tool_outputs.items() if r.get("status") != "success"
        ) or None,
    }
