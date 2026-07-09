import json
import logging
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from state import PlatformState
from registry.prompt_registry import get_prompt 

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def output_agent(state: PlatformState) -> dict:
    """
    Synthesizes results from parallel nodes into a business-friendly summary.
    """
    print("\n==================================================")
    print(" 🏁 [OUTPUT NODE] Synthesizing Business Insights...")
    print("==================================================")

    user_query = state.get("user_query", "")
    # Retrieve the unified dictionary
    parallel_results = state.get("parallel_results", {}) 
    execution_status = state.get("execution_status")
    error_message = state.get("error_message")

    # 1. Handle Execution Failures Gracefully
    if execution_status == "failed":
        print("❌ [OUTPUT NODE] Execution failed. Generating fallback message.")
        fallback_msg = (
            f"I encountered an issue retrieving the data for your request. "
            f"Technical details: {error_message or 'Workflow failed during execution.'}"
        )
        return {"formatted_response": fallback_msg}

    # 2. Handle Empty Results
    if not parallel_results:
        print("⚠️ [OUTPUT NODE] No data returned from parallel branches.")
        empty_msg = "The analysis completed successfully, but no matching records or calculations were found."
        return {"formatted_response": empty_msg}

    # 3. Format Prompt & Invoke LLM
    prompt_template_str = get_prompt("output")
    prompt = PromptTemplate.from_template(prompt_template_str)

    # Convert the parallel_results dict into a clean JSON string for the LLM
    # We use default=str to handle any non-serializable objects (like Decimal)
    context_data = json.dumps(parallel_results, indent=2, default=str)

    formatted_prompt = prompt.format(
        user_query=user_query,
        context=context_data 
    )

    try:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.3 
        )
        
        print(" 🏁 [OUTPUT NODE] Generating final narrative with unified insights...")
        response = llm.invoke(formatted_prompt)
        
        print("✅ [OUTPUT NODE] Business insight generated successfully.")
        print("--------------------------------------------------")
        
        return {
            "formatted_response": response.content
        }
        
    except Exception as e:
        logger.error(f"Error in Output Node synthesis: {str(e)}")
        return {
            "formatted_response": "An error occurred while synthesizing the final business insights."
        }