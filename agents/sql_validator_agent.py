import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from state import PlatformState 

def sql_validator_agent(state: PlatformState):
    """
    Deterministic SQL validation using sqlglot.
    No LLM used. Checks for syntax and enforces SELECT-only restrictions.
    """
    query = state.get("sql_query", "")
    
    try:
        # Parse the query using the PostgreSQL dialect
        parsed = sqlglot.parse_one(query, read="postgres")
        
        # Check for destructive queries - the root AST node MUST be a Select
        if not isinstance(parsed, exp.Select):
            return {
                "sql_validation": {
                    "is_valid": False,
                    "issues": f"Security Violation: Only SELECT queries are allowed. Detected: {parsed.key.upper()}"
                }
            }
            
        # If execution reaches here, it is a valid, safe PostgreSQL SELECT query
        return {
            "sql_validation": {
                "is_valid": True,
                "issues": None
            }
        }
        
    except ParseError as e:
        # sqlglot instantly catches missing commas, bad keywords, etc.
        error_message = f"Syntax Error in PostgreSQL query. Details: {str(e)}"
        return {
            "sql_validation": {
                "is_valid": False,
                "issues": error_message
            }
        }
    except Exception as e:
        # Catch-all for unexpected parsing failures
        return {
            "sql_validation": {
                "is_valid": False,
                "issues": f"Unexpected validation error: {str(e)}"
            }
        }