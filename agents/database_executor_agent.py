"""Database Executor — runs the validated SQL asynchronously.

Writes results into state['parallel_results']['database_executor'] (the state
reducer merges parallel branch writes). Includes:
  - one automatic retry on transient connection errors
  - the truncation safety valve that protects the LLM from oversized payloads
"""

import asyncio

from database.engine import execute_read_query
from state import PlatformState
from utils.logger import get_node_logger, log_node

logger = get_node_logger("database_executor")

MAX_ROWS_FOR_LLM = 50
TRANSIENT_MARKERS = ("connection", "timeout", "temporarily", "reset", "closed")


@log_node("database_executor")
async def database_executor_agent(state: PlatformState) -> dict:
    print("\n==================================================")
    print(" [DATABASE EXECUTOR NODE] Firing Query...")
    print("==================================================")

    sql_query = state.get("sql_query")
    if not sql_query:
        print("❌ [DATABASE EXECUTOR NODE] Error: No SQL query found in state.")
        return {
            "parallel_results": {"database_executor": None},
            "execution_status": "failed",
            "error_message": "No SQL query provided to the executor.",
        }

    raw_data = None
    last_error = None
    for attempt in (1, 2):
        try:
            raw_data = await execute_read_query(sql_query)
            break
        except Exception as e:
            last_error = e
            message = str(e).lower()
            transient = any(marker in message for marker in TRANSIENT_MARKERS)
            if attempt == 1 and transient:
                logger.warning("Transient DB error (%s); retrying once...", e)
                await asyncio.sleep(1.0)
                continue
            print(f"❌ [DATABASE EXECUTOR NODE] Execution Failed: {e}")
            print("--------------------------------------------------")
            return {
                "parallel_results": {"database_executor": None},
                "execution_status": "failed",
                "error_message": str(e),
            }

    print(f"✅ [DATABASE EXECUTOR NODE] Query executed successfully. Retrieved {len(raw_data)} rows.")

    # ==========================================
    # SAFETY VALVE: Prevent 413 Payload Errors
    # ==========================================
    if len(raw_data) > MAX_ROWS_FOR_LLM:
        print(f"⚠️ [DATABASE EXECUTOR NODE] Truncating data from {len(raw_data)} to {MAX_ROWS_FOR_LLM} rows.")
        data_to_pass = raw_data[:MAX_ROWS_FOR_LLM]
        data_to_pass.append({
            "SYSTEM_WARNING": (
                f"Note for AI: This dataset was too large ({len(raw_data)} rows). "
                f"You are only seeing a sample of the top {MAX_ROWS_FOR_LLM} rows."
            )
        })
    else:
        data_to_pass = raw_data

    print("--------------------------------------------------")

    return {
        "parallel_results": {"database_executor": data_to_pass},
        "execution_status": "success",
        "error_message": None,
    }
