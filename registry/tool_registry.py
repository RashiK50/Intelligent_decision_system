from typing import Type
from pydantic import BaseModel, Field

# Assuming these are standard Python functions in your tools directory
from tools.sales_tools import compare_period_over_period
from tools.inventory_tools import check_current_stock

# =====================================================================
# 1. PYDANTIC INPUT SCHEMAS (The Anti-Hallucination Layer)
# =====================================================================

class ComparePeriodInput(BaseModel):
    current_value: float = Field(
        ..., 
        description="The numerical revenue or sales value for the current period."
    )
    previous_value: float = Field(
        ..., 
        description="The numerical revenue or sales value for the previous period."
    )

class CheckStockInput(BaseModel):
    product_identifier: str = Field(
        ..., 
        description="CRITICAL DATASET RULE: The identifier for the product. You MUST use a valid 'product_category_name' or 'product_id' from the schema. NEVER invent or hallucinate a 'product_name'."
    )

# =====================================================================
# 2. TOOL MAPPING REGISTRY
# =====================================================================

# This maps the intent strings (from your Intent Agent) to the actual tools
TOOL_MAP = {
    "sales_performance_analysis": [
        {
            "name": "compare_period_over_period",
            "description": "Calculates the percentage growth or decline between two numerical values. Use this when the user asks for Month-over-Month, Quarter-over-Quarter, or Year-over-Year comparisons.",
            "args_schema": ComparePeriodInput,  # Links the strict Pydantic rules to the tool
            "function": compare_period_over_period
        }
    ],
    "inventory_supply_analysis": [
        {
            "name": "check_current_stock",
            "description": "Pings the live warehouse system to get the exact, real-time stock levels for a product.",
            "args_schema": CheckStockInput,     # Prevents the LLM from passing invalid column data
            "function": check_current_stock
        }
    ]
}

def get_tools_for_intent(intent: str) -> list[dict]:
    """
    Returns the specific tools allowed for a given intent.
    Called by the Orchestrator to limit token usage and isolate domain context.
    """
    return TOOL_MAP.get(intent, [])