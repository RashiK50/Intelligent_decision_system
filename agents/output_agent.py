"""Output Agent — the ONLY node that produces the final user-facing response.

Synthesizes the fan-in results (SQL rows + tool outputs) into business prose.

Fixes vs. the previous version:
  - The prompt template referenced {query_result}/{tool_results} which were
    never passed, so .format() raised KeyError before the try block -> the
    node crashed on every run. Prompt v2 uses only {user_query} and {context}.
  - Partial results are now synthesized: if one parallel branch failed but
    the other returned data, the user still gets an answer plus a one-line
    caveat, instead of a hard failure message.
"""

import json
import logging

from langchain_core.prompts import PromptTemplate

from state import PlatformState
from registry.prompt_registry import get_prompt
from utils.llm import invoke_text
from utils.logger import log_node

logger = logging.getLogger(__name__)

FALLBACK_PROMPT = (
    "You are an Enterprise Business Analyst. Using the context data below, answer the "
    "user request in plain, professional prose (no markdown, no SQL/table/ID mentions).\n\n"
    "USER REQUEST: {user_query}\n\nCONTEXT DATA:\n{context}"
)


def _has_usable_results(parallel_results: dict) -> bool:
    rows = parallel_results.get("database_executor")
    if rows:
        return True
    tools = parallel_results.get("tools") or {}
    return any(
        isinstance(r, dict) and r.get("status") == "success" for r in tools.values()
    )


@log_node("output")
def output_agent(state: PlatformState) -> dict:
    print("\n==================================================")
    print(" 🏁 [OUTPUT NODE] Synthesizing Business Insights...")
    print("==================================================")

    # Guardrail rejections already carry their own response — pass through.
    if state.get("is_allowed") is False and state.get("formatted_response"):
        return {"formatted_response": state["formatted_response"]}

    user_query = state.get("user_query", "")
    parallel_results = state.get("parallel_results") or {}
    execution_status = state.get("execution_status")
    error_message = state.get("error_message")

    # 1. Total failure: nothing usable came back from any branch.
    if not _has_usable_results(parallel_results):
        if execution_status == "failed" or error_message:
            print("❌ [OUTPUT NODE] No usable results. Generating fallback message.")
            return {
                "formatted_response": (
                    "I encountered an issue retrieving the data for your request. "
                    f"Technical details: {error_message or 'Workflow failed during execution.'}"
                )
            }
        print("⚠️ [OUTPUT NODE] No data returned from any branch.")
        return {
            "formatted_response": (
                "The analysis completed successfully, but no matching records or calculations were found."
            )
        }

    # 2. Partial failure: annotate the context so the LLM can add a caveat.
    context_payload = dict(parallel_results)
    if execution_status == "failed" and error_message:
        context_payload["_partial_failure_note"] = (
            f"One part of the analysis failed ({error_message}). Answer with the data that is present "
            "and mention the limitation in a single short sentence."
        )

    prompt_template_str = get_prompt("output", fallback=FALLBACK_PROMPT)
    prompt = PromptTemplate.from_template(prompt_template_str)
    context_data = json.dumps(context_payload, indent=2, default=str)

    try:
        formatted_prompt = prompt.format(user_query=user_query, context=context_data)
        print(" 🏁 [OUTPUT NODE] Generating final narrative with unified insights...")
        response_text = invoke_text("output", formatted_prompt, temperature=0.3)
        print("✅ [OUTPUT NODE] Business insight generated successfully.")
        print("--------------------------------------------------")
        return {"formatted_response": response_text}
    except Exception as e:
        logger.error("Error in Output Node synthesis: %s", e)
        # Last-resort deterministic fallback so the user still gets the data.
        rows = parallel_results.get("database_executor") or []
        preview = json.dumps(rows[:5], default=str) if rows else "No rows."
        return {
            "formatted_response": (
                "I retrieved the results but could not generate the narrative summary. "
                f"Raw result preview: {preview}"
            )
        }
