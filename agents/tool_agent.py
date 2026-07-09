import os
import sys
from state import PlatformState

# Keep the path hack
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.sales_tools import compare_period_over_period

async def tool_executor_agent(state: PlatformState) -> dict:
    """
    Executes Python math/logic functions directly. 
    Writes results to state['parallel_results'] to support parallel execution.
    """
    print("\n==================================================")
    print(" 🛠️ [TOOL EXECUTOR NODE] Executing Python Tool...")
    print("==================================================")
    
    entities = state.get("entities", {})
    intent = state.get("intent")
    
    parallel_results = state.get("parallel_results", {}).copy()
    
    # 1. Resilience Check: Ensure we have data before we proceed
    # If the Intent Agent failed to extract these, we stop here with a clear message.
    current_val_raw = entities.get("current_value")
    prev_val_raw = entities.get("previous_value")
    
    if current_val_raw is None or prev_val_raw is None:
        result_text = "Sales Tool Error: I could not identify the numerical values needed to perform the comparison. Please check the query formatting."
    
    elif intent == "sales_performance_analysis":
        metric = entities.get("metric", "Revenue")
        try:
            current_value = float(current_val_raw)
            previous_value = float(prev_val_raw)
            
            print(f" 🛠️ [TOOL EXECUTOR NODE] Firing 'compare_period_over_period' for {metric}")
            
            tool_response = compare_period_over_period.invoke({
                "metric": metric,
                "current_value": current_value,
                "previous_value": previous_value
            })
            
            result_text = f"Sales Math Tool Calculation: {tool_response}"
            
        except (ValueError, TypeError) as e:
            result_text = f"Sales Tool Error: Could not convert extracted values into numbers. Details: {str(e)}"
        except Exception as e:
            result_text = f"Sales Tool Error: {str(e)}"
    else:
        print(f"❌ [TOOL EXECUTOR NODE] No tool mapped for intent: {intent}")
        result_text = f"No tool found for intent: {intent}"

    # Write the result (either the success string OR the error message) to the state
    parallel_results["tool_executor"] = [{"System_Tool_Output": result_text}]

    print(f"✅ [TOOL EXECUTOR NODE] Result written to parallel_results")
    print("--------------------------------------------------")
    
    return {
        "parallel_results": parallel_results,
        "execution_status": "success"
    }