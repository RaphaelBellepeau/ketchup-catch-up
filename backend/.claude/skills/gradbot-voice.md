# Skill: Gradbot Voice Agent Integration

## When to use
When working on any voice feature in Catch-Up: onboarding vocal, feedback vocal, ou tout futur cas d'usage voix.

## What is Gradbot
Gradbot is a Python voice agent framework by Gradium. It orchestrates STT → LLM → TTS in a single event loop via a Rust multiplexer. We use it for in-browser voice conversations (WebSocket audio, not phone calls).

## Architecture in Catch-Up

```
Browser (Lovable) ──WebSocket──→ FastAPI endpoint ──→ Gradbot session
                                                        ├── Gradium STT (speech → text)
                                                        ├── LLM (text → response)
                                                        └── Gradium TTS (response → speech)
```

The browser sends Opus-encoded audio via WebSocket. Gradbot handles VAD, turn-taking, interruptions, and tool calls automatically.

## Installation

```bash
pip install gradbot
# gradbot includes: fastapi, uvicorn[standard], pydantic-settings, pyyaml
```

## Required env vars

```bash
GRADIUM_API_KEY=grd_...          # Gradium STT/TTS
LLM_API_KEY=...                  # OpenAI-compatible LLM key
LLM_BASE_URL=...                 # e.g. https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-2.5-flash       # Any OpenAI-compatible model
```

## Config loading

```python
import gradbot

# Load from config.yaml in current dir (+ parent dir inheritance)
cfg = gradbot.config.from_env()

# cfg exposes:
# cfg.client_kwargs   → dict for gradbot.run() (LLM/Gradium API creds)
# cfg.session_kwargs  → dict for SessionConfig (flush_duration_s, silence_timeout_s, etc.)
# cfg.audio_format    → AudioFormat.OggOpus or .Pcm
# cfg.debug           → bool
```

## config.yaml (place next to main.py)

```yaml
llm:
  model: "gemini-2.5-flash"
  base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"

tts:
  padding_bonus: 0.0
  rewrite_rules: "fr"

stt:
  flush_duration_s: 0.5

session:
  silence_timeout_s: 0.0    # CRITICAL: 0.0 to avoid agent re-prompting itself
  assistant_speaks_first: true
```

## Backend pattern — with tools (our use case)

We use the "tool-using agent" pattern. Gradbot calls our tool `save_result` when the LLM has extracted enough info from the conversation.

```python
import json
import fastapi
import gradbot

app = fastapi.FastAPI()
cfg = gradbot.config.from_env()

# 1. Define tools — parameters_json MUST be a JSON string via json.dumps()
tools = [
    gradbot.ToolDef(
        "save_result",                          # name
        "Save extracted info from the conversation. Call when you have enough data.",  # description: say WHEN to call
        json.dumps({                            # parameters_json — MUST be json.dumps()
            "type": "object",
            "properties": {
                "cuisines_liked": {
                    "type": "string",            # NEVER use "type": "array" — use string + comma-separated
                    "description": "Comma-separated list of liked cuisines",
                },
                "budget_range": {
                    "type": "string",
                    "description": "low, medium, or high",
                },
            },
            "required": ["cuisines_liked", "budget_range"],
        }),
    ),
]

# 2. on_start callback — returns SessionConfig
def on_start(msg: dict) -> gradbot.SessionConfig:
    return gradbot.SessionConfig(
        voice_id="X8-_I8yFvYONny54",
        instructions="Tu es l'assistant Catch-Up...",
        language=gradbot.Lang.Fr,
        tools=tools,
        assistant_speaks_first=True,
        silence_timeout_s=0.0,       # CRITICAL: avoid self-reprompting
        **cfg.session_kwargs,        # merge YAML settings (they override)
    )

# 3. on_tool_call — 3 args: (handle, input_handle, websocket)
async def on_tool_call(handle, input_handle, websocket):
    if handle.name == "save_result":
        args = handle.args                       # already a dict (auto-deserialized)
        # Process and save...
        await handle.send_json({"status": "saved"})  # send result back to LLM
    else:
        await handle.send_error(f"Unknown tool: {handle.name}")

# 4. WebSocket endpoint
@app.websocket("/ws/voice/{task_type}/{user_id}")
async def ws_voice(websocket: fastapi.WebSocket, task_type: str, user_id: str):
    await gradbot.websocket.handle_session(
        websocket,
        config=cfg,                  # auto-sets run_kwargs, output_format, debug
        on_start=on_start,
        on_tool_call=on_tool_call,   # OMIT this entirely if no tools needed
    )

# 5. Serve static files (audio worklet JS for the browser)
gradbot.routes.setup(
    app,
    config=cfg,
    static_dir=pathlib.Path(__file__).parent / "static",
)
```

## Tool API reference

```python
# Tool definition
gradbot.ToolDef(name, description, parameters_json)
# parameters_json MUST be json.dumps({...}), NOT a raw dict
# NEVER use "type": "array" — use "type": "string" with "Comma-separated list"

# Tool handle (received as first arg in on_tool_call)
handle.name                      # str — tool name
handle.args                      # dict — parsed args (already deserialized)
handle.send(json.dumps({...}))   # send raw JSON string to LLM
handle.send_json({...})          # send dict to LLM (auto-serializes) — PREFERRED
handle.send_error("message")     # send error to LLM

# Session control (second arg in on_tool_call)
input_handle.send_config(new_config)  # swap prompt/voice/tools mid-session

# WebSocket (third arg in on_tool_call)
websocket.send_json({"type": "custom_event", ...})  # send UI update to frontend
```

## Session config reference

```python
gradbot.SessionConfig(
    voice_id="X8-_I8yFvYONny54",     # Gradium voice ID
    instructions="System prompt...",   # system prompt for the LLM
    language=gradbot.Lang.Fr,          # Lang.En, .Fr, .Es, .De, .Pt
    tools=[...],                       # list of ToolDef (or empty)
    assistant_speaks_first=True,       # agent greets first
    silence_timeout_s=0.0,            # ALWAYS 0.0 to avoid re-prompting
    flush_duration_s=0.5,             # STT flush delay
    padding_bonus=0.0,
    rewrite_rules="fr",               # language code string for TTS rewriting
)
```

## Language helpers

```python
gradbot.Lang.En, .Fr, .Es, .De, .Pt
gradbot.LANGUAGES          # dict: "en" → Lang.En, "fr" → Lang.Fr, ...
gradbot.LANGUAGE_NAMES      # dict: "en" → "English", "fr" → "French", ...
```

## Mid-session reconfiguration

To swap prompt, voice, or tools during a conversation (e.g. switching from onboarding questions to confirmation):

```python
async def on_tool_call(handle, input_handle, websocket):
    if handle.name == "save_result":
        # ... save data ...
        
        # Switch to a "thank you" prompt
        new_config = gradbot.SessionConfig(
            voice_id="X8-_I8yFvYONny54",
            instructions="L'utilisateur a terminé l'onboarding. Remercie-le et dis au revoir.",
            language=gradbot.Lang.Fr,
            tools=[],                    # no more tools needed
            assistant_speaks_first=False,
        )
        await input_handle.send_config(new_config)
        await handle.send_json({"status": "saved"})
```

## Frontend integration

The frontend MUST load Gradbot's bundled JS via three script tags (NOT ES module imports):

```html
<script src="/static/js/opus-encoder.js"></script>
<script src="/static/js/audio-processor.js"></script>
<script src="/static/js/synced-audio-player.js"></script>
```

These are served automatically by `gradbot.routes.setup()`. SyncedAudioPlayer is a global.

### Minimal frontend JS to connect:

```javascript
let ws = null;
let player = null;
let isRecording = false;

async function startCall() {
    const audioConfig = await fetch('/api/audio-config').then(r => r.json());
    
    player = new SyncedAudioPlayer({
        basePath: '/static/js',
        sampleRate: 24000,
        pcmOutput: audioConfig.pcm || false,
        echoCancellation: true,         // CRITICAL: prevents feedback loop
        onEncodedAudio: (opusData) => {
            if (isRecording && ws?.readyState === WebSocket.OPEN) ws.send(opusData);
        },
        onText: ({ text, turnIdx, isUser }) => {
            // CRITICAL: destructure single object, NOT separate args
            appendTranscript(text, turnIdx, isUser);
        },
        onEvent: (eventType, msg) => {
            // Handle custom messages from backend (websocket.send_json)
            handleCustomMessage(msg);
        },
    });

    await player.start();

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/voice/onboarding/user123`);

    ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'start', speed: 1.0 }));
        isRecording = true;
    };

    ws.onmessage = (event) => player.handleMessage(event.data);
    ws.onclose = () => endCall();
}

function endCall() {
    isRecording = false;
    ws?.close();
    player?.stop();
}
```

### Transcript display (word-by-word streaming):

```javascript
let turnBubbles = {};
let userBubble = null;
let hadAssistantBubble = false;

function getBubbleForTurn(turnIdx, isUser) {
    if (isUser) {
        if (userBubble && !hadAssistantBubble) return userBubble;
        hadAssistantBubble = false;
        userBubble = document.createElement('div');
        userBubble.className = 'msg msg-user';
        const tx = document.createElement('span');
        tx.className = 'msg-text';
        userBubble.appendChild(tx);
        transcript.appendChild(userBubble);
        return userBubble;
    }
    let bubble = turnBubbles[turnIdx];
    if (!bubble) {
        hadAssistantBubble = true;
        bubble = document.createElement('div');
        bubble.className = 'msg msg-agent';
        const tx = document.createElement('span');
        tx.className = 'msg-text';
        bubble.appendChild(tx);
        transcript.appendChild(bubble);
        turnBubbles[turnIdx] = bubble;
    }
    return bubble;
}

function appendTranscript(text, turnIdx, isUser) {
    const bubble = getBubbleForTurn(turnIdx, isUser);
    bubble.querySelector('.msg-text').textContent += text + ' ';
    transcript.scrollTop = transcript.scrollHeight;
}
```

## Critical rules — DO NOT FORGET

1. **silence_timeout_s = 0.0** — always. Default 5s causes agent to re-prompt itself.
2. **parameters_json = json.dumps({...})** — must be a JSON string, not a dict.
3. **NEVER "type": "array"** in tool params — use "type": "string" + "Comma-separated list".
4. **on_tool_call takes 3 args**: (handle, input_handle, websocket).
5. **handle.args is already a dict** — don't json.loads() it again.
6. **handle.send_json({...})** preferred over handle.send(json.dumps({...})).
7. **Frontend: three script tags**, NOT ES module imports. SyncedAudioPlayer is a global.
8. **Frontend: onText destructures a single object** — `({ text, turnIdx, isUser })`.
9. **Echo cancellation checkbox** on frontend — without it, agent hears its own TTS output.
10. **Tool descriptions say WHEN to call** — "Call when you have enough info" not just "Save data".

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Agent gives long responses | Add to prompt: "Keep ALL responses to 1-2 SHORT sentences. This is voice." |
| Agent repeats itself when user is silent | Set `silence_timeout_s=0.0` |
| Tool calls fail with "Invalid JSON" | Use `handle.send_json({...})` not `handle.send(raw_string)` |
| Audio doesn't play in browser | Check three script tags loaded (not ES imports) |
| Agent hears its own voice | Add echo cancellation checkbox wired to SyncedAudioPlayer |
| Transcript shows [object Object] | onText receives single object, destructure it |
| WebSocket 404 | `gradbot.routes.setup()` must be called. Also need `uvicorn[standard]`. |
