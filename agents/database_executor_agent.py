from database.engine import execute_read_query
from state import PlatformState

async def database_executor_agent(state: PlatformState) -> dict:
    """
    Executes the validated SQL query against the database asynchronously.
    Stores the output in the raw_db_result state variable with a safety valve
    to prevent LLM context window overflow (413 errors).
    """
    print("\n==================================================")
    print(" [DATABASE EXECUTOR NODE] Firing Query...")
    print("==================================================")
    
    sql_query = state.get("sql_query")
    
    if not sql_query:
        print("❌ [DATABASE EXECUTOR NODE] Error: No SQL query found in state.")
        return {
            "execution_status": "failed",
            "error_message": "No SQL query provided to the executor."
        }
    
    try:
        # Await the async database network call
        raw_data = await execute_read_query(sql_query)
        
        print(f"✅ [DATABASE EXECUTOR NODE] Query executed successfully. Retrieved {len(raw_data)} rows.")
        
        # ==========================================
        # SAFETY VALVE: Prevent 413 Payload Errors
        # ==========================================
        MAX_ROWS_FOR_LLM = 50
        
        if len(raw_data) > MAX_ROWS_FOR_LLM:
            print(f"⚠️ [DATABASE EXECUTOR NODE] Truncating data from {len(raw_data)} to {MAX_ROWS_FOR_LLM} rows for LLM synthesis.")
            data_to_pass_to_output = raw_data[:MAX_ROWS_FOR_LLM]
            
            # Inject a warning record so the Output Agent knows it was truncated
            data_to_pass_to_output.append({
                "SYSTEM_WARNING": f"Note for AI: This dataset was too large ({len(raw_data)} rows). You are only seeing a sample of the top {MAX_ROWS_FOR_LLM} rows. Please inform the user that this is a sample."
            })
        else:
            data_to_pass_to_output = raw_data
            
        print("--------------------------------------------------")
        
        # Output stored directly in the state variable you requested
        return {
            "raw_db_result": data_to_pass_to_output,
            "execution_status": "success",
            "error_message": None
        }
        
    except Exception as e:
        print(f"❌ [DATABASE EXECUTOR NODE] Execution Failed: {str(e)}")
        print("--------------------------------------------------")
        
        return {
            "raw_db_result": None,
            "execution_status": "failed",
            "error_message": str(e)
        }