"""
Thin wrapper around the Anthropic API, used by the LLM-backed analysis
modules (career_engine, aerospace_engine's bullet-quality pass, jd_matching,
keyword_engine's semantic enrichment).

Uses forced tool-use to get reliable structured JSON back -- the Anthropic
API has no separate "JSON mode," so defining a single tool and forcing
tool_choice to it is the standard reliable pattern for structured output.

Every caller MUST catch LLMNotConfiguredError and LLMCallError and degrade
just that score/section -- never let an LLM failure take down the whole
/api/analyze request (see app/main.py).
"""
from __future__ import annotations

from typing import Any

from app.config import ANTHROPIC_API_KEY, LLM_ENABLED, LLM_MODEL

_client = None  # lazily constructed so importing this module never requires a key


class LLMNotConfiguredError(Exception):
    """Raised when a caller invokes call_tool() but no ANTHROPIC_API_KEY is set."""


class LLMCallError(Exception):
    """Wraps any Anthropic API/network failure so callers can catch one type."""


def _get_client():
    global _client
    if _client is None:
        import anthropic  # imported lazily so the package is optional until used

        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def call_tool(
    system: str,
    user_content: str,
    tool_name: str,
    tool_description: str,
    input_schema: dict,
    max_tokens: int = 2000,
) -> dict[str, Any]:
    """Calls the configured model with a single forced tool, returns the
    tool call's parsed input dict.

    Raises LLMNotConfiguredError if no API key is set, LLMCallError on any
    API/network failure or if the model didn't return the expected tool
    call (should be rare with tool_choice forced, but never assume).
    """
    if not LLM_ENABLED:
        raise LLMNotConfiguredError("ANTHROPIC_API_KEY is not set -- see .env.example.")

    tool_def = {
        "name": tool_name,
        "description": tool_description,
        "input_schema": input_schema,
    }

    try:
        client = _get_client()
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_content}],
            tools=[tool_def],
            tool_choice={"type": "tool", "name": tool_name},
        )
    except Exception as exc:  # network errors, auth errors, rate limits, etc.
        raise LLMCallError(f"Anthropic API call failed: {exc}") from exc

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
            return block.input

    raise LLMCallError(f"Model did not return the expected '{tool_name}' tool call.")
