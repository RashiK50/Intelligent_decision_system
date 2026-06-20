def compare_period_over_period(metric_name: str, current_value: float, previous_value: float) -> dict:
    """
    Calculates the percentage growth or decline between two periods.
    Offloads deterministic math from the LLM to ensure absolute accuracy.
    """
    print(f"🔧 [TOOL EXECUTED] Comparing {metric_name} period-over-period...")
    
    if previous_value == 0:
        return {
            "metric": metric_name,
            "status": "error",
            "message": "Cannot calculate percentage change when the previous period value is 0."
        }
        
    difference = current_value - previous_value
    percentage_change = (difference / previous_value) * 100
    
    trend = "increase" if percentage_change > 0 else "decrease" if percentage_change < 0 else "flat"
    
    return {
        "metric": metric_name,
        "current_value": current_value,
        "previous_value": previous_value,
        "absolute_change": round(difference, 2),
        "percentage_change": round(percentage_change, 2),
        "trend": trend
    }