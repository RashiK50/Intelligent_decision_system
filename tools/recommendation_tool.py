"""Recommendation Tool — rule-based business recommendations from result rows.

Produces structured recommendation objects; the Output Agent turns them into
prose. Rules are deliberately transparent (no LLM) so recommendations are
explainable and testable.
"""

from typing import Any, Dict, List

from tools.common import ToolContext, categorical_columns, clean_rows, column_values, linear_fit, numeric_columns, to_float


def generate_recommendations(context: ToolContext) -> Dict[str, Any]:
    rows = clean_rows(context.rows)
    if not rows:
        return {"status": "error", "error": "No analytical results available to base recommendations on."}

    numeric = numeric_columns(rows)
    if not numeric:
        return {"status": "error", "error": "No numeric metric available to base recommendations on."}

    categorical = categorical_columns(rows)
    metric = numeric[0]
    dimension = categorical[0] if categorical else None

    recommendations: List[Dict[str, Any]] = []
    values = column_values(rows, metric)
    total = sum(values)

    if dimension and values:
        ranked = sorted(
            (r for r in rows if to_float(r.get(metric)) is not None),
            key=lambda r: to_float(r.get(metric)),
            reverse=True,
        )
        top, bottom = ranked[0], ranked[-1]
        recommendations.append({
            "type": "double_down",
            "target": str(top.get(dimension)),
            "reason": f"Highest {metric} ({to_float(top.get(metric)):,.2f}). Prioritize inventory, marketing, and availability here.",
        })
        if len(ranked) > 1:
            recommendations.append({
                "type": "investigate_underperformer",
                "target": str(bottom.get(dimension)),
                "reason": f"Lowest {metric} ({to_float(bottom.get(metric)):,.2f}). Review pricing, listing quality, or discontinue.",
            })

        # Concentration risk: top 20% of categories driving >60% of the metric
        if total > 0 and len(ranked) >= 5:
            top_n = max(1, len(ranked) // 5)
            top_share = sum(to_float(r.get(metric)) for r in ranked[:top_n]) / total * 100
            if top_share > 60:
                recommendations.append({
                    "type": "concentration_risk",
                    "target": f"top {top_n} of {len(ranked)} {dimension} values",
                    "reason": f"They account for {top_share:.1f}% of {metric}. Diversify to reduce dependency risk.",
                })

    fit = linear_fit(values)
    if fit["slope"] < 0 and len(values) >= 3:
        recommendations.append({
            "type": "declining_trend",
            "target": metric,
            "reason": f"{metric} shows a downward trend across the result set. Investigate drivers before it compounds.",
        })

    if not recommendations:
        recommendations.append({
            "type": "no_action",
            "target": metric,
            "reason": "No rule triggered on this result set; metrics look balanced.",
        })

    return {
        "status": "success",
        "metric": metric,
        "dimension": dimension,
        "recommendations": recommendations,
    }
