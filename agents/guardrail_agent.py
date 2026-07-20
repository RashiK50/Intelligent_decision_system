"""Guardrail Agent — validates the query belongs to the business domain.

Uses the centralized LLM factory (Groq today, Claude via LLM_PROVIDER config)
and the prompt registry. Rejections short-circuit the graph with a polite,
user-facing formatted_response.
"""

import logging
from typing import Literal, Optional

from pydantic import BaseModel, Field

from langchain_core.prompts import PromptTemplate

from state import PlatformState
from registry.prompt_registry import get_prompt
from registry.schema_loader import get_schema_context
from utils.llm import invoke_structured
from utils.logger import log_node

logger = logging.getLogger(__name__)

FALLBACK_PROMPT = """
You are the Guardrail Agent for an Enterprise Decision Intelligence Platform.
PROJECT CONTEXT: Translating natural language to SQL for Sales & Inventory analysis.
SCHEMA CONTEXT: {schema_context}
USER QUERY: "{user_query}"
TASK: Determine if the query is actionable using the provided schema.
"""


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


@log_node("guardrail")
def guardrail_agent(state: PlatformState) -> dict:
    print("\n==================================================")
    print(" [GUARDRAIL NODE] Starting execution...")
    print(f" [GUARDRAIL NODE] Incoming User Query: '{state.get('user_query', '')}'")
    print("==================================================")

    user_query = state.get("user_query", "")
    schema_context = state.get("schema_context", "")
    if not schema_context:
        try:
            schema_context = get_schema_context()
        except Exception as e:
            logger.warning("Could not load schema context for guardrail: %s", e)

    prompt = PromptTemplate.from_template(get_prompt("guardrail", fallback=FALLBACK_PROMPT))
    formatted_prompt = prompt.format(schema_context=schema_context, user_query=user_query)

    try:
        print(" [GUARDRAIL NODE] Invoking LLM...")
        result: GuardrailOutput = invoke_structured("guardrail", formatted_prompt, GuardrailOutput)

        print("--------------------------------------------------")
        print(" [GUARDRAIL NODE] LLM Response Received Successfully:")
        print(f"   - Classification: {result.classification}")
        print(f"   - Is Allowed:     {result.is_allowed}")
        print(f"   - Reason:         {result.guardrail_reason}")
        print("--------------------------------------------------")

        formatted_response = None
        if not result.is_allowed:
            formatted_response = result.guardrail_reason or (
                "I'm sorry, I couldn't map your request to our data domain. "
                "Could you please specify what business metrics you are looking for?"
            )

        return {
            "is_allowed": result.is_allowed,
            "guardrail_reason": result.guardrail_reason,
            "formatted_response": formatted_response,
        }

    except Exception as e:
        logger.error("Guardrail execution failed: %s", e)
        print(f"❌ [GUARDRAIL NODE] CRITICAL ERROR: {e}")
        return {
            "is_allowed": False,
            "guardrail_reason": f"System error: {e}",
            "formatted_response": "The platform is currently experiencing high load. Please try again in a few moments.",
        }
