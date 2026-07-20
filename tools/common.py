"""Shared helpers for analytical tools.

Tools receive a ToolContext (structured input) and must return a plain dict
(structured output). They never produce user-facing prose — the Output Agent
owns final synthesis.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class ToolContext:
    """Structured input handed to every tool by the Tool Executor node."""
    user_query: str = ""
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    rows: Optional[List[Dict[str, Any]]] = None  # SQL branch output, if any
    plan: Dict[str, Any] = field(default_factory=dict)


def clean_rows(rows: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Drop truncation-warning records injected by the Database Executor."""
    if not rows:
        return []
    return [r for r in rows if isinstance(r, dict) and "SYSTEM_WARNING" not in r]


def to_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    return None


def numeric_columns(rows: List[Dict[str, Any]]) -> List[str]:
    """Columns where every non-null value is numeric (order preserved)."""
    if not rows:
        return []
    columns = list(rows[0].keys())
    result = []
    for col in columns:
        values = [r.get(col) for r in rows if r.get(col) is not None]
        if values and all(to_float(v) is not None for v in values):
            result.append(col)
    return result


def categorical_columns(rows: List[Dict[str, Any]]) -> List[str]:
    if not rows:
        return []
    numeric = set(numeric_columns(rows))
    return [c for c in rows[0].keys() if c not in numeric]


def column_values(rows: List[Dict[str, Any]], col: str) -> List[float]:
    values = []
    for r in rows:
        f = to_float(r.get(col))
        if f is not None:
            values.append(f)
    return values


def linear_fit(ys: List[float]) -> Dict[str, float]:
    """Least-squares fit of y over index 0..n-1. Returns slope and intercept."""
    n = len(ys)
    if n < 2:
        return {"slope": 0.0, "intercept": ys[0] if ys else 0.0}
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom if denom else 0.0
    intercept = mean_y - slope * mean_x
    return {"slope": slope, "intercept": intercept}
