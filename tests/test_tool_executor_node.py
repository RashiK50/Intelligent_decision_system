"""Tool Executor node — integration between graph state and the registry.

Runs the real async node with real registered tools; still fully offline
(no LLM, no database)."""

import asyncio

from agents.tool_agent import _build_context, _select_tools, tool_executor_agent


def run(state: dict) -> dict:
    return asyncio.run(tool_executor_agent(state))


class TestContextBuilding:
    def test_rows_flow_from_database_branch(self):
        state = {
            "user_query": "q",
            "intent": "sales_performance_analysis",
            "entities": {"x": 1},
            "parallel_results": {"database_executor": [{"revenue": 10}]},
            "plan": {"directive": "d"},
        }
        ctx = _build_context(state)
        assert ctx.rows == [{"revenue": 10}]
        assert ctx.entities == {"x": 1}

    def test_missing_keys_are_safe(self):
        ctx = _build_context({})
        assert ctx.rows is None
        assert ctx.entities == {}


class TestToolSelection:
    def test_orchestrator_selection_wins(self):
        state = {"required_tools": ["forecasting"], "intent": "anything"}
        assert _select_tools(state) == ["forecasting"]

    def test_unknown_requested_tools_are_dropped(self):
        state = {
            "required_tools": ["not_registered"],
            "intent": "general",
            "entities": {"current_value": 5, "previous_value": 4},
        }
        assert _select_tools(state) == ["compare_period_over_period"]


class TestNodeExecution:
    def test_kpi_tool_end_to_end(self):
        state = {
            "user_query": "How did revenue change?",
            "intent": "sales_performance_analysis",
            "entities": {"current_value": 120, "previous_value": 100, "metric": "Revenue"},
            "required_tools": ["python_analytics"],
            "parallel_results": {},
        }
        update = run(state)
        tools = update["parallel_results"]["tools"]
        assert tools["python_analytics"]["status"] == "success"
        assert tools["python_analytics"]["kpis"]["period_over_period"]["growth_pct"] == 20.0
        assert update["execution_status"] == "success"

    def test_sequential_rows_reach_sql_dependent_tool(self):
        rows = [
            {"month": "2018-01", "revenue": 100.0},
            {"month": "2018-02", "revenue": 110.0},
            {"month": "2018-03", "revenue": 120.0},
        ]
        state = {
            "user_query": "forecast revenue",
            "intent": "sales_performance_analysis",
            "entities": {},
            "required_tools": ["forecasting"],
            "parallel_results": {"database_executor": rows},
        }
        update = run(state)
        result = update["parallel_results"]["tools"]["forecasting"]
        assert result["status"] == "success"
        assert result["trend"]["direction"] == "increasing"

    def test_all_tools_failing_marks_branch_failed(self):
        # visualization needs SQL rows; none provided -> structured error
        state = {
            "user_query": "chart it",
            "intent": "general",
            "entities": {},
            "required_tools": ["visualization"],
            "parallel_results": {},
        }
        update = run(state)
        assert update["parallel_results"]["tools"]["visualization"]["status"] == "error"
        assert update["execution_status"] == "failed"
        assert update["error_message"]  # surfaced for the Output Agent
