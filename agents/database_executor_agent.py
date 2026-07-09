from database.engine import execute_read_query
from state import PlatformState

async def database_executor_agent(state: PlatformState) -> dict:
    """
    Executes the validated SQL query against the database asynchronously.
    Stores the output in state['parallel_results']['database_executor'] 
    to support parallel execution patterns.
    """
    print("\n==================================================")
    print(" [DATABASE EXECUTOR NODE] Firing Query...")
    print("==================================================")
    
    sql_query = state.get("sql_query")
    # Get current parallel_results or init a new dict if this is the first parallel node
    parallel_results = state.get("parallel_results", {}).copy()
    
    if not sql_query:
        print("❌ [DATABASE EXECUTOR NODE] Error: No SQL query found in state.")
        parallel_results["database_executor"] = None
        return {
            "parallel_results": parallel_results,
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
            print(f"⚠️ [DATABASE EXECUTOR NODE] Truncating data from {len(raw_data)} to {MAX_ROWS_FOR_LLM} rows.")
            data_to_pass_to_output = raw_data[:MAX_ROWS_FOR_LLM]
            
            # Inject a warning record
            data_to_pass_to_output.append({
                "SYSTEM_WARNING": f"Note for AI: This dataset was too large ({len(raw_data)} rows). You are only seeing a sample of the top {MAX_ROWS_FOR_LLM} rows."
            })
        else:
            data_to_pass_to_output = raw_data
            
        print("--------------------------------------------------")
        
        # Update the parallel_results dictionary for this specific node
        parallel_results["database_executor"] = data_to_pass_to_output
        
        return {
            "parallel_results": parallel_results,
            "execution_status": "success",
            "error_message": None
        }
        
    except Exception as e:
        print(f"❌ [DATABASE EXECUTOR NODE] Execution Failed: {str(e)}")
        print("--------------------------------------------------")
        
        parallel_results["database_executor"] = None
        return {
            "parallel_results": parallel_results,
            "execution_status": "failed",
            "error_message": str(e)
        }