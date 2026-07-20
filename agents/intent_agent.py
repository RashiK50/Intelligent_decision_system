"""Intent Agent — classifies the business intent and extracts entities.

Uses the centralized LLM factory and prompt registry. On total LLM failure it
degrades to a generic intent instead of halting the graph, so the SQL path can
still attempt an answer.
"""

import json
import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from langchain_core.prompts import PromptTemplate

from state import PlatformState
from registry.prompt_registry import get_prompt
from utils.llm import invoke_structured
from utils.logger import log_node

logger = logging.getLogger(__name__)

FALLBACK_PROMPT = """
You are an expert Intent Categorization Agent for an Enterprise Decision Intelligence Platform.
Your job is to categorize the user query and extract matching entities and constraints.

SUPPORTED DOMAINS:
1. sales_performance_analysis (Sub-intents: revenue_growth, seller_metrics, product_velocity, regional_performance)
2. inventory_supply_analysis (Sub-intents: stock_levels, stockout_risk, restock_forecasting, supplier_performance)

USER QUERY: "{user_query}"

Analyze the query, choose the most appropriate intent/sub-intent, and fill the structured schema accurately.
"""


class AnalyticalConstraints(BaseModel):
    limit: Optional[int] = Field(None, description="The maximum number of rows requested by the user, e.g., Top 5 -> 5")
    sort_order: Optional[str] = Field(None, description="Requested sorting preference, e.g., 'highest', 'lowest', 'alphabetical'")
    time_grain: Optional[str] = Field(None, description="The granularity of time requested, e.g., 'monthly', 'daily', 'yearly'")
    aggregation_preference: Optional[str] = Field(None, description="Preferred math calculation, e.g., 'sum', 'average', 'percentage_change'")


class IntentOutput(BaseModel):
    intent: str = Field(
        description="The high-level domain intent. Must be either 'sales_performance_analysis' or 'inventory_supply_analysis'."
    )
    sub_intent: str = Field(
        description="The granular categorization. For Sales: 'revenue_growth', 'seller_metrics', 'product_velocity', 'regional_performance'. For Inventory: 'stock_levels', 'stockout_risk', 'restock_forecasting', 'supplier_performance'."
    )
    entities: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Key-value pairs extracted for the query. Examples: {'product_id': '123'}, {'start_date': '2026-01-01'}. "
            "CRITICAL: If the query asks to calculate growth or compare numbers, you MUST extract the metric name and values like so: "
            "{'metric': 'Revenue', 'current_value': 500, 'previous_value': 400}."
        ),
    )
    analytical_constraints: AnalyticalConstraints = Field(
        default_factory=AnalyticalConstraints,
        description="Structural or sorting limits requested by the user query.",
    )


@log_node("intent")
def intent_agent(state: PlatformState) -> dict:
    print("\n==================================================")
    print(" [INTENT NODE] Starting execution...")
    print(f" [INTENT NODE] Incoming User Query: '{state.get('user_query', '')}'")
    print("==================================================")

    user_query = state.get("user_query", "")

    prompt = PromptTemplate.from_template(get_prompt("intent", fallback=FALLBACK_PROMPT))
    formatted_prompt = prompt.format(user_query=user_query)

    try:
        print(" [INTENT NODE] Invoking LLM for Intent Analysis...")
        result: IntentOutput = invoke_structured("intent", formatted_prompt, IntentOutput)

        extracted_entities = dict(result.entities)
        extracted_entities["constraints"] = result.analytical_constraints.model_dump()

        print("--------------------------------------------------")
        print(" [INTENT NODE] LLM Response Received Successfully:")
        print(f"   - Intent:     {result.intent}")
        print(f"   - Sub-Intent: {result.sub_intent}")
        print(f"   - Entities:   {json.dumps(result.entities, indent=2, default=str)}")
        print("--------------------------------------------------")

        return {
            "intent": result.intent,
            "sub_intent": result.sub_intent,
            "entities": extracted_entities,
        }

    except Exception as e:
        # Graceful degradation: a generic intent still lets the SQL path try.
        logger.error("Intent extraction failed after retries: %s", e)
        print(f"❌ [INTENT NODE] LLM failed ({e}); using generic fallback intent.")
        return {
            "intent": "sales_performance_analysis",
            "sub_intent": "general",
            "entities": {"constraints": AnalyticalConstraints().model_dump()},
        }
