import json
import logging
from typing import Literal, Optional, TypedDict
from pydantic import BaseModel, Field
from state import PlatformState

from langchain_core.prompts import PromptTemplate
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from langchain_groq import ChatGroq
from openai import RateLimitError, APIStatusError # Groq uses the openai library spec under the hood for core exceptions

# Optional: Setup basic logging (aligns with your 'Next Planned Features')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==========================================
# 2. Pydantic Output Schema
# ==========================================
class GuardrailOutput(BaseModel):
    classification: Literal["domain_specific", "vague_or_out_of_scope"] = Field(
        description="Classify as 'domain_specific' if the query relates to sales, inventory, or business analytics supported by the schema. Otherwise, classify as 'vague_or_out_of_scope'."
    )
    is_allowed: bool = Field(
        description="True if the query is domain_specific and can be answered using the data. False if it is vague, casual greetings, or completely out of scope."
    )
    guardrail_reason: Optional[str] = Field(
        None, 
        description="Provide a polite explanation to the user if the query is rejected, or a brief internal reason if allowed."
    )

# ==========================================
# 3. Helper: Centralized Prompt Loader
# ==========================================
def get_prompt(prompt_key: str) -> str:
    """
    Simulates loading the prompt from prompts/prompts.json
    """
    try:
        with open("prompts/prompts.json", "r") as f:
            prompts = json.load(f)
            active_version = prompts.get(prompt_key, {}).get("active_version", "v1")
            return prompts.get(prompt_key, {}).get("versions", {}).get(active_version, "")
    except FileNotFoundError:
        logger.warning("prompts.json not found. Using fallback Guardrail prompt.")
        return """
        You are the Guardrail Agent for an Enterprise Decision Intelligence Platform.
        PROJECT CONTEXT: Translating natural language to SQL for Sales & Inventory analysis.
        SCHEMA CONTEXT: {schema_context}
        USER QUERY: "{user_query}"
        TASK: Determine if the query is actionable using the provided schema.
        """

# ==========================================
# 4. LLM Call with Retry Logic (Handles 429/503)
# ==========================================
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    stop=stop_after_attempt(3),
    # Catch Groq RateLimit (429) or Server Errors (500/503)
    retry=retry_if_exception_type((RateLimitError, APIStatusError)),
    before_sleep=lambda retry_state: logger.warning(f"Groq Rate Limit or Server Error hit. Retrying... Attempt {retry_state.attempt_number}")
)
def invoke_guardrail_llm(formatted_prompt: str) -> GuardrailOutput:
    """
    Wraps the Groq API call in Tenacity retry logic to handle rate-limits smoothly.
    """
    # Initialize Groq client
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",  # High quality, fast model optimal for guardrail decisions
        temperature=0.0
    ).with_structured_output(GuardrailOutput)
    
    return llm.invoke(formatted_prompt)

# ==========================================
# 5. LangGraph Node implementation
# ==========================================
def guardrail_agent(state: PlatformState) -> dict:

    print("\n==================================================")
    print(" [GUARDRAIL NODE] Starting execution...")
    print(f" [GUARDRAIL NODE] Incoming User Query: '{state.get('user_query', '')}'")
    print("==================================================")

    """
    Evaluates the user query against the schema to determine if it should proceed.
    """
    logger.info("--- ENTERING GUARDRAIL NODE ---")
    
    user_query = state.get("user_query", "")
    schema_context = state.get("schema_context", "")
    
    prompt_template_str = get_prompt("guardrail")

    print(f" [GUARDRAIL NODE] Prompt template successfully fetched. Length: {len(prompt_template_str)} chars.")
    prompt = PromptTemplate.from_template(prompt_template_str)
    
    formatted_prompt = prompt.format(
        schema_context=schema_context,
        user_query=user_query
    )
    
    try:
        # Call LLM with resilient retry logic

        print(" [GUARDRAIL NODE] Invoking Groq API (model: llama-3.3-70b-versatile)...")

        result: GuardrailOutput = invoke_guardrail_llm(formatted_prompt)

        print("--------------------------------------------------")
        print(" [GUARDRAIL NODE] Groq Response Received Successfully:")
        print(f"   - Classification: {result.classification}")
        print(f"   - Is Allowed:      {result.is_allowed}")
        print(f"   - Reason:   {result.guardrail_reason}")
        print("--------------------------------------------------")

        logger.info(f"Guardrail decision: {result.classification} | Allowed: {result.is_allowed}")
        
        # Prepare direct response if rejected
        formatted_response = None
        if not result.is_allowed:
            formatted_response = result.guardrail_reason or "I'm sorry, I couldn't map your request to our data domain. Could you please specify what business metrics you are looking for?"

        return {
            "is_allowed": result.is_allowed,
            "guardrail_reason": result.guardrail_reason,
            "formatted_response": formatted_response
        }
        
    except Exception as e:
        # Hard fail fallback (e.g., if quota is completely exhausted after retries)
        logger.error(f"Guardrail execution failed: {str(e)}")
        print("❌ [GUARDRAIL NODE] CRITICAL ERROR encountered during execution!")
        print(f"❌ [GUARDRAIL NODE] Exception Details: {str(e)}")
        print("--------------------------------------------------")
        return {
            "is_allowed": False,
            "guardrail_reason": f"System error: {str(e)}",
            "formatted_response": "The platform is currently experiencing high load. Please try again in a few moments."
        }

