import json
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from openai import RateLimitError, APIStatusError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Import your centralized state definition
from state import PlatformState  

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 1. Pydantic Models for Intent Extraction
# ==========================================

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
        description="Key-value pairs extracted for the query. Examples: {'product_id': '123'}, {'start_date': '2026-01-01'}, {'category': 'electronics'}, {'region': 'North'}."
    )
    analytical_constraints: AnalyticalConstraints = Field(
        description="Structural or sorting limits requested by the user query."
    )

# ==========================================
# 2. Helper: Centralized Prompt Loader
# ==========================================
def get_prompt(prompt_key: str) -> str:
    """Loads prompt from prompts/prompts.json with a hardcoded fallback if missing."""
    try:
        with open("prompts/prompts.json", "r") as f:
            prompts = json.load(f)
            active_version = prompts.get(prompt_key, {}).get("active_version", "v1")
            return prompts.get(prompt_key, {}).get("versions", {}).get(active_version, "")
    except FileNotFoundError:
        logger.warning("prompts.json not found. Using fallback Intent prompt.")
        return """
        You are an expert Intent Categorization Agent for an Enterprise Decision Intelligence Platform.
        Your job is to categorize the user query and extract matching entities and constraints.

        SUPPORTED DOMAINS:
        1. sales_performance_analysis (Sub-intents: revenue_growth, seller_metrics, product_velocity, regional_performance)
        2. inventory_supply_analysis (Sub-intents: stock_levels, stockout_risk, restock_forecasting, supplier_performance)

        USER QUERY: "{user_query}"
        
        Analyze the query, choose the most appropriate intent/sub-intent, and fill the structured schema accurately.
        """

# ==========================================
# 3. LLM Call with Retry Logic (Groq API)
# ==========================================
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((RateLimitError, APIStatusError)),
    before_sleep=lambda retry_state: logger.warning(f"Groq Rate Limit hit in Intent Agent. Retrying... Attempt {retry_state.attempt_number}")
)
def invoke_intent_llm(formatted_prompt: str) -> IntentOutput:
    """Invokes Groq API to extract structured intent configurations."""
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.0  # Precise extraction, no variations
    ).with_structured_output(IntentOutput)
    
    return llm.invoke(formatted_prompt)

# ==========================================
# 4. LangGraph Node Implementation
# ==========================================
def intent_agent(state: PlatformState) -> dict:
    """
    LangGraph node that processes the allowed user query to classify intent
    and extract contextual entities.
    """
    # 🛑 POSITION 1: Entry Checkpoint Terminal Log
    print("\n==================================================")
    print(" [INTENT NODE] Starting execution...")
    print(f" [INTENT NODE] Incoming User Query: '{state.get('user_query', '')}'")
    print("==================================================")
    
    user_query = state.get("user_query", "")
    
    prompt_template_str = get_prompt("intent")
    
    # 🛑 POSITION 2: Prompt Loaded Checkpoint
    print(f" [INTENT NODE] Prompt template fetched. Length: {len(prompt_template_str)} chars.")
    
    prompt = PromptTemplate.from_template(prompt_template_str)
    formatted_prompt = prompt.format(user_query=user_query)
    
    try:
        # 🛑 POSITION 3: API Call Checkpoint
        print(" [INTENT NODE] Invoking Groq API for Intent Analysis...")
        
        result: IntentOutput = invoke_intent_llm(formatted_prompt)
        
        # Merge entities and constraints together if desired, or keep track cleanly
        extracted_entities = result.entities
        # Add constraints as an inner element of entities to match your central State schema dictionary
        extracted_entities["constraints"] = result.analytical_constraints.model_dump()

        # 🛑 POSITION 4: LLM Response Received Checkpoint
        print("--------------------------------------------------")
        print(" [INTENT NODE] Groq Response Received Successfully:")
        print(f"   - Intent:     {result.intent}")
        print(f"   - Sub-Intent: {result.sub_intent}")
        print(f"   - Entities:   {json.dumps(result.entities, indent=2)}")
        print("--------------------------------------------------")

        # Update and return values directly to the central state variables
        return {
            "intent": result.intent,
            "sub_intent": result.sub_intent,
            "entities": extracted_entities
        }
        
    except Exception as e:
        # 🛑 POSITION 5: Error Checkpoint
        print("❌ [INTENT NODE] CRITICAL ERROR encountered during execution!")
        print(f"❌ [INTENT NODE] Exception Details: {str(e)}")
        print("--------------------------------------------------")
        raise e