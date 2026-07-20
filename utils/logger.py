"""Structured logging for LangGraph nodes.

Every node gets a named logger plus a `log_node` decorator that records
entry/exit and wall-clock duration, so a full request leaves a readable
trace like:

    2026-07-18 10:00:01 | INFO | node.orchestrator | >> enter
    2026-07-18 10:00:02 | INFO | node.orchestrator | << exit ok (1.04s)
"""

import functools
import inspect
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("platform")


def get_node_logger(node_name: str) -> logging.Logger:
    return logging.getLogger(f"node.{node_name}")


def log_node(node_name: str):
    """Decorator adding entry/exit/timing logs to a sync or async graph node."""

    def decorator(fn):
        node_logger = get_node_logger(node_name)

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                node_logger.info(">> enter")
                try:
                    result = await fn(*args, **kwargs)
                    node_logger.info("<< exit ok (%.2fs)", time.perf_counter() - start)
                    return result
                except Exception:
                    node_logger.exception("<< exit FAILED (%.2fs)", time.perf_counter() - start)
                    raise

            return async_wrapper

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            node_logger.info(">> enter")
            try:
                result = fn(*args, **kwargs)
                node_logger.info("<< exit ok (%.2fs)", time.perf_counter() - start)
                return result
            except Exception:
                node_logger.exception("<< exit FAILED (%.2fs)", time.perf_counter() - start)
                raise

        return wrapper

    return decorator
