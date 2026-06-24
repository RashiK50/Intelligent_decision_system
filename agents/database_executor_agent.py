from database.engine import execute_read_query
from state import PlatformState

async def database_executor_agent(state: PlatformState) -> dict:
    """
    Executes the validated SQL query against the database asynchronously.
    Stores the output in the raw_db_result state variable.
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
        print("--------------------------------------------------")
        
        # Output stored directly in the state variable you requested
        return {
            "raw_db_result": raw_data,
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