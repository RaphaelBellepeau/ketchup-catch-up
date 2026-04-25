// Lightweight WebSocket helper for the onboarding voice call.
// Streams mic audio to the agent and plays back incoming agent audio chunks.
// Also surfaces text messages (transcript snippets) to the caller.
//
// This is intentionally minimal — no resampling, no jitter buffer, no VAD.
// The real Gradbot service handles all of that on the server side.

export interface VoiceSocketHandlers {
  /** Called when the WS reaches OPEN state. */
  onOpen?: () => void;
  /** Text message from the agent (e.g. transcript snippet for caption). */
  onText?: (text: string) => void;
  /** Called when the WS closes for any reason. */
  onClose?: (event: CloseEvent) => void;
  /** Called on any error (WS or audio). */
  onError?: (error: unknown) => void;
}

export interface VoiceSocketHandle {
  /** Cleanly tear down: stops mic, closes audio context and WS. */
  close: () => void;
  /** Underlying socket — exposed for debugging only. */
  socket: WebSocket;
}

const SAMPLE_RATE = 16000;

/**
 * Open a bidirectional voice WebSocket.
 *
 * Wire format (kept simple for the demo):
 *  - Browser → server: raw 16-bit PCM frames (ArrayBuffer) at 16kHz mono.
 *  - Server → browser: either binary PCM frames to play back, OR JSON text
 *    messages of the shape `{ "type": "transcript", "text": "..." }` for
 *    captions. Any non-JSON text is shown verbatim.
 */
export async function openVoiceSocket(
  url: string,
  handlers: VoiceSocketHandlers = {},
): Promise<VoiceSocketHandle> {
  const socket = new WebSocket(url);
  socket.binaryType = "arraybuffer";

  // Audio context for both capture and playback.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const AudioCtx: typeof AudioContext = window.AudioContext || (window as any).webkitAudioContext;
  const audioCtx = new AudioCtx({ sampleRate: SAMPLE_RATE });

  let micStream: MediaStream | null = null;
  let micSource: MediaStreamAudioSourceNode | null = null;
  let processor: ScriptProcessorNode | null = null;
  let playbackTime = 0;
  let closed = false;

  const cleanup = () => {
    if (closed) return;
    closed = true;
    try {
      processor?.disconnect();
      micSource?.disconnect();
      micStream?.getTracks().forEach((t) => t.stop());
      audioCtx.close();
    } catch {
      /* swallow */
    }
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      try {
        socket.close();
      } catch {
        /* swallow */
      }
    }
  };

  socket.addEventListener("open", async () => {
    try {
      // Mic capture only after the WS is open so we don't waste user permission.
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micSource = audioCtx.createMediaStreamSource(micStream);
      // ScriptProcessor is deprecated but ubiquitous — fine for a demo path.
      processor = audioCtx.createScriptProcessor(2048, 1, 1);
      processor.onaudioprocess = (e) => {
        if (socket.readyState !== WebSocket.OPEN) return;
        const input = e.inputBuffer.getChannelData(0);
        const pcm = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
          const s = Math.max(-1, Math.min(1, input[i]));
          pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        socket.send(pcm.buffer);
      };
      micSource.connect(processor);
      processor.connect(audioCtx.destination);
      handlers.onOpen?.();
    } catch (err) {
      handlers.onError?.(err);
    }
  });

  socket.addEventListener("message", (event) => {
    if (typeof event.data === "string") {
      // Try parse JSON for `{ type: "transcript", text }` shape; fallback to raw.
      try {
        const parsed = JSON.parse(event.data);
        if (parsed && typeof parsed.text === "string") {
          handlers.onText?.(parsed.text);
          return;
        }
      } catch {
        /* not JSON */
      }
      handlers.onText?.(event.data);
      return;
    }

    // Binary: assume 16-bit PCM mono at SAMPLE_RATE.
    const buffer = event.data as ArrayBuffer;
    const pcm = new Int16Array(buffer);
    if (pcm.length === 0) return;
    const audioBuffer = audioCtx.createBuffer(1, pcm.length, SAMPLE_RATE);
    const channel = audioBuffer.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) {
      channel[i] = pcm[i] / 0x8000;
    }
    const source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioCtx.destination);
    const startAt = Math.max(audioCtx.currentTime, playbackTime);
    source.start(startAt);
    playbackTime = startAt + audioBuffer.duration;
  });

  socket.addEventListener("error", (e) => handlers.onError?.(e));
  socket.addEventListener("close", (e) => {
    cleanup();
    handlers.onClose?.(e);
  });

  return {
    close: cleanup,
    socket,
  };
}
