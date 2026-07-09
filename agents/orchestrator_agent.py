import json
import logging
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from openai import RateLimitError, APIStatusError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from state import PlatformState
from database.schema_registry import schema_registry
from registry.tool_registry import registry as tool_registry

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 1. Pydantic Models for Orchestrator Output
# ==========================================

class OrchestratorOutput(BaseModel):
    # Added 'parallel_planner' as a literal option
    workflow_type: Literal["single_planner", "parallel_planner", "sequential_planners"] = Field(
        description="Determine the execution path. Use 'parallel_planner' if you need to fetch DB data AND run a tool."
    )
    required_tables: List[str] = Field(default_factory=list, description="The exact database tables required.")    # Renamed to required_tasks to match the router logic
    required_tasks: List[str] = Field(description="List of nodes to run: ['database_executor', 'tool_executor']")
    execution_plan: str = Field(description="A brief directive for downstream nodes.")

# ==========================================
# 2. Helper & Invoke Logic (Kept as is)
# ==========================================
def get_prompt(prompt_key: str) -> str:
    try:
        with open("prompts/prompts.json", "r") as f:
            prompts = json.load(f)
            active_version = prompts.get(prompt_key, {}).get("active_version", "v1")
            return prompts.get(prompt_key, {}).get("versions", {}).get(active_version, "")
    except FileNotFoundError:
        return ""

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((RateLimitError, APIStatusError))
)
def invoke_orchestrator_llm(formatted_prompt: str) -> OrchestratorOutput:
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0).with_structured_output(OrchestratorOutput)
    return llm.invoke(formatted_prompt)

# ==========================================
# 4. LangGraph Node Implementation
# ==========================================
def orchestrator_agent(state: PlatformState) -> dict:
    print("\n🚦 [ORCHESTRATOR NODE] Planning Execution...")
    
    user_query = state.get("user_query", "")
    intent = state.get("intent", "unknown")
    
    available_tables = "\n".join([f"- {name}" for name in schema_registry.tables.keys()])
    available_tools_str = tool_registry.get_tool_descriptions_for_llm(intent)
    
    prompt_template_str = get_prompt("orchestrator")
    prompt = PromptTemplate.from_template(prompt_template_str)
    formatted_prompt = prompt.format(
        user_query=user_query,
        intent=intent,
        available_tables=available_tables,
        available_tools=available_tools_str
    )
    
    try:
        result: OrchestratorOutput = invoke_orchestrator_llm(formatted_prompt)
        
        print(f"✅ [ORCHESTRATOR NODE] Plan: {result.workflow_type} | Tasks: {result.required_tasks}")

        focused_schema_context = schema_registry.get_formatted_menu_for_intent(result.required_tables)

        # RETURN VALUES MAPPED TO STATE
        return {
            "workflow": result.workflow_type,
            "required_tasks": result.required_tasks, # This is the list your router will use
            "plan": {
                "directive": result.execution_plan,
                "tables": result.required_tables
            },
            "schema_context": focused_schema_context,
            "available_tools": available_tools_str
        }
        
    except Exception as e:
        logger.error(f"❌ [ORCHESTRATOR NODE] Error: {str(e)}")
        raise e