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
    
    query = state.get("sql_query")
    
    if not query:
        print("❌ [DATABASE EXECUTOR NODE] Error: No SQL query found in state.")
        return {
            "execution_status": "failed",
            "error_message": "No SQL query provided to the executor."
        }
    
    try:
        # Await the async database network call
        results = await execute_read_query(query)
        
        print(f"✅ [DATABASE EXECUTOR NODE] Query executed successfully. Retrieved {len(results)} rows.")
        print("--------------------------------------------------")
        
        # Output stored directly in the state variable you requested
        return {
            "raw_db_result": results,
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