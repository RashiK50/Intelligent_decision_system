"""Python Analytics Tool — business KPI calculations over result rows.

Computes totals, averages, contribution shares, and (when the Intent Agent
extracted current/previous values) period-over-period growth.
"""

from typing import Any, Dict

from tools.common import ToolContext, categorical_columns, clean_rows, column_values, numeric_columns, to_float


def compute_kpis(context: ToolContext) -> Dict[str, Any]:
    rows = clean_rows(context.rows)
    entities = context.entities or {}

    result: Dict[str, Any] = {"status": "success", "kpis": {}}

    # Period-over-period growth from extracted entities (works without SQL rows)
    current = to_float(entities.get("current_value"))
    previous = to_float(entities.get("previous_value"))
    if current is not None and previous is not None:
        metric = entities.get("metric", "metric")
        if previous == 0:
            growth = None
            narrative = f"{metric} grew from 0 to {current:,.2f} (new growth)."
        else:
            growth = round((current - previous) / abs(previous) * 100, 2)
            narrative = f"{metric} changed {growth:+.2f}% (current {current:,.2f} vs previous {previous:,.2f})."
        result["kpis"]["period_over_period"] = {
            "metric": metric,
            "current": current,
            "previous": previous,
            "growth_pct": growth,
            "explanation": narrative,
        }

    if not rows:
        if not result["kpis"]:
            return {"status": "error", "error": "No data rows and no numeric entities available for KPI calculation."}
        return result

    numeric = numeric_columns(rows)
    if not numeric:
        return result if result["kpis"] else {"status": "error", "error": "No numeric columns for KPI calculation."}

    primary = numeric[0]
    values = column_values(rows, primary)
    total = sum(values)
    result["kpis"]["primary_metric"] = {
        "column": primary,
        "total": round(total, 2),
        "average": round(total / len(values), 2) if values else 0,
        "max": max(values) if values else None,
        "min": min(values) if values else None,
        "row_count": len(rows),
    }

    # Contribution share per category (top 10)
    categorical = categorical_columns(rows)
    if categorical and total:
        cat = categorical[0]
        contributions = []
        for r in rows[:10]:
            v = to_float(r.get(primary))
            if v is not None:
                contributions.append({
                    "category": str(r.get(cat)),
                    "value": v,
                    "share_pct": round(v / total * 100, 2),
                })
        result["kpis"]["contribution"] = {
            "dimension": cat,
            "metric": primary,
            "top": contributions,
        }

    return result
