"""Schema-aware SQL validator — deterministic, no LLM.

Uses real Olist tables from the generated schema registry:
orders, order_items, customers, sellers, order_payments, ...
"""

import pytest

from agents.sql_validator_agent import sql_validator_agent


def validate(sql: str) -> dict:
    result = sql_validator_agent({"sql_query": sql})
    return result["sql_validation"]


class TestSecurityRules:
    def test_delete_statement_rejected(self):
        v = validate("DELETE FROM orders")
        assert v["is_valid"] is False
        assert "SELECT" in v["issues"] or "DELETE" in v["issues"].upper()

    def test_insert_statement_rejected(self):
        assert validate("INSERT INTO orders (order_id) VALUES ('x')")["is_valid"] is False

    def test_drop_rejected(self):
        assert validate("DROP TABLE orders")["is_valid"] is False

    def test_empty_query_rejected(self):
        assert validate("")["is_valid"] is False

    def test_syntax_error_rejected(self):
        v = validate("SELEC order_id FRM orders")
        assert v["is_valid"] is False

    def test_forbidden_word_inside_string_literal_is_allowed(self):
        """Regression: substring scanning used to flag literals like 'DROP'."""
        v = validate("SELECT order_id FROM orders WHERE order_status = 'DROP TABLE ha'")
        assert v["is_valid"] is True

    def test_forbidden_word_outside_literal_still_caught(self):
        v = validate("SELECT order_id FROM orders; DROP TABLE orders")
        assert v["is_valid"] is False


class TestSchemaAwareness:
    def test_valid_simple_query_passes(self):
        v = validate(
            "SELECT order_status, COUNT(*) AS total FROM orders GROUP BY order_status"
        )
        assert v["is_valid"] is True
        assert v["issues"] is None

    def test_unknown_table_rejected(self):
        v = validate("SELECT * FROM warehouse_inventory")
        assert v["is_valid"] is False
        assert "warehouse_inventory" in v["issues"]

    def test_unknown_column_rejected(self):
        v = validate("SELECT order_id, profit_margin FROM orders")
        assert v["is_valid"] is False
        assert "profit_margin" in v["issues"]

    def test_ambiguous_unqualified_column_rejected(self):
        # customer_id exists in both orders and customers
        v = validate(
            "SELECT customer_id FROM orders "
            "JOIN customers ON orders.customer_id = customers.customer_id"
        )
        assert v["is_valid"] is False
        assert "Ambiguous" in v["issues"] or "ambiguous" in v["issues"]

    def test_qualified_columns_resolve_ambiguity(self):
        v = validate(
            "SELECT orders.customer_id, customers.customer_city FROM orders "
            "JOIN customers ON orders.customer_id = customers.customer_id"
        )
        assert v["is_valid"] is True

    def test_alias_qualified_columns_pass(self):
        v = validate(
            "SELECT o.order_id, oi.price FROM orders o "
            "JOIN order_items oi ON oi.order_id = o.order_id"
        )
        assert v["is_valid"] is True

    def test_select_output_alias_usable_in_order_by(self):
        v = validate(
            "SELECT order_status, COUNT(*) AS order_count "
            "FROM orders GROUP BY order_status ORDER BY order_count DESC"
        )
        assert v["is_valid"] is True


class TestJoinPathWarnings:
    def test_registered_fk_join_produces_no_warning(self):
        v = validate(
            "SELECT o.order_id, oi.price FROM orders o "
            "JOIN order_items oi ON oi.order_id = o.order_id"
        )
        assert v["is_valid"] is True
        assert v["warnings"] == []

    def test_unregistered_join_path_warns_but_passes(self):
        v = validate(
            "SELECT o.order_id, s.seller_city FROM orders o "
            "JOIN sellers s ON o.customer_id = s.seller_id"
        )
        assert v["is_valid"] is True
        assert any("foreign-key" in w for w in v["warnings"])
