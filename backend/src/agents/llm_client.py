"""Lightweight OpenAI-compat chat wrapper for backend agent calls.

Goes straight to Gemini's /v1beta/openai endpoint — gradbot's tool_call
SSE-parsing bug is a streaming issue, and our agent calls are one-shot
JSON completions, so we don't need the local llm-proxy hop here.
"""

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

# Gemini 2.5 Flash silently spends a chunk of the token budget on
# "thinking" before any visible output. With small budgets (~2k) it
# regularly clips JSON mid-string. 4k gives the structured outputs
# breathing room without being wasteful.
DEFAULT_MAX_TOKENS = 4000


def _api_key() -> str:
    key = os.environ.get("LLM_API_KEY")
    if not key:
        raise RuntimeError("LLM_API_KEY is not set")
    return key


def _model() -> str:
    return os.environ.get("LLM_MODEL", "gemini-2.5-flash")


def lite_model() -> str:
    """Lighter model alias for tasks that don't need extended reasoning.

    Reads ``LLM_LITE_MODEL`` from env, falling back to the main model if
    unset. Useful for structured extraction over long inputs where the
    main model's thinking tokens would eat the response budget.
    """
    return os.environ.get("LLM_LITE_MODEL") or _model()


async def chat_json(
    system: str,
    user: str,
    *,
    temperature: float = 0.7,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    model: str | None = None,
) -> dict[str, Any]:
    """Send a one-shot chat completion and parse a JSON object from the reply.

    Robustness layers (in order):
      1. Call the configured model with response_format=json_object.
      2. If finish_reason="length" (truncated) OR the JSON refuses to
         parse, retry once on the lite model — which has thinking
         disabled by default and so spends every token on visible output.
      3. If THAT also fails, raise.
    """
    primary = model or _model()
    fallback = lite_model()

    content, finish_reason = await _chat_raw(
        primary, system, user, temperature, max_tokens
    )

    parsed = _try_parse(content)
    if parsed is not None and finish_reason != "length":
        return parsed

    # Retry on the lite model — same tokens budget, no thinking spend.
    if fallback != primary:
        reason = "truncated" if finish_reason == "length" else "unparseable"
        logger.warning(
            "LLM reply was %s on %s; retrying on %s",
            reason, primary, fallback,
        )
        retry_content, retry_finish = await _chat_raw(
            fallback, system, user, temperature, max_tokens
        )
        retry_parsed = _try_parse(retry_content)
        if retry_parsed is not None and retry_finish != "length":
            return retry_parsed
        # Fall through with whichever attempt actually produced JSON.
        if retry_parsed is not None:
            return retry_parsed

    if parsed is not None:
        # Original parse worked but flagged length — caller chose to
        # accept partial data rather than raise. Better than nothing.
        return parsed
    # Re-raise the original parse error so callers see WHY it failed.
    return _parse_json_lenient(content)


async def _chat_raw(
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
) -> tuple[str, str | None]:
    """Single LLM call. Returns (content, finish_reason)."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    url = f"{GEMINI_BASE_URL}/chat/completions"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        logger.warning(
            "LLM call failed status=%s body=%s", resp.status_code, resp.text[:300],
        )
        raise RuntimeError(f"LLM returned {resp.status_code}")
    data = resp.json()
    choice = data["choices"][0]
    content = choice.get("message", {}).get("content") or ""
    finish_reason = choice.get("finish_reason")
    return content, finish_reason


def _try_parse(text: str) -> dict[str, Any] | None:
    """Best-effort JSON parse — returns None if it can't be made into a dict."""
    try:
        return _parse_json_lenient(text)
    except (ValueError, json.JSONDecodeError):
        return None


def _parse_json_lenient(text: str) -> dict[str, Any]:
    """Try strict JSON first, then look for the first balanced {...} block."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object in LLM reply: {text[:200]}")
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError(f"Unbalanced JSON in LLM reply: {text[:200]}")
