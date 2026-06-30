import os
import sys
from state import PlatformState

# Keep the path hack to prevent ModuleNotFoundError
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the newly created sales tool
from tools.sales_tools import compare_period_over_period

async def tool_executor_agent(state: PlatformState) -> dict:
    """
    Executes Python math/logic functions directly, bypassing SQL generation.
    """
    print("\n==================================================")
    print(" 🛠️ [TOOL EXECUTOR NODE] Executing Python Tool...")
    print("==================================================")
    
    # 1. Grab the extracted parameters from the Intent Agent
    entities = state.get("entities", {})
    intent = state.get("intent")
    
    result_text = "Tool execution failed: Unknown intent or missing parameters."
    
    # 2. Route to the correct Python function based on Intent
    if intent == "sales_performance_analysis":
        
        # Extract the specific parameters your tool requires from the LLM's entity extraction
        metric = entities.get("metric", "Revenue")
        
        try:
            # Safely cast to float in case the LLM passes them as strings
            current_value = float(entities.get("current_value", 0.0))
            previous_value = float(entities.get("previous_value", 0.0))
            
            print(f" 🛠️ [TOOL EXECUTOR NODE] Firing 'compare_period_over_period' for {metric}")
            
            # Because we decorated the function with @tool in sales_tools.py, 
            # we execute it using LangChain's .invoke() method with a dictionary
            tool_response = compare_period_over_period.invoke({
                "metric": metric,
                "current_value": current_value,
                "previous_value": previous_value
            })
            
            result_text = f"Sales Math Tool Calculation: {tool_response}"
            
        except ValueError:
            result_text = "Sales Tool Error: Could not convert extracted values into numbers."
        except Exception as e:
            result_text = f"Sales Tool Error: {str(e)}"
            
    else:
        print(f"❌ [TOOL EXECUTOR NODE] No tool mapped for intent: {intent}")

    print(f"✅ [TOOL EXECUTOR NODE] Result: {result_text}")
    print("--------------------------------------------------")
    
    # 3. Return it mimicking a DB response so the Output Agent works flawlessly
    return {
        "raw_db_result": [{"System_Tool_Output": result_text}], 
        "execution_status": "success",
        "error_message": None
    }