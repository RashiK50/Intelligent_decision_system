import json
import logging
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from openai import RateLimitError, APIStatusError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Centralized State and Registries
from state import PlatformState
from database.schema_registry import schema_registry
from registry.tool_registry import tool_registry

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 1. Pydantic Models for Orchestrator Output
# ==========================================

class OrchestratorOutput(BaseModel):
    workflow_type: Literal["single_planner", "parallel_planners", "sequential_planners"] = Field(
        description="Determine the execution path. Use 'single_planner' for most queries. Use 'parallel_planners' if multiple independent data pulls are needed. Use 'sequential_planners' if step 2 depends on the output of step 1."
    )
    required_tables: List[str] = Field(
        description="The exact database tables required to answer the query."
    )
    required_tools: List[str] = Field(
        description="The specific tools needed to supplement the SQL data, if any."
    )
    execution_plan: str = Field(
        description="A brief 1-2 sentence directive instructing the downstream planner(s) on how to approach the task."
    )

# ==========================================
# 2. Helper: Centralized Prompt Loader
# ==========================================
def get_prompt(prompt_key: str) -> str:
    """Loads prompt from prompts/prompts.json."""
    try:
        with open("prompts/prompts.json", "r") as f:
            prompts = json.load(f)
            active_version = prompts.get(prompt_key, {}).get("active_version", "v1")
            return prompts.get(prompt_key, {}).get("versions", {}).get(active_version, "")
    except FileNotFoundError:
        return """
        You are the Master Orchestrator for an Enterprise Decision Intelligence Platform.
        
        USER QUERY: "{user_query}"
        DETECTED INTENT: "{intent}" (Sub-intent: "{sub_intent}")
        EXTRACTED ENTITIES: {entities}
        
        AVAILABLE DATABASE TABLES:
        {available_tables}
        
        AVAILABLE TOOLS:
        {available_tools}
        
        TASK:
        1. Decide the optimal workflow (single, parallel, or sequential).
        2. Select ONLY the necessary tables and tools required.
        3. Provide a brief execution directive for the Planner Agent.
        """

# ==========================================
# 3. LLM Call with Retry Logic
# ==========================================
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((RateLimitError, APIStatusError)),
    before_sleep=lambda retry_state: logger.warning(f"Groq Rate Limit hit in Orchestrator. Retrying... Attempt {retry_state.attempt_number}")
)
def invoke_orchestrator_llm(formatted_prompt: str) -> OrchestratorOutput:
    # Using Llama 3.3 70B for high-level architectural reasoning
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.0 
    ).with_structured_output(OrchestratorOutput)
    
    return llm.invoke(formatted_prompt)

# ==========================================
# 4. LangGraph Node Implementation
# ==========================================
def orchestrator_agent(state: PlatformState) -> dict:
    # 🛑 POSITION 1: Entry Checkpoint
    print("\n==================================================")
    print(" [ORCHESTRATOR NODE] Starting execution...")
    print(f" [ORCHESTRATOR NODE] Intent: {state.get('intent')} | Sub: {state.get('sub_intent')}")
    print("==================================================")
    
    user_query = state.get("user_query", "")
    intent = state.get("intent", "")
    sub_intent = state.get("sub_intent", "")
    entities = state.get("entities", {})
    
    # Generate high-level summaries of tables to save context window
    # We only show the names and descriptions here, not the full columns
    available_tables = "\n".join([f"- {name}: {info.get('description', '')}" for name, info in schema_registry.tables.items()])
    
    # Get relevant tools based on intent
    available_tools = tool_registry.get_all_tool_schemas_for_llm(intent)
    
    prompt_template_str = get_prompt("orchestrator")
    prompt = PromptTemplate.from_template(prompt_template_str)
    
    formatted_prompt = prompt.format(
        user_query=user_query,
        intent=intent,
        sub_intent=sub_intent,
        entities=json.dumps(entities),
        available_tables=available_tables,
        available_tools=available_tools
    )
    
    try:
        # 🛑 POSITION 2: API Call
        print(" [ORCHESTRATOR NODE] Evaluating resources and constructing execution plan...")
        result: OrchestratorOutput = invoke_orchestrator_llm(formatted_prompt)
        
        # 🛑 POSITION 3: Success Checkpoint
        print("--------------------------------------------------")
        print(" [ORCHESTRATOR NODE] Execution Plan Generated:")
        print(f"   - Workflow Type:   {result.workflow_type}")
        print(f"   - Required Tables: {result.required_tables}")
        print(f"   - Required Tools:  {result.required_tools}")
        print(f"   - Directive:       {result.execution_plan}")
        print("--------------------------------------------------")

        # MAGIC HAPPENS HERE: We fetch the highly detailed, token-optimized menu 
        # ONLY for the tables the orchestrator selected.
        focused_schema_context = schema_registry.get_formatted_menu_for_intent(result.required_tables)

        # Update the state. We inject the focused schema context and the selected workflow.
        return {
            "workflow": result.workflow_type,
            "plan": {
                "directive": result.execution_plan,
                "tools": result.required_tools,
                "tables": result.required_tables
            },
            "schema_context": focused_schema_context # This overwrites the global schema with the focused one!
        }
        
    except Exception as e:
        # 🛑 POSITION 4: Error Block
        print("❌ [ORCHESTRATOR NODE] CRITICAL ERROR encountered!")
        print(f"❌ Exception Details: {str(e)}")
        print("--------------------------------------------------")
        raise e