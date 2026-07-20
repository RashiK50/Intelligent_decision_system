"""Central prompt registry.

Prompts live in prompts/prompts.json, versioned per agent:

    {"<name>": {"active_version": "v2", "versions": {"v1": "...", "v2": "..."}}}

Every agent loads its prompt through `get_prompt(name)`. A missing file or
missing key never crashes a node: callers may pass a `fallback` template.
"""

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

_PROMPTS_PATH = os.path.join("prompts", "prompts.json")
_lock = threading.Lock()
_cache: dict = {}
_cache_mtime: float = -1.0


def _load() -> dict:
    global _cache, _cache_mtime
    with _lock:
        try:
            mtime = os.path.getmtime(_PROMPTS_PATH)
            if mtime != _cache_mtime:
                with open(_PROMPTS_PATH, "r", encoding="utf-8") as f:
                    _cache = json.load(f)
                _cache_mtime = mtime
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to load prompt registry: %s", e)
        return _cache


def get_prompt(prompt_name: str, version: str = None, fallback: str = "") -> str:
    """Return the active (or requested) version of a named prompt."""
    prompts = _load()
    entry = prompts.get(prompt_name)
    if not entry:
        if fallback:
            logger.warning("Prompt '%s' not found; using fallback.", prompt_name)
            return fallback
        raise KeyError(f"Prompt '{prompt_name}' not found in {_PROMPTS_PATH}")

    active = version or entry.get("active_version", "v1")
    template = entry.get("versions", {}).get(active)
    if not template:
        if fallback:
            logger.warning("Prompt '%s' version '%s' missing; using fallback.", prompt_name, active)
            return fallback
        raise KeyError(f"Prompt '{prompt_name}' has no version '{active}'")
    return template
