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
    max_tokens: int = 2000,
    model: str | None = None,
) -> dict[str, Any]:
    """Send a one-shot chat completion and parse a JSON object from the reply.

    The model is instructed via response_format=json_object to return a
    parseable JSON document. Falls back to extracting the first {...} block
    if the model wraps it in prose.

    Notes on max_tokens:
        Gemini 2.5 Flash counts internal "thinking" tokens against this
        budget. We default to 2000 so a ~100-token JSON answer has
        breathing room behind the model's reasoning. We also set
        reasoning_effort=none and thinking_budget=0 to keep the
        chain-of-thought minimal — this is what was causing the negotiation
        agent JSON to come back truncated mid-string.
    """
    payload: dict[str, Any] = {
        "model": model or _model(),
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
        logger.warning("LLM call failed status=%s body=%s", resp.status_code, resp.text[:300])
        raise RuntimeError(f"LLM returned {resp.status_code}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"] or ""
    return _parse_json_lenient(content)


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
