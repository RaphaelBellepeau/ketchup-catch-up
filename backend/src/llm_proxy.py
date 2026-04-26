"""LLM proxy — patches Gemini's OpenAI-compat SSE so gradbot can read it.

Gradbot's Rust SSE parser strictly requires every streaming `tool_call`
delta to carry an `index: usize` field (per the OpenAI streaming spec).
Gemini's `/v1beta/openai/chat/completions` endpoint omits that field,
causing gradbot to silently drop the tool_call and the agent to look
mute right after the user's last answer.

This proxy:
  1. Forwards POST /chat/completions to the upstream Gemini endpoint.
  2. Streams the SSE response back chunk-by-chunk.
  3. For each `data:` line that contains `tool_calls`, parses the JSON,
     injects `index: 0, 1, 2…` on each tool_call that's missing one,
     and re-serializes.

Configure gradbot to use this proxy by setting in backend/.env:

    LLM_BASE_URL=http://localhost:8000/llm-proxy

Everything else (LLM_API_KEY, LLM_MODEL) stays the same.
"""

import json
import logging
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)

UPSTREAM_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"

router = APIRouter(prefix="/llm-proxy", tags=["llm-proxy"])


def _patch_sse_line(line: str) -> str:
    """Return the SSE line with tool_call indexes injected when missing."""
    if not line.startswith("data: "):
        return line
    payload = line[6:].strip()
    if not payload or payload == "[DONE]":
        return line
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return line
    patched = False
    for choice in data.get("choices") or []:
        delta = choice.get("delta") or {}
        tool_calls = delta.get("tool_calls") or []
        for i, tc in enumerate(tool_calls):
            if tc.get("index") is None:
                tc["index"] = i
                patched = True
    if not patched:
        return line
    return "data: " + json.dumps(data, separators=(",", ":"))


async def _proxy_stream(
    upstream_url: str,
    headers: dict[str, str],
    body: bytes,
) -> AsyncIterator[bytes]:
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST", upstream_url, content=body, headers=headers
        ) as resp:
            resp.raise_for_status()
            buffer = ""
            async for chunk in resp.aiter_bytes():
                if not chunk:
                    continue
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    yield (_patch_sse_line(line) + "\n").encode("utf-8")
            if buffer:
                yield (_patch_sse_line(buffer)).encode("utf-8")


def _forward_headers(request: Request) -> dict[str, str]:
    """Pass through Authorization + content-type, drop hop-by-hop headers."""
    out: dict[str, str] = {}
    for k, v in request.headers.items():
        kl = k.lower()
        if kl in (
            "host",
            "content-length",
            "connection",
            "accept-encoding",
            "transfer-encoding",
        ):
            continue
        out[k] = v
    return out


@router.post("/chat/completions")
async def chat_completions(request: Request):
    """Proxy + SSE-patch for chat completions (streaming or one-shot)."""
    body = await request.body()
    headers = _forward_headers(request)
    upstream_url = f"{UPSTREAM_BASE}/chat/completions"

    # Detect streaming vs one-shot from the request body (the upstream cares
    # about the same flag we do).
    stream_requested = False
    try:
        parsed = json.loads(body.decode("utf-8"))
        stream_requested = bool(parsed.get("stream"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass

    if not stream_requested:
        # One-shot: just forward and return the full response. No SSE to patch.
        async with httpx.AsyncClient(timeout=None) as client:
            r = await client.post(upstream_url, content=body, headers=headers)
        return JSONResponse(
            content=r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
            status_code=r.status_code,
        )

    return StreamingResponse(
        _proxy_stream(upstream_url, headers, body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.api_route("/{rest:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def passthrough(rest: str, request: Request):
    """Anything other than /chat/completions just passes through unchanged."""
    body = await request.body()
    headers = _forward_headers(request)
    upstream_url = f"{UPSTREAM_BASE}/{rest}"
    async with httpx.AsyncClient(timeout=None) as client:
        r = await client.request(
            request.method, upstream_url, content=body, headers=headers,
            params=request.query_params,
        )
    return JSONResponse(
        content=r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
        status_code=r.status_code,
    )
