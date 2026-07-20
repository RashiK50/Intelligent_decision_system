"""State reducers — these make parallel fan-out/fan-in writes safe."""

from state import build_initial_state, merge_dicts, merge_errors, merge_status


class TestMergeDicts:
    def test_merges_parallel_branch_results(self):
        left = {"database_executor": [{"a": 1}]}
        right = {"tools": {"visualization": {"status": "success"}}}
        merged = merge_dicts(left, right)
        assert merged == {
            "database_executor": [{"a": 1}],
            "tools": {"visualization": {"status": "success"}},
        }

    def test_right_wins_on_collision(self):
        assert merge_dicts({"k": 1}, {"k": 2}) == {"k": 2}

    def test_handles_none_sides(self):
        assert merge_dicts(None, {"k": 1}) == {"k": 1}
        assert merge_dicts({"k": 1}, None) == {"k": 1}
        assert merge_dicts(None, None) == {}


class TestMergeStatus:
    def test_failed_is_sticky_either_side(self):
        assert merge_status("failed", "success") == "failed"
        assert merge_status("success", "failed") == "failed"

    def test_success_propagates(self):
        assert merge_status("pending", "success") == "success"

    def test_none_falls_back_to_other_side(self):
        assert merge_status(None, "success") == "success"
        assert merge_status("success", None) == "success"
        assert merge_status(None, None) is None


class TestMergeErrors:
    def test_concatenates_distinct_errors(self):
        assert merge_errors("db timeout", "tool crashed") == "db timeout | tool crashed"

    def test_dedupes_identical_errors(self):
        assert merge_errors("same", "same") == "same"

    def test_none_handling(self):
        assert merge_errors(None, "boom") == "boom"
        assert merge_errors("boom", None) == "boom"
        assert merge_errors(None, None) is None


class TestBuildInitialState:
    def test_contains_every_routing_key(self):
        state = build_initial_state("show me sales")
        assert state["user_query"] == "show me sales"
        for key in (
            "required_tasks", "required_tools", "workflow", "parallel_results",
            "execution_status", "sql_retry_count", "entities", "plan",
        ):
            assert key in state
        assert state["sql_retry_count"] == 0
        assert state["parallel_results"] == {}
