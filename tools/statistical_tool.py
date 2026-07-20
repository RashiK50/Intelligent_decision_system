"""Statistical Analysis Tool — descriptive stats, correlation, trend detection.

Pure-Python (statistics module) implementation: deterministic, dependency-free,
independently testable.
"""

import statistics
from typing import Any, Dict, List

from tools.common import ToolContext, clean_rows, column_values, linear_fit, numeric_columns


def _pearson(xs: List[float], ys: List[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 3:
        return 0.0
    xs, ys = xs[:n], ys[:n]
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / (var_x ** 0.5 * var_y ** 0.5)


def analyze_statistics(context: ToolContext) -> Dict[str, Any]:
    rows = clean_rows(context.rows)
    if not rows:
        return {"status": "error", "error": "No data rows available for statistical analysis."}

    numeric = numeric_columns(rows)
    if not numeric:
        return {"status": "error", "error": "No numeric columns available for statistical analysis."}

    summary: Dict[str, Any] = {}
    for col in numeric:
        values = column_values(rows, col)
        if not values:
            continue
        summary[col] = {
            "count": len(values),
            "mean": round(statistics.fmean(values), 4),
            "median": round(statistics.median(values), 4),
            "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
        }

    correlations = []
    for i, a in enumerate(numeric):
        for b in numeric[i + 1:]:
            r = _pearson(column_values(rows, a), column_values(rows, b))
            correlations.append({
                "columns": [a, b],
                "pearson_r": round(r, 4),
                "strength": (
                    "strong" if abs(r) >= 0.7 else
                    "moderate" if abs(r) >= 0.4 else
                    "weak"
                ),
            })

    primary = numeric[0]
    fit = linear_fit(column_values(rows, primary))
    trend = {
        "column": primary,
        "slope_per_row": round(fit["slope"], 4),
        "direction": "increasing" if fit["slope"] > 0 else "decreasing" if fit["slope"] < 0 else "flat",
    }

    return {
        "status": "success",
        "row_count": len(rows),
        "summary": summary,
        "correlations": correlations,
        "trend": trend,
    }
