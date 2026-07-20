"""Graph wiring + routers. The routers are pure functions over state, so the
entire decision surface (fan-out, sequential handoff, retry cap) is testable
without invoking a single LLM."""

from langgraph.graph import END

from graph.workflow import (
    MAX_SQL_RETRIES,
    graph,
    route_after_database_executor,
    route_after_generation,
    route_after_guardrail,
    route_after_orchestrator,
    route_after_validation,
)

EXPECTED_NODES = {
    "guardrail", "intent", "orchestrator", "planner", "sql_generator",
    "sql_validator", "database_executor", "tool_node", "output",
}


class TestGraphCompilation:
    def test_all_nodes_present(self):
        nodes = set(graph.get_graph().nodes.keys())
        assert EXPECTED_NODES.issubset(nodes)

    def test_single_compiled_graph_object(self):
        # Regression: the old module compiled once, then kept mutating the
        # builder. Importing must yield a runnable compiled graph.
        assert hasattr(graph, "ainvoke")


class TestGuardrailRouting:
    def test_allowed_goes_to_intent(self):
        assert route_after_guardrail({"is_allowed": True}) == "intent"

    def test_blocked_ends_workflow(self):
        assert route_after_guardrail({"is_allowed": False}) == END
        assert route_after_guardrail({}) == END


class TestOrchestratorFanOut:
    def test_sql_only(self):
        branches = route_after_orchestrator(
            {"required_tasks": ["database_executor"], "workflow": "single_planner"}
        )
        assert branches == ["planner"]

    def test_tool_only(self):
        branches = route_after_orchestrator(
            {"required_tasks": ["tool_executor"], "workflow": "single_planner"}
        )
        assert branches == ["tool_node"]

    def test_parallel_fans_out_both_branches(self):
        branches = route_after_orchestrator({
            "required_tasks": ["database_executor", "tool_executor"],
            "workflow": "parallel_planner",
        })
        assert set(branches) == {"planner", "tool_node"}

    def test_sequential_defers_tool_branch(self):
        branches = route_after_orchestrator({
            "required_tasks": ["database_executor", "tool_executor"],
            "workflow": "sequential_planners",
        })
        assert branches == ["planner"]  # tool_node runs after the DB executor

    def test_empty_tasks_defaults_to_planner(self):
        assert route_after_orchestrator({}) == ["planner"]


class TestSqlRetryLoop:
    def test_valid_generation_proceeds_to_validator(self):
        state = {"sql_validation": {"is_valid": True}, "sql_query": "SELECT 1"}
        assert route_after_generation(state) == "sql_validator"

    def test_failed_generation_retries_via_planner(self):
        state = {"sql_validation": {"is_valid": False}, "sql_retry_count": 1}
        assert route_after_generation(state) == "planner"

    def test_generation_retry_cap_exits_to_output(self):
        state = {"sql_validation": {"is_valid": False}, "sql_retry_count": MAX_SQL_RETRIES}
        assert route_after_generation(state) == "output"

    def test_valid_sql_proceeds_to_executor(self):
        assert route_after_validation({"sql_validation": {"is_valid": True}}) == "database_executor"

    def test_invalid_sql_loops_back_to_planner(self):
        state = {"sql_validation": {"is_valid": False}, "sql_retry_count": 0}
        assert route_after_validation(state) == "planner"

    def test_validation_retry_cap_exits_to_output(self):
        state = {"sql_validation": {"is_valid": False}, "sql_retry_count": MAX_SQL_RETRIES}
        assert route_after_validation(state) == "output"


class TestSequentialHandoff:
    def test_sequential_hands_rows_to_tool_node(self):
        state = {
            "workflow": "sequential_planners",
            "required_tasks": ["database_executor", "tool_executor"],
            "parallel_results": {"database_executor": [{"a": 1}]},
            "execution_status": "success",
        }
        assert route_after_database_executor(state) == "tool_node"

    def test_non_sequential_goes_straight_to_output(self):
        state = {
            "workflow": "single_planner",
            "required_tasks": ["database_executor"],
            "parallel_results": {},
        }
        assert route_after_database_executor(state) == "output"

    def test_failed_sql_branch_skips_tools(self):
        state = {
            "workflow": "sequential_planners",
            "required_tasks": ["database_executor", "tool_executor"],
            "parallel_results": {"database_executor": None},
            "execution_status": "failed",
        }
        assert route_after_database_executor(state) == "output"

    def test_tools_never_run_twice(self):
        state = {
            "workflow": "sequential_planners",
            "required_tasks": ["database_executor", "tool_executor"],
            "parallel_results": {"database_executor": [{"a": 1}], "tools": {}},
            "execution_status": "success",
        }
        assert route_after_database_executor(state) == "output"
