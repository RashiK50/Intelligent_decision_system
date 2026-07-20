"""Tool Registry — extensibility contract and the fault barrier.

Key architectural guarantee under test: adding a tool = registry.register(),
zero graph changes; and one crashing tool can never take down the branch.
"""

from registry.tool_registry import ToolRegistry, ToolSpec, registry as global_registry
from tools.common import ToolContext


def make_registry_with(runner, name="dummy", **spec_kwargs) -> ToolRegistry:
    r = ToolRegistry()
    r.register(ToolSpec(name=name, description="test tool", runner=runner, **spec_kwargs))
    return r


class TestRegistration:
    def test_register_and_lookup(self):
        r = make_registry_with(lambda ctx: {"status": "success"})
        assert r.has("dummy")
        assert r.get("dummy").description == "test tool"
        assert r.names() == ["dummy"]

    def test_reregistration_overwrites(self):
        r = make_registry_with(lambda ctx: {"v": 1})
        r.register(ToolSpec(name="dummy", description="v2", runner=lambda ctx: {"v": 2}))
        assert len(r.names()) == 1
        assert r.get("dummy").description == "v2"

    def test_intent_filtering(self):
        r = ToolRegistry()
        r.register(ToolSpec(name="everywhere", description="", runner=lambda c: {}, intents=["*"]))
        r.register(ToolSpec(name="sales_only", description="", runner=lambda c: {},
                            intents=["sales_performance_analysis"]))
        names = [t.name for t in r.get_tools_for_intent("inventory_supply_analysis")]
        assert names == ["everywhere"]
        names = [t.name for t in r.get_tools_for_intent("sales_performance_analysis")]
        assert set(names) == {"everywhere", "sales_only"}

    def test_llm_menu_marks_sql_dependent_tools(self):
        r = make_registry_with(lambda c: {}, needs_sql_data=True)
        menu = r.get_tool_descriptions_for_llm("any")
        assert "dummy" in menu
        assert "sequential_planners" in menu


class TestFaultBarrier:
    def test_unknown_tool_returns_structured_error(self):
        r = ToolRegistry()
        result = r.execute("ghost", ToolContext())
        assert result["status"] == "error"
        assert "ghost" in result["error"]

    def test_raising_tool_never_propagates(self):
        def bomb(ctx):
            raise RuntimeError("kaboom")

        r = make_registry_with(bomb)
        result = r.execute("dummy", ToolContext())
        assert result["status"] == "error"
        assert "kaboom" in result["error"]
        assert result["tool"] == "dummy"

    def test_non_dict_result_is_wrapped(self):
        r = make_registry_with(lambda ctx: [1, 2, 3])
        result = r.execute("dummy", ToolContext())
        assert result["status"] == "success"
        assert result["result"] == [1, 2, 3]

    def test_tool_name_stamped_onto_result(self):
        r = make_registry_with(lambda ctx: {"status": "success", "x": 1})
        assert r.execute("dummy", ToolContext())["tool"] == "dummy"


class TestGlobalRegistry:
    """The production registry must expose the full built-in toolset."""

    EXPECTED = {
        "visualization", "forecasting", "statistical_analysis",
        "python_analytics", "recommendation", "export",
        "compare_period_over_period",
    }

    def test_all_builtin_tools_registered(self):
        assert self.EXPECTED.issubset(set(global_registry.names()))

    def test_sql_dependent_flags(self):
        assert global_registry.get("visualization").needs_sql_data is True
        assert global_registry.get("forecasting").needs_sql_data is True
        assert global_registry.get("python_analytics").needs_sql_data is False
        assert global_registry.get("compare_period_over_period").needs_sql_data is False
