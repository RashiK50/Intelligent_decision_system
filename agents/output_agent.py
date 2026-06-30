import json
import logging
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from state import PlatformState
# Assuming you have your prompt loader utility
from registry.prompt_registry import get_prompt 

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def output_agent(state: PlatformState) -> dict:
    """
    Translates raw database rows and tool outputs into a business-friendly natural language summary.
    """
    print("\n==================================================")
    print(" 🏁 [OUTPUT NODE] Synthesizing Business Insights...")
    print("==================================================")

    user_query = state.get("user_query", "")
    raw_db_result = state.get("raw_db_result")
    tool_results = state.get("tool_results")  # NEW: Retrieve tool results
    execution_status = state.get("execution_status")
    error_message = state.get("error_message")

    # ==========================================
    # 1. Handle Execution Failures Gracefully
    # ==========================================
    if execution_status == "failed" or raw_db_result is None:
        print("❌ [OUTPUT NODE] Database execution failed. Generating fallback message.")
        fallback_msg = (
            f"I encountered an issue retrieving the data for your request. "
            f"Technical details: {error_message or 'Maximum retry limit reached for SQL generation.'}"
        )
        return {"formatted_response": fallback_msg}

    # ==========================================
    # 2. Handle Empty Results
    # ==========================================
    if not raw_db_result and not tool_results:
        print("⚠️ [OUTPUT NODE] No data (DB or Tool) returned.")
        empty_msg = "The analysis completed successfully, but no records or calculated results were found matching your criteria."
        return {"formatted_response": empty_msg}

    # ==========================================
    # 3. Format Prompt & Invoke LLM
    # ==========================================
    prompt_template_str = get_prompt("output")
    prompt = PromptTemplate.from_template(prompt_template_str)

    # Serialize both DB and Tool data
    json_db_results = json.dumps(raw_db_result, default=str)
    # Ensure tool_results are treated as a string for the prompt
    tool_data_str = json.dumps(tool_results, default=str) if tool_results else "No tool data generated."

    formatted_prompt = prompt.format(
        user_query=user_query,
        query_result=json_db_results,
        tool_results=tool_data_str  # NEW: Pass tool results to the prompt
    )

    try:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.3 
        )
        
        print(" 🏁 [OUTPUT NODE] Generating final narrative with tool insights...")
        response = llm.invoke(formatted_prompt)
        
        print("✅ [OUTPUT NODE] Business insight generated successfully.")
        print("--------------------------------------------------")
        
        return {
            "formatted_response": response.content
        }
        
    except Exception as e:
        print("❌ [OUTPUT NODE] CRITICAL ERROR encountered during generation!")
        print(f"❌ Exception Details: {str(e)}")
        print("--------------------------------------------------")
        return {
            "formatted_response": "An error occurred while synthesizing the final business insights."
        }