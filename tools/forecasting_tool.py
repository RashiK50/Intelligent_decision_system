"""Forecasting Tool — projects future values of a business metric.

Deterministic (least-squares trend + moving average), so results are
reproducible and unit-testable. Works on the ordered result rows produced by
the SQL branch (e.g. monthly revenue).
"""

from typing import Any, Dict

from tools.common import ToolContext, categorical_columns, clean_rows, column_values, linear_fit, numeric_columns

DEFAULT_HORIZON = 3
MAX_HORIZON = 24


def forecast_metric(context: ToolContext) -> Dict[str, Any]:
    rows = clean_rows(context.rows)
    if len(rows) < 3:
        return {
            "status": "error",
            "error": f"Forecasting needs at least 3 historical data points, got {len(rows)}. "
                     "Ensure the SQL branch returns an ordered time series (sequential workflow).",
        }

    numeric = numeric_columns(rows)
    if not numeric:
        return {"status": "error", "error": "No numeric metric column found to forecast."}

    categorical = categorical_columns(rows)
    period_col = categorical[0] if categorical else None
    metric_col = numeric[0]

    history = column_values(rows, metric_col)
    fit = linear_fit(history)
    n = len(history)

    horizon = context.entities.get("forecast_periods") or DEFAULT_HORIZON
    try:
        horizon = max(1, min(int(horizon), MAX_HORIZON))
    except (TypeError, ValueError):
        horizon = DEFAULT_HORIZON

    window = history[-3:]
    moving_avg = sum(window) / len(window)

    forecast = []
    for step in range(1, horizon + 1):
        trend_value = fit["intercept"] + fit["slope"] * (n - 1 + step)
        # Blend trend projection with the recent moving average for stability.
        blended = 0.7 * trend_value + 0.3 * moving_avg
        forecast.append({"period_ahead": step, "forecast": round(blended, 2)})

    direction = "increasing" if fit["slope"] > 0 else "decreasing" if fit["slope"] < 0 else "flat"

    return {
        "status": "success",
        "metric": metric_col,
        "period_column": period_col,
        "history_points": n,
        "method": "least_squares_trend_blended_with_moving_average",
        "trend": {"slope_per_period": round(fit["slope"], 4), "direction": direction},
        "recent_average": round(moving_avg, 2),
        "forecast": forecast,
    }
