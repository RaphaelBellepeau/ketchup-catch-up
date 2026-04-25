# Skill: Test an endpoint

## When to use
After creating or modifying any endpoint.

## Quick curl tests

```bash
# Health check
curl -s http://localhost:8000/health | python -m json.tool

# POST with JSON body
curl -s -X POST http://localhost:8000/catchups \
  -H "Content-Type: application/json" \
  -d '{"group_id": "xxx", "type": "one_shot", "time_window": "next 2 weeks", "vibe": "dinner"}' \
  | python -m json.tool

# GET with auth header
curl -s http://localhost:8000/users/me \
  -H "Authorization: Bearer $JWT" \
  | python -m json.tool

# SSE stream (negotiation)
curl -N http://localhost:8000/catchups/xxx/negotiate/stream

# WebSocket test (voice) — use websocat
websocat ws://localhost:8000/ws/voice/onboarding/test_user
```

## Pytest pattern

```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
```

## Rules
- Always test after creating/modifying an endpoint
- If test fails, fix before moving to next feature
- For SSE endpoints, verify the stream format: `data: {"agent": "...", "content": "..."}\n\n`
