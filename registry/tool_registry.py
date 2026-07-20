"""Tool Registry — the single place where executable tools are declared.

Adding a new tool NEVER requires touching the LangGraph workflow:

    registry.register(ToolSpec(
        name="my_tool",
        description="What it does — the Orchestrator reads this.",
        intents=["*"],                      # or specific intents
        runner=my_module.my_function,        # (ToolContext) -> dict
    ))

The generic Tool Executor node looks tools up by name at runtime, builds a
ToolContext from graph state, executes each runner inside a fault barrier,
and merges structured results into state. The Orchestrator selects tools
dynamically from the descriptions exposed by this registry.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from tools.common import ToolContext
from tools.analytics_tool import compute_kpis
from tools.export_tool import export_results
from tools.forecasting_tool import forecast_metric
from tools.recommendation_tool import generate_recommendations
from tools.sales_tools import compare_period_over_period
from tools.statistical_tool import analyze_statistics
from tools.visualization_tool import generate_chart

logger = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    name: str
    description: str
    runner: Callable[[ToolContext], Dict[str, Any]]
    intents: List[str] = field(default_factory=lambda: ["*"])
    needs_sql_data: bool = False  # hint for the Orchestrator: run SQL first (sequential)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    # ------------------------------------------------------------------
    # Registration & lookup
    # ------------------------------------------------------------------
    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            logger.warning("Tool '%s' re-registered; overwriting previous spec.", spec.name)
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def get_tools_for_intent(self, intent: str) -> List[ToolSpec]:
        return [
            t for t in self._tools.values()
            if "*" in t.intents or intent in t.intents
        ]

    def get_tool_descriptions_for_llm(self, intent: str) -> str:
        """Menu of tool names + descriptions injected into the Orchestrator prompt."""
        tools = self.get_tools_for_intent(intent)
        if not tools:
            return "No external tools available."
        lines = []
        for t in tools:
            suffix = " (requires SQL data first — use sequential_planners)" if t.needs_sql_data else ""
            lines.append(f"- {t.name}: {t.description}{suffix}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Fault-tolerant execution
    # ------------------------------------------------------------------
    def execute(self, name: str, context: ToolContext) -> Dict[str, Any]:
        """Run one tool. Never raises: failures come back as structured errors."""
        spec = self._tools.get(name)
        if spec is None:
            return {"tool": name, "status": "error", "error": f"Unknown tool '{name}'. Available: {self.names()}"}
        try:
            result = spec.runner(context)
            if not isinstance(result, dict):
                result = {"status": "success", "result": result}
            result.setdefault("tool", name)
            return result
        except Exception as e:  # fault barrier: one bad tool must not kill the branch
            logger.exception("Tool '%s' raised", name)
            return {"tool": name, "status": "error", "error": str(e)}


# ----------------------------------------------------------------------
# Runner adapters for tools that predate ToolContext
# ----------------------------------------------------------------------

def _run_period_comparison(context: ToolContext) -> Dict[str, Any]:
    entities = context.entities or {}
    current = entities.get("current_value")
    previous = entities.get("previous_value")
    if current is None or previous is None:
        return {
            "status": "error",
            "error": "compare_period_over_period needs 'current_value' and 'previous_value' entities from the query.",
        }
    try:
        text = compare_period_over_period.invoke({
            "metric": str(entities.get("metric", "Revenue")),
            "current_value": float(current),
            "previous_value": float(previous),
        })
        return {"status": "success", "comparison": text}
    except (TypeError, ValueError) as e:
        return {"status": "error", "error": f"Could not convert extracted values to numbers: {e}"}


# ----------------------------------------------------------------------
# Global registry instance + built-in tool registration
# ----------------------------------------------------------------------

registry = ToolRegistry()

registry.register(ToolSpec(
    name="visualization",
    description="Generate a chart specification (bar/line/scatter) from SQL result rows for dashboards.",
    runner=generate_chart,
    needs_sql_data=True,
))
registry.register(ToolSpec(
    name="forecasting",
    description="Predict future values of a business metric (sales, revenue, demand) from an ordered time series.",
    runner=forecast_metric,
    needs_sql_data=True,
))
registry.register(ToolSpec(
    name="statistical_analysis",
    description="Descriptive statistics, correlation analysis, and trend detection over SQL result rows.",
    runner=analyze_statistics,
    needs_sql_data=True,
))
registry.register(ToolSpec(
    name="python_analytics",
    description="Business KPI calculations: totals, averages, contribution shares, period-over-period growth.",
    runner=compute_kpis,
))
registry.register(ToolSpec(
    name="recommendation",
    description="Generate rule-based business recommendations (double-down, underperformers, concentration risk) from analytical results.",
    runner=generate_recommendations,
    needs_sql_data=True,
))
registry.register(ToolSpec(
    name="export",
    description="Export result rows to a downloadable CSV or Excel report file.",
    runner=export_results,
    needs_sql_data=True,
))
registry.register(ToolSpec(
    name="compare_period_over_period",
    description="Percentage growth/decline between two numbers the user supplied directly in the question.",
    runner=_run_period_comparison,
    intents=["sales_performance_analysis", "*"],
))
