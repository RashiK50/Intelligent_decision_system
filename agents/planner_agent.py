import json
import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from openai import RateLimitError, APIStatusError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Centralized State
from state import PlatformState

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 1. Pydantic Models for Query Blueprint
# ==========================================

class FilterCondition(BaseModel):
    column: str = Field(description="The exact database column name (e.g., 'order_date', 'product_category').")
    operator: str = Field(description="The SQL operator (e.g., '=', '>', '<=', 'ILIKE', 'IN').")
    value: str = Field(description="The value to filter by, formatted for SQL (e.g., '100', \"'Electronics'\", \"'2026-01-01'\").")

class PlannerOutput(BaseModel):
    tables: List[str] = Field(description="List of tables that need to be joined or queried.")
    metrics: List[str] = Field(description="The columns or aliases to SELECT.")
    aggregations: List[str] = Field(description="Mathematical operations needed (e.g., 'SUM(total_price)', 'COUNT(DISTINCT user_id)').")
    filters: List[FilterCondition] = Field(description="Precise conditions for the WHERE clause.")
    group_by: List[str] = Field(description="Columns to use in the GROUP BY clause.")
    sort_by: Optional[str] = Field(None, description="ORDER BY logic (e.g., 'total_revenue DESC').")
    limit: Optional[int] = Field(None, description="Number of rows to limit.")
    reasoning: str = Field(description="Step-by-step logic explaining why these tables, joins, and filters were chosen.")

# ==========================================
# 2. Helper: Centralized Prompt Loader
# ==========================================
def get_prompt(prompt_key: str) -> str:
    try:
        with open("prompts/prompts.json", "r") as f:
            prompts = json.load(f)
            active_version = prompts.get(prompt_key, {}).get("active_version", "v1")
            return prompts.get(prompt_key, {}).get("versions", {}).get(active_version, "")
    except FileNotFoundError:
        return """
        You are the Master Query Planner for an Enterprise Decision Intelligence Platform.
        
        USER QUERY: "{user_query}"
        ORCHESTRATOR DIRECTIVE: "{directive}"
        EXTRACTED ENTITIES: {entities}
        
        AVAILABLE SCHEMA CONTEXT:
        {schema_context}
        
        TASK:
        Map the user's intent and entities directly to the provided schema. 
        Determine exactly which tables, aggregations, and WHERE clause filters are required.
        Output a precise, structured blueprint that a downstream SQL Generator can easily convert into Postgres SQL.
        """

# ==========================================
# 3. LLM Call with Retry Logic
# ==========================================
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((RateLimitError, APIStatusError)),
    before_sleep=lambda retry_state: logger.warning(f"Groq Rate Limit hit in Planner. Retrying... Attempt {retry_state.attempt_number}")
)
def invoke_planner_llm(formatted_prompt: str) -> PlannerOutput:
    # Llama 3.3 70B is excellent at strict JSON matching and logical deductions
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.0 
    ).with_structured_output(PlannerOutput)
    
    return llm.invoke(formatted_prompt)

# ==========================================
# 4. LangGraph Node Implementation
# ==========================================
def planner_agent(state: PlatformState) -> dict:
    # 🛑 POSITION 1: Entry Checkpoint
    print("\n==================================================")
    print(" [PLANNER NODE] Starting execution...")
    print("==================================================")
    
    user_query = state.get("user_query", "")
    entities = state.get("entities", {})
    schema_context = state.get("schema_context", "")
    
    # Extract the directive passed down by the Orchestrator
    plan_state = state.get("plan", {})
    directive = plan_state.get("directive", "Generate a plan based on the intent and schema.")
    
    prompt_template_str = get_prompt("planner")
    prompt = PromptTemplate.from_template(prompt_template_str)
    
    formatted_prompt = prompt.format(
        user_query=user_query,
        directive=directive,
        entities=json.dumps(entities),
        schema_context=schema_context
    )
    
    try:
        # 🛑 POSITION 2: API Call
        print(" [PLANNER NODE] Analyzing schema and drafting query blueprint...")
        result: PlannerOutput = invoke_planner_llm(formatted_prompt)
        
        # 🛑 POSITION 3: Success Checkpoint
        print("--------------------------------------------------")
        print(" [PLANNER NODE] Blueprint Generated:")
        print(f"   - Target Tables: {result.tables}")
        print(f"   - Aggregations:  {result.aggregations}")
        print(f"   - Filters:       {[f'{f.column} {f.operator} {f.value}' for f in result.filters]}")
        print(f"   - Sort / Limit:  {result.sort_by} / {result.limit}")
        print("--------------------------------------------------")

        # Update the state with the detailed plan
        # We merge this with the existing plan dictionary so we don't lose the Orchestrator's tool selections
        updated_plan = {
            **plan_state,
            "blueprint": result.model_dump()
        }

        return {
            "plan": updated_plan
        }
        
    except Exception as e:
        # 🛑 POSITION 4: Error Block
        print("❌ [PLANNER NODE] CRITICAL ERROR encountered!")
        print(f"❌ Exception Details: {str(e)}")
        print("--------------------------------------------------")
        raise e