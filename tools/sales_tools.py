from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 1. Define the input schema for the LLM
class ComparePeriodInput(BaseModel):
    metric: str = Field(
        ...,
        description="The name of the metric being compared (e.g., 'Revenue', 'Orders')."
    )
    current_value: float = Field(
        ...,
        description="The numerical value for the current time period."
    )
    previous_value: float = Field(
        ...,
        description="The numerical value for the previous time period."
    )

# 2. Define the tool
@tool("compare_period_over_period", args_schema=ComparePeriodInput)
def compare_period_over_period(metric: str, current_value: float, previous_value: float) -> str:
    """
    Calculates the percentage growth or decline between two numbers.
    Always use this tool when the user asks to compare two time periods or calculate growth.
    """
    # Edge case: avoid division by zero
    if previous_value == 0:
        if current_value > 0:
            return f"{metric} grew from 0 to {current_value:,.2f} (New growth)."
        return f"{metric} remained flat at 0."
        
    # Math logic
    percentage_change = ((current_value - previous_value) / abs(previous_value)) * 100
    
    # Narrative generation
    direction = "up" if percentage_change > 0 else "down"
    
    if percentage_change == 0:
        return f"{metric} remained perfectly flat at {current_value:,.2f}."
        
    return (
        f"{metric} is {direction} {abs(percentage_change):.2f}%. "
        f"(Current: {current_value:,.2f}, Previous: {previous_value:,.2f})"
    )