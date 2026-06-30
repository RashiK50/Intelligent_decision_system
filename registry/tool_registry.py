# registry/tool_registry.py

# Import the actual LangChain tool objects from your tools directory
from tools.sales_tools import compare_period_over_period
# from tools.inventory_tools import check_current_stock  # Commented out since we are dropping WMS for now

class ToolRegistry:
    def __init__(self):
        # Map intents directly to the actual LangChain tool objects
        self.registry = {
            "sales_performance_analysis": [
                compare_period_over_period
            ],
            "inventory_supply_analysis": [
                # check_current_stock
            ]
        }
        
    def get_tools_for_intent(self, intent: str) -> list:
        """
        Returns the list of usable tool objects based on the business intent.
        Called by the Orchestrator to limit token usage and isolate domain context.
        """
        return self.registry.get(intent, [])
        
    def get_tool_descriptions_for_llm(self, intent: str) -> str:
        """
        Returns a clean string of tool names and descriptions for the Orchestrator/Planner prompt.
        Because we used the @tool decorator, the tool natively knows its own name and description!
        """
        tools = self.get_tools_for_intent(intent)
        if not tools:
            return "No external tools required."
            
        descriptions = []
        for t in tools:
            # LangChain tools automatically have .name and .description properties
            descriptions.append(f"- {t.name}: {t.description}")
            
        return "\n".join(descriptions)

# Instantiate a global registry object to be imported by your agents
registry = ToolRegistry()