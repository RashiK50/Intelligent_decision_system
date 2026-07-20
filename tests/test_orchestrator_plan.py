"""Orchestrator output schema + deterministic plan normalization.

The first class is the regression suite for the original production blocker:
the LLM omitting `required_tables` caused a Pydantic ValidationError (400).
Every field must now tolerate being absent.
"""

from agents.orchestrator_agent import (
    OrchestratorOutput,
    fallback_plan,
    normalize_plan,
)


class TestOrchestratorOutputDefaults:
    def test_empty_payload_validates(self):
        """THE blocker: a bare/partial LLM response must never raise."""
        out = OrchestratorOutput.model_validate({})
        assert out.workflow_type == "single_planner"
        assert out.required_tables == []
        assert out.required_tasks == []
        assert out.required_tools == []
        assert out.execution_plan == ""

    def test_missing_required_tables_specifically(self):
        out = OrchestratorOutput.model_validate(
            {"workflow_type": "parallel_planner", "required_tasks": ["database_executor"]}
        )
        assert out.required_tables == []
        assert out.workflow_type == "parallel_planner"

    def test_workflow_alias_normalization(self):
        assert OrchestratorOutput(workflow_type="parallel_planners").workflow_type == "parallel_planner"
        assert OrchestratorOutput(workflow_type="sequential_planner").workflow_type == "sequential_planners"
        assert OrchestratorOutput(workflow_type="SEQUENTIAL_PLANNERS").workflow_type == "sequential_planners"

    def test_garbage_workflow_falls_back(self):
        assert OrchestratorOutput(workflow_type="banana").workflow_type == "single_planner"
        assert OrchestratorOutput.model_validate({"workflow_type": 42}).workflow_type == "single_planner"


class TestNormalizePlan:
    def test_unknown_tables_and_tools_filtered(self):
        out = OrchestratorOutput(
            required_tables=["orders", "not_a_table"],
            required_tools=["visualization", "not_a_tool"],
            required_tasks=["database_executor", "bogus_task"],
        )
        fixed = normalize_plan(out, "sales_performance_analysis")
        assert fixed.required_tables == ["orders"]
        assert fixed.required_tools == ["visualization"]
        assert "bogus_task" not in fixed.required_tasks

    def test_tools_selected_implies_tool_executor_task(self):
        out = OrchestratorOutput(
            required_tools=["forecasting"], required_tasks=["database_executor"]
        )
        fixed = normalize_plan(out, "sales_performance_analysis")
        assert "tool_executor" in fixed.required_tasks

    def test_empty_plan_defaults_to_sql_run(self):
        fixed = normalize_plan(OrchestratorOutput(), "general")
        assert fixed.required_tasks == ["database_executor"]

    def test_sql_consuming_tool_forces_sequential(self):
        out = OrchestratorOutput(
            workflow_type="parallel_planner",
            required_tasks=["database_executor", "tool_executor"],
            required_tools=["visualization"],  # needs_sql_data=True
        )
        fixed = normalize_plan(out, "sales_performance_analysis")
        assert fixed.workflow_type == "sequential_planners"

    def test_independent_tool_plus_sql_becomes_parallel(self):
        out = OrchestratorOutput(
            workflow_type="single_planner",
            required_tasks=["database_executor", "tool_executor"],
            required_tools=["compare_period_over_period"],  # needs_sql_data=False
        )
        fixed = normalize_plan(out, "sales_performance_analysis")
        assert fixed.workflow_type == "parallel_planner"

    def test_tool_only_plan_is_single_planner(self):
        out = OrchestratorOutput(
            workflow_type="sequential_planners",
            required_tasks=["tool_executor"],
            required_tools=["compare_period_over_period"],
        )
        fixed = normalize_plan(out, "sales_performance_analysis")
        assert fixed.workflow_type == "single_planner"
        assert fixed.required_tasks == ["tool_executor"]


class TestFallbackPlan:
    def test_fallback_always_runs_sql(self):
        plan = fallback_plan("sales_performance_analysis")
        assert plan.required_tasks == ["database_executor"]
        assert plan.workflow_type == "single_planner"
        assert plan.required_tools == []
