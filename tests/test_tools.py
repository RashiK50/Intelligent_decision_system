"""Analytical tools — deterministic units, structured in/out, no LLM."""

import csv
import os

import pytest

from tools.analytics_tool import compute_kpis
from tools.common import (
    ToolContext,
    clean_rows,
    linear_fit,
    numeric_columns,
    categorical_columns,
    to_float,
)
from tools.forecasting_tool import forecast_metric
from tools.recommendation_tool import generate_recommendations
from tools.statistical_tool import analyze_statistics
from tools.visualization_tool import generate_chart

SALES_ROWS = [
    {"month": "2018-01", "revenue": 100.0},
    {"month": "2018-02", "revenue": 110.0},
    {"month": "2018-03", "revenue": 120.0},
    {"month": "2018-04", "revenue": 130.0},
]

CATEGORY_ROWS = [
    {"category": "toys", "revenue": 500.0},
    {"category": "books", "revenue": 300.0},
    {"category": "garden", "revenue": 200.0},
]


class TestCommonHelpers:
    def test_clean_rows_drops_system_warning(self):
        rows = SALES_ROWS + [{"SYSTEM_WARNING": "truncated"}]
        assert clean_rows(rows) == SALES_ROWS
        assert clean_rows(None) == []

    def test_to_float_coercions(self):
        from decimal import Decimal

        assert to_float(Decimal("2.5")) == 2.5
        assert to_float("1,234.5") == 1234.5
        assert to_float(True) is None  # bools are not metrics
        assert to_float(None) is None
        assert to_float("not a number") is None

    def test_column_classification(self):
        assert numeric_columns(SALES_ROWS) == ["revenue"]
        assert categorical_columns(SALES_ROWS) == ["month"]

    def test_linear_fit_recovers_slope(self):
        fit = linear_fit([1.0, 2.0, 3.0, 4.0])
        assert fit["slope"] == pytest.approx(1.0)
        assert fit["intercept"] == pytest.approx(1.0)

    def test_linear_fit_degenerate_inputs(self):
        assert linear_fit([]) == {"slope": 0.0, "intercept": 0.0}
        assert linear_fit([7.0])["intercept"] == 7.0


class TestVisualizationTool:
    def test_temporal_axis_yields_line_chart(self):
        result = generate_chart(ToolContext(rows=SALES_ROWS))
        assert result["status"] == "success"
        chart = result["chart"]
        assert chart["type"] == "line"
        assert chart["x_axis"] == "month"
        assert chart["series"] == ["revenue"]
        assert len(chart["data"]) == 4

    def test_categorical_axis_yields_bar_chart(self):
        result = generate_chart(ToolContext(rows=CATEGORY_ROWS))
        assert result["chart"]["type"] == "bar"

    def test_no_rows_is_structured_error(self):
        result = generate_chart(ToolContext(rows=None))
        assert result["status"] == "error"

    def test_no_numeric_columns_is_error(self):
        result = generate_chart(ToolContext(rows=[{"name": "a"}, {"name": "b"}]))
        assert result["status"] == "error"


class TestForecastingTool:
    def test_upward_series_forecasts_higher_values(self):
        result = forecast_metric(ToolContext(rows=SALES_ROWS))
        assert result["status"] == "success"
        assert result["trend"]["direction"] == "increasing"
        assert len(result["forecast"]) == 3  # DEFAULT_HORIZON
        assert result["forecast"][0]["forecast"] > 120.0

    def test_horizon_from_entities(self):
        result = forecast_metric(
            ToolContext(rows=SALES_ROWS, entities={"forecast_periods": 6})
        )
        assert len(result["forecast"]) == 6

    def test_insufficient_history_is_error(self):
        result = forecast_metric(ToolContext(rows=SALES_ROWS[:2]))
        assert result["status"] == "error"
        assert "3" in result["error"]


class TestStatisticalTool:
    def test_descriptive_stats_over_rows(self):
        result = analyze_statistics(ToolContext(rows=SALES_ROWS))
        assert result["status"] == "success"

    def test_empty_rows_is_error(self):
        assert analyze_statistics(ToolContext(rows=[]))["status"] == "error"


class TestAnalyticsTool:
    def test_period_over_period_from_entities_only(self):
        ctx = ToolContext(entities={
            "current_value": 120, "previous_value": 100, "metric": "Revenue",
        })
        result = compute_kpis(ctx)
        assert result["status"] == "success"
        pop = result["kpis"]["period_over_period"]
        assert pop["growth_pct"] == pytest.approx(20.0)

    def test_zero_previous_value_does_not_divide(self):
        ctx = ToolContext(entities={"current_value": 50, "previous_value": 0})
        result = compute_kpis(ctx)
        assert result["kpis"]["period_over_period"]["growth_pct"] is None

    def test_kpis_from_rows(self):
        result = compute_kpis(ToolContext(rows=CATEGORY_ROWS))
        primary = result["kpis"]["primary_metric"]
        assert primary["total"] == pytest.approx(1000.0)
        assert primary["average"] == pytest.approx(333.33, abs=0.01)
        contribution = result["kpis"]["contribution"]["top"]
        assert contribution[0]["share_pct"] == pytest.approx(50.0)

    def test_nothing_to_compute_is_error(self):
        assert compute_kpis(ToolContext())["status"] == "error"


class TestRecommendationTool:
    def test_recommendations_from_category_rows(self):
        result = generate_recommendations(ToolContext(rows=CATEGORY_ROWS))
        assert result["status"] == "success"
        assert len(result["recommendations"]) >= 1

    def test_no_rows_is_error(self):
        assert generate_recommendations(ToolContext(rows=[]))["status"] == "error"


class TestExportTool:
    def test_csv_export_roundtrip(self, tmp_path, monkeypatch):
        import tools.export_tool as export_tool

        monkeypatch.setattr(export_tool, "EXPORT_DIR", str(tmp_path))
        result = export_tool.export_results(
            ToolContext(user_query="monthly revenue", rows=SALES_ROWS)
        )
        assert result["status"] == "success"
        assert result["format"] == "csv"
        assert result["rows"] == 4
        with open(result["path"], newline="", encoding="utf-8") as f:
            read_back = list(csv.DictReader(f))
        assert len(read_back) == 4
        assert read_back[0]["month"] == "2018-01"

    def test_xlsx_export_when_openpyxl_present(self, tmp_path, monkeypatch):
        import tools.export_tool as export_tool

        monkeypatch.setattr(export_tool, "EXPORT_DIR", str(tmp_path))
        result = export_tool.export_results(
            ToolContext(
                user_query="monthly revenue",
                rows=SALES_ROWS,
                entities={"export_format": "xlsx"},
            )
        )
        assert result["status"] == "success"
        assert result["format"] in ("xlsx", "csv")  # csv = graceful fallback
        assert os.path.exists(result["path"])

    def test_no_rows_is_error(self):
        from tools.export_tool import export_results

        assert export_results(ToolContext(rows=[]))["status"] == "error"
