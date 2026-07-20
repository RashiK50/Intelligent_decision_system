"""Deterministic, schema-aware SQL validation (no LLM).

Checks, in order:
  1. Valid PostgreSQL syntax (sqlglot parse)
  2. SELECT-only enforcement — via the AST, not substring matching
  3. Forbidden statement types anywhere in the tree (INSERT/UPDATE/DDL/...)
  4. Every referenced table exists in the Schema Registry
  5. Every referenced column exists on its table; unqualified columns must be
     unambiguous across the query's tables (SELECT aliases are honored)
  6. Join conditions are checked against registered foreign-key paths;
     unregistered join paths produce warnings (not failures)

Failures route the graph back to the Planner for self-correction with a
precise, actionable issue message.
"""

import re
from typing import Dict, List, Optional, Set

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from database.schema_registry import schema_registry
from state import PlatformState
from utils.logger import log_node

FORBIDDEN_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
    exp.TruncateTable, exp.Grant,
)
FORBIDDEN_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "TRUNCATE", "CREATE", "GRANT", "REVOKE",
)


def _fail(issue: str, warnings: Optional[List[str]] = None) -> dict:
    print(f"❌ [SQL VALIDATOR NODE] {issue}")
    return {"sql_validation": {"is_valid": False, "issues": issue, "warnings": warnings or []}}


def _strip_string_literals(query: str) -> str:
    """Remove '...' literals so keyword scanning can't false-positive on data values."""
    return re.sub(r"'(?:[^']|'')*'", "''", query)


def _schema_columns(table: str) -> Set[str]:
    return set(schema_registry.tables.get(table, {}).get("columns", []))


def _fk_pairs() -> Set[frozenset]:
    """All registered FK relationships as {(table.col), (table.col)} pairs."""
    pairs = set()
    for table_name, meta in schema_registry.tables.items():
        for local_col, target in (meta.get("foreign_keys") or {}).items():
            if isinstance(target, str) and "." in target:
                pairs.add(frozenset({f"{table_name}.{local_col}", target}))
    return pairs


@log_node("sql_validator")
def sql_validator_agent(state: PlatformState) -> dict:
    print("\n==================================================")
    print(" [SQL VALIDATOR NODE] Validating Query...")
    print("==================================================")

    query = state.get("sql_query", "")
    if not query:
        return _fail("No SQL query found.")

    # 1. Syntax
    try:
        parsed = sqlglot.parse_one(query, read="postgres")
    except ParseError as e:
        return _fail(f"Syntax Error in PostgreSQL query. Details: {e}")
    except Exception as e:
        return _fail(f"Unexpected validation error: {e}")

    # 2. SELECT-only
    if not isinstance(parsed, exp.Select):
        return _fail(
            f"Security Violation: Only SELECT queries are allowed. Detected: {parsed.key.upper()}"
        )

    # 3. Forbidden statements — AST first, then a word-boundary sweep with
    #    string literals stripped (fixes the old substring false positives on
    #    columns like 'order_delivered_customer_date' vs DELETE etc.)
    for node_type in FORBIDDEN_NODES:
        if list(parsed.find_all(node_type)):
            return _fail(f"Security Violation: Forbidden statement detected: {node_type.__name__.upper()}")

    scannable = _strip_string_literals(query).upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", scannable):
            return _fail(f"Security Violation: Forbidden keyword detected: {keyword}")

    warnings: List[str] = []

    # Schema-aware checks only run when the registry loaded successfully.
    if schema_registry.tables:
        known_tables = set(schema_registry.tables.keys())

        # 4. Tables exist; build alias -> real table mapping
        alias_map: Dict[str, str] = {}
        query_tables: Set[str] = set()
        for t in parsed.find_all(exp.Table):
            query_tables.add(t.name)
            alias_map[t.alias_or_name] = t.name

        unknown_tables = query_tables - known_tables
        if unknown_tables:
            return _fail(
                f"Unknown table(s): {sorted(unknown_tables)}. Valid tables: {sorted(known_tables)}."
            )

        # SELECT output aliases are legal in ORDER BY / GROUP BY
        select_aliases = {a.alias for a in parsed.find_all(exp.Alias) if a.alias}

        # 5. Columns exist and are unambiguous
        for col in parsed.find_all(exp.Column):
            col_name = col.name
            if not col_name or col_name == "*":
                continue
            table_ref = col.table
            if table_ref:
                actual_table = alias_map.get(table_ref, table_ref)
                if actual_table not in known_tables:
                    return _fail(f"Column '{table_ref}.{col_name}' references unknown table '{table_ref}'.")
                if col_name not in _schema_columns(actual_table):
                    return _fail(
                        f"Column '{col_name}' does not exist in table '{actual_table}'. "
                        f"Available columns: {sorted(_schema_columns(actual_table))}."
                    )
            else:
                if col_name in select_aliases:
                    continue
                owners = [t for t in query_tables if col_name in _schema_columns(t)]
                if not owners:
                    return _fail(
                        f"Column '{col_name}' does not exist in any queried table {sorted(query_tables)}."
                    )
                if len(owners) > 1:
                    return _fail(
                        f"Ambiguous column '{col_name}': present in tables {sorted(owners)}. "
                        f"Qualify it with a table name."
                    )

        # 6. Join-path sanity against registered foreign keys (warning only)
        fk_pairs = _fk_pairs()
        if fk_pairs:
            for join in parsed.find_all(exp.Join):
                on_clause = join.args.get("on")
                if on_clause is None:
                    warnings.append("Join without an ON condition detected (possible cartesian product).")
                    continue
                for eq in on_clause.find_all(exp.EQ):
                    left, right = eq.left, eq.right
                    if isinstance(left, exp.Column) and isinstance(right, exp.Column):
                        left_full = f"{alias_map.get(left.table, left.table)}.{left.name}"
                        right_full = f"{alias_map.get(right.table, right.table)}.{right.name}"
                        if frozenset({left_full, right_full}) not in fk_pairs:
                            warnings.append(
                                f"Join {left_full} = {right_full} does not match a registered foreign-key path."
                            )

    for w in warnings:
        print(f"⚠️ [SQL VALIDATOR NODE] {w}")
    print("✅ [SQL VALIDATOR NODE] Query Passed Validation")
    print("--------------------------------------------------")

    return {"sql_validation": {"is_valid": True, "issues": None, "warnings": warnings}}
