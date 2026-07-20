"""Visualization Tool — turns SQL result rows into a renderable chart spec.

Output is a structured chart specification (not an image): the frontend (or a
BI layer) renders it. This keeps the tool deterministic, testable, and free of
plotting dependencies.
"""

from typing import Any, Dict

from tools.common import ToolContext, categorical_columns, clean_rows, numeric_columns, to_float

MAX_POINTS = 100

_TEMPORAL_HINTS = ("date", "month", "year", "week", "day", "quarter", "period", "time")


def _looks_temporal(column_name: str) -> bool:
    lowered = column_name.lower()
    return any(hint in lowered for hint in _TEMPORAL_HINTS)


def generate_chart(context: ToolContext) -> Dict[str, Any]:
    rows = clean_rows(context.rows)
    if not rows:
        return {"status": "error", "error": "No tabular data available to chart. Run the SQL branch first (sequential workflow) or refine the query."}

    numeric = numeric_columns(rows)
    categorical = categorical_columns(rows)

    if not numeric:
        return {"status": "error", "error": "Result set contains no numeric columns to plot."}

    x_col = categorical[0] if categorical else numeric[0]
    y_cols = [c for c in numeric if c != x_col] or numeric[:1]

    chart_type = "line" if _looks_temporal(x_col) else "bar"
    if not categorical and len(numeric) >= 2:
        chart_type = "scatter"

    data = []
    for r in rows[:MAX_POINTS]:
        point = {"x": str(r.get(x_col))}
        for y in y_cols:
            point[y] = to_float(r.get(y))
        data.append(point)

    return {
        "status": "success",
        "chart": {
            "type": chart_type,
            "title": f"{', '.join(y_cols)} by {x_col}",
            "x_axis": x_col,
            "series": y_cols,
            "data": data,
            "truncated": len(rows) > MAX_POINTS,
        },
    }
