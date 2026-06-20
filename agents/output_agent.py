import json
import logging
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from state import PlatformState
# Assuming you have your prompt loader utility
from utils.prompt_manager import get_prompt 

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def output_agent(state: PlatformState) -> dict:
    """
    Translates raw database rows into a business-friendly natural language summary.
    Handles empty sets and database execution errors gracefully.
    """
    print("\n==================================================")
    print(" [OUTPUT NODE] Synthesizing Business Insights...")
    print("==================================================")

    user_query = state.get("user_query", "")
    raw_db_result = state.get("raw_db_result")
    execution_status = state.get("execution_status")
    error_message = state.get("error_message")

    # ==========================================
    # 1. Handle Execution Failures Gracefully
    # ==========================================
    # If the SQL executor failed or the self-healing loop maxed out
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
    # The query succeeded, but returned 0 rows
    if not raw_db_result:
        print("⚠️ [OUTPUT NODE] Query succeeded but returned 0 rows.")
        empty_msg = "The analysis completed successfully, but no records were found matching your exact criteria."
        return {"formatted_response": empty_msg}

    # ==========================================
    # 3. Format Prompt & Invoke LLM
    # ==========================================
    prompt_template_str = get_prompt("output")
    prompt = PromptTemplate.from_template(prompt_template_str)

    # Convert the raw database rows into a stringified JSON payload for the LLM
    # Using default=str to safely serialize dates/decimals from PostgreSQL
    json_results = json.dumps(raw_db_result, default=str)

    formatted_prompt = prompt.format(
        user_query=user_query,
        query_result=json_results
    )

    try:
        # We use a slight bump in temperature (0.3) to allow for natural language fluidity
        # No structured Pydantic output here - we want plain text per your rules
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.3 
        )
        
        print(" [OUTPUT NODE] Generating final narrative...")
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