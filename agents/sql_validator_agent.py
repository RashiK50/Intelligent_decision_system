import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from state import PlatformState


def sql_validator_agent(state: PlatformState):
    """
    Deterministic SQL validation using sqlglot.

    Checks:
    - Valid PostgreSQL syntax
    - SELECT-only enforcement
    - Basic query safety
    """

    print("\n==================================================")
    print(" [SQL VALIDATOR NODE] Validating Query...")
    print("==================================================")

    query = state.get("sql_query", "")

    if not query:
        return {
            "sql_validation": {
                "is_valid": False,
                "issues": "No SQL query found."
            }
        }

    try:

        parsed = sqlglot.parse_one(
            query,
            read="postgres"
        )

        # Enforce SELECT-only
        if not isinstance(parsed, exp.Select):

            issue = (
                f"Security Violation: "
                f"Only SELECT queries are allowed. "
                f"Detected: {parsed.key.upper()}"
            )

            print(f"❌ {issue}")

            return {
                "sql_validation": {
                    "is_valid": False,
                    "issues": issue
                }
            }

        # Block dangerous keywords even if parsing succeeds
        forbidden_keywords = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "ALTER",
            "TRUNCATE",
            "CREATE",
            "GRANT",
            "REVOKE"
        ]

        query_upper = query.upper()

        for keyword in forbidden_keywords:

            if keyword in query_upper:

                issue = (
                    f"Security Violation: "
                    f"Forbidden keyword detected: {keyword}"
                )

                print(f"❌ {issue}")

                return {
                    "sql_validation": {
                        "is_valid": False,
                        "issues": issue
                    }
                }

        print("✅ [SQL VALIDATOR NODE] Query Passed Validation")
        print("--------------------------------------------------")

        return {
            "sql_validation": {
                "is_valid": True,
                "issues": None
            }
        }

    except ParseError as e:

        issue = (
            f"Syntax Error in PostgreSQL query. "
            f"Details: {str(e)}"
        )

        print(f"❌ {issue}")

        return {
            "sql_validation": {
                "is_valid": False,
                "issues": issue
            }
        }

    except Exception as e:

        issue = (
            f"Unexpected validation error: {str(e)}"
        )

        print(f"❌ {issue}")

        return {
            "sql_validation": {
                "is_valid": False,
                "issues": issue
            }
        }