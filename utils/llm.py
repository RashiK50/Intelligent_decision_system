"""Centralized LLM provider factory.

All LangGraph nodes obtain their chat model through this module so that the
Groq -> Claude migration is a configuration flip, not a code change.

Provider selection (first match wins):
  1. LLM_PROVIDER env var ("groq" or "anthropic")
  2. "anthropic" if ANTHROPIC_API_KEY is set
  3. "groq" (current default, requires GROQ_API_KEY)

Model selection (first match wins):
  1. LLM_MODEL_<NODE> env var (e.g. LLM_MODEL_ORCHESTRATOR)
  2. ANTHROPIC_MODEL / GROQ_MODEL env var
  3. Provider default (claude-sonnet-5 / llama-3.3-70b-versatile)
"""

import logging
import os
from typing import Optional, Type

from dotenv import load_dotenv
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

# Retryable exception types are assembled from whichever SDKs are installed.
# langchain_groq surfaces openai-spec exceptions; langchain_anthropic surfaces
# anthropic SDK exceptions.
_retryable: list = []
try:
    from openai import APIConnectionError as _OpenAIConnErr
    from openai import APIStatusError as _OpenAIStatusErr
    from openai import RateLimitError as _OpenAIRateErr

    _retryable += [_OpenAIRateErr, _OpenAIStatusErr, _OpenAIConnErr]
except ImportError:  # pragma: no cover
    pass
try:
    from anthropic import APIConnectionError as _AnthropicConnErr
    from anthropic import APIStatusError as _AnthropicStatusErr
    from anthropic import RateLimitError as _AnthropicRateErr

    _retryable += [_AnthropicRateErr, _AnthropicStatusErr, _AnthropicConnErr]
except ImportError:  # pragma: no cover
    pass

RETRYABLE_EXCEPTIONS = tuple(_retryable) or (ConnectionError,)


def get_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider in ("groq", "anthropic"):
        return provider
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "groq"


def get_model_name(node: str, provider: Optional[str] = None) -> str:
    provider = provider or get_provider()
    node_override = os.getenv(f"LLM_MODEL_{node.upper()}")
    if node_override:
        return node_override
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    return os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)


def get_chat_model(node: str, temperature: float = 0.0):
    """Return a LangChain chat model for the given node name."""
    provider = get_provider()
    model = get_model_name(node, provider)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        # Claude Sonnet 5 / Opus 4.7+ reject non-default sampling params, so
        # temperature is intentionally not forwarded on the Anthropic path.
        return ChatAnthropic(model=model, max_tokens=8000)

    from langchain_groq import ChatGroq

    return ChatGroq(model=model, temperature=temperature)


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=lambda rs: logger.warning(
        "LLM call failed with retryable error, attempt %s", rs.attempt_number
    ),
)
def invoke_structured(node: str, prompt: str, schema: Type[BaseModel], temperature: float = 0.0):
    """Invoke the node's LLM with structured (Pydantic) output and retries."""
    llm = get_chat_model(node, temperature=temperature).with_structured_output(schema)
    return llm.invoke(prompt)


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=lambda rs: logger.warning(
        "LLM call failed with retryable error, attempt %s", rs.attempt_number
    ),
)
def invoke_text(node: str, prompt: str, temperature: float = 0.0) -> str:
    """Invoke the node's LLM for a plain-text completion with retries."""
    response = get_chat_model(node, temperature=temperature).invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)
