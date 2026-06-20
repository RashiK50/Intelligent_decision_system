from tools.sales_tools import compare_period_over_period
from tools.inventory_tools import check_current_stock

# This maps the intent strings (from your Intent Agent) to the actual Python functions
TOOL_MAP = {
    "sales_performance_analysis": [
        {
            "name": "compare_period_over_period",
            "description": "Calculates the percentage growth or decline between two numerical values. Use this when the user asks for Month-over-Month or Q3 vs Q4 comparisons.",
            "function": compare_period_over_period
        }
    ],
    "inventory_supply_analysis": [
        {
            "name": "check_current_stock",
            "description": "Pings the live warehouse system to get the exact, real-time stock levels for a specific product ID.",
            "function": check_current_stock
        }
    ]
}

def get_tools_for_intent(intent: str) -> list[dict]:
    """
    Returns the specific tools allowed for a given intent.
    Called by the Orchestrator to limit token usage.
    """
    return TOOL_MAP.get(intent, [])