// Browser-side client for the backend Gradbot voice WebSocket.
//
// Gradbot ships its own audio worklet + Opus encoder + synced player as three
// JS bundles served by the backend at /static/js/. This module:
//   1. Loads those bundles (cross-origin OK — backend has CORS allow-all).
//   2. Spins up SyncedAudioPlayer (a global the bundles install on window).
//   3. Opens the WS, pipes encoded Opus frames out, plays back incoming audio,
//      surfaces text/event/level callbacks.
//
// The backend WS is /ws/voice/{task_type}/{user_id}.

const SCRIPT_FILES = [
  "opus-encoder.js",
  "audio-processor.js",
  "synced-audio-player.js",
] as const;

const SCRIPT_TAG_DATA_ATTR = "data-catchup-gradbot";

interface SyncedAudioPlayerOptions {
  basePath: string;
  sampleRate: number;
  pcmOutput: boolean;
  echoCancellation: boolean;
  onEncodedAudio: (data: ArrayBuffer) => void;
  onText?: (info: { text: string; turnIdx: number; isUser: boolean }) => void;
  onEvent?: (eventType: string, msg: unknown) => void;
}

interface AudioProcessorInternal {
  inputAnalyser?: AnalyserNode;
  outputAnalyser?: AnalyserNode;
}

interface SyncedAudioPlayerInstance {
  start: () => Promise<void>;
  stop: () => void;
  handleMessage: (data: unknown) => void;
  audioProcessor?: AudioProcessorInternal;
}

declare global {
  interface Window {
    SyncedAudioPlayer: new (opts: SyncedAudioPlayerOptions) => SyncedAudioPlayerInstance;
  }
}

let scriptsPromise: Promise<void> | null = null;

/**
 * Resolve the HTTP base URL for backend assets. Same logic in dev (Vite proxy)
 * and prod (absolute URL). Exported so callers can pre-warm scripts before
 * the user gesture that opens the call.
 */
export function getHttpBase(): string {
  const useProxy = import.meta.env.DEV;
  if (useProxy) return window.location.origin;
  const fromEnv = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "");
  if (!fromEnv) throw new Error("VITE_API_BASE_URL must be set");
  return fromEnv;
}

/** Dynamically inject the Gradbot bundle <script> tags. Idempotent. */
export function loadGradbotScripts(httpBase: string = getHttpBase()): Promise<void> {
  if (scriptsPromise) return scriptsPromise;
  scriptsPromise = (async () => {
    for (const name of SCRIPT_FILES) {
      const src = `${httpBase}/static/js/${name}`;
      const existing = document.querySelector(
        `script[${SCRIPT_TAG_DATA_ATTR}="${name}"]`,
      );
      if (existing) continue;
      await new Promise<void>((resolve, reject) => {
        const tag = document.createElement("script");
        tag.src = src;
        tag.async = false; // preserve load order
        tag.setAttribute(SCRIPT_TAG_DATA_ATTR, name);
        tag.onload = () => resolve();
        tag.onerror = () =>
          reject(new Error(`Failed to load Gradbot bundle: ${name}`));
        document.head.appendChild(tag);
      });
    }
  })().catch((err) => {
    // Reset so a future call can retry.
    scriptsPromise = null;
    throw err;
  });
  return scriptsPromise;
}

interface AudioConfigResponse {
  pcm?: boolean;
}

export interface VoiceCallHandlers {
  /** Called once the player is started AND the WS reaches OPEN. */
  onConnected?: () => void;
  /** Streaming transcript chunk (word-by-word). */
  onTranscript?: (info: { text: string; turnIdx: number; isUser: boolean }) => void;
  /** Custom backend events (websocket.send_json on the server). */
  onEvent?: (eventType: string, msg: unknown) => void;
  /** Periodic input/output level update (0..1). Driven by requestAnimationFrame. */
  onLevel?: (info: { input: number; output: number }) => void;
  /** WS closed — for any reason. */
  onClose?: (event: CloseEvent) => void;
  /** Any error — surface it but don't auto-reconnect. */
  onError?: (error: unknown) => void;
}

export interface VoiceCallHandle {
  /** Cleanly tear everything down: stop mic, close WS, release audio context. */
  close: () => void;
}

export interface OpenVoiceCallOptions {
  /** "onboarding" or "feedback". */
  taskType: "onboarding" | "feedback";
  /** Authenticated user id. */
  userId: string;
  /** Optional catchup id — passed to the backend to personalise the
      feedback prompt and persist the result against the right catchup. */
  catchupId?: string;
  /** Spoken language sent in the WS start handshake. Defaults to "en". */
  language?: "en" | "fr" | "es" | "de" | "pt";
  /** TTS speed multiplier (0.5..2.0). Defaults to 1.0. */
  speed?: number;
  /** Handlers for connection state and incoming data. */
  handlers?: VoiceCallHandlers;
}

function rms(analyser: AnalyserNode, buffer: Uint8Array): number {
  analyser.getByteTimeDomainData(buffer);
  let sumSq = 0;
  for (let i = 0; i < buffer.length; i++) {
    const v = (buffer[i] - 128) / 128; // -1..1
    sumSq += v * v;
  }
  // Boost the visual gain so casual speech reads visibly on the meter.
  // The signal SENT to Gradium is unaffected — this only scales the
  // RMS that drives the on-screen bars.
  return Math.min(1, Math.sqrt(sumSq / buffer.length) * 6);
}

/**
 * Open a Gradbot voice WebSocket for the given user/task. Returns a handle
 * with a `close()` method. Mic permission is requested by SyncedAudioPlayer.
 *
 * Sequence (matches the working Gradbot reference flow):
 *   1. Load bundles + fetch audio-config.
 *   2. Construct + start SyncedAudioPlayer (mic prompt happens here, in the
 *      user-gesture trace that triggered openVoiceCall).
 *   3. ONLY then create the WebSocket and attach handlers.
 *   4. On open, send {type:"start", language, speed} — gradbot needs the
 *      language to bootstrap STT, otherwise the session stays silent.
 */
export async function openVoiceCall({
  taskType,
  userId,
  catchupId,
  language = "en",
  speed = 1.0,
  handlers = {},
}: OpenVoiceCallOptions): Promise<VoiceCallHandle> {
  const useProxy = import.meta.env.DEV;
  const httpBase = getHttpBase();
  const wsBase = useProxy
    ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`
    : (import.meta.env.VITE_WS_BASE_URL as string | undefined)?.replace(/\/$/, "");
  if (!wsBase) {
    throw new Error("VITE_WS_BASE_URL must be set");
  }

  await loadGradbotScripts(httpBase);

  if (typeof window.SyncedAudioPlayer !== "function") {
    throw new Error("SyncedAudioPlayer global was not installed by Gradbot bundles");
  }

  const audioConfigRes = await fetch(`${httpBase}/api/audio-config`);
  const audioConfig: AudioConfigResponse = audioConfigRes.ok
    ? await audioConfigRes.json().catch(() => ({}))
    : {};

  let isRunning = false;
  let closed = false;
  let levelRafId = 0;
  let audioFrames = 0;
  let ws: WebSocket | null = null;

  const player = new window.SyncedAudioPlayer({
    basePath: `${httpBase}/static/js`,
    sampleRate: 24000,
    pcmOutput: Boolean(audioConfig.pcm),
    echoCancellation: true, // CRITICAL: prevents the agent hearing its own TTS
    onEncodedAudio: (opusData) => {
      if (!isRunning) return;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(opusData);
      }
    },
    onText: (info) => {
      handlers.onTranscript?.(info);
    },
    onEvent: (eventType, msg) => {
      handlers.onEvent?.(eventType, msg);
    },
  });

  const cleanup = () => {
    if (closed) return;
    closed = true;
    isRunning = false;
    if (levelRafId) cancelAnimationFrame(levelRafId);
    levelRafId = 0;
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      try {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "stop" }));
        }
        ws.close();
      } catch {
        /* swallow */
      }
    }
    try {
      player.stop();
    } catch {
      /* swallow */
    }
  };

  // 1. Get the audio pipeline running BEFORE opening the WS — same order as
  //    Gradbot's reference demo. This avoids a race where the WS reaches OPEN
  //    while we're still awaiting getUserMedia and worklet setup.
  try {
    await player.start();
  } catch (err) {
    cleanup();
    throw err;
  }

  // 2. Only now open the WebSocket. By the time it reaches OPEN, the player
  //    is fully initialized so we can immediately negotiate the start frame.
  //    NOTE: do NOT set ws.binaryType — SyncedAudioPlayer expects Blob frames
  //    (which is the default).
  const wsUrl = (() => {
    const base = `${wsBase}/ws/voice/${encodeURIComponent(taskType)}/${encodeURIComponent(userId)}`;
    if (!catchupId) return base;
    return `${base}?catchup_id=${encodeURIComponent(catchupId)}`;
  })();
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    isRunning = true;
    try {
      ws!.send(JSON.stringify({ type: "start", language, speed }));
    } catch (err) {
      handlers.onError?.(err);
    }
    handlers.onConnected?.();
  };

  ws.onmessage = (event) => {
    if (event.data instanceof Blob) {
      audioFrames += 1;
      if (audioFrames === 1 || audioFrames % 25 === 0) {
        console.debug("[voice] received audio frame", audioFrames, "size", event.data.size);
      }
    }
    try {
      player.handleMessage(event.data);
    } catch (err) {
      handlers.onError?.(err);
    }
  };

  ws.onerror = (event) => {
    handlers.onError?.(event);
  };

  ws.onclose = (event) => {
    isRunning = false;
    handlers.onClose?.(event);
    cleanup();
  };

  // Hook into the SyncedAudioPlayer's internal analysers to surface live
  // input/output levels for the UI. The analysers exist after start().
  if (handlers.onLevel) {
    const inputAnalyser = player.audioProcessor?.inputAnalyser;
    const outputAnalyser = player.audioProcessor?.outputAnalyser;
    if (inputAnalyser || outputAnalyser) {
      const inBuf = inputAnalyser ? new Uint8Array(inputAnalyser.fftSize) : null;
      const outBuf = outputAnalyser ? new Uint8Array(outputAnalyser.fftSize) : null;
      const tick = () => {
        if (closed) return;
        const input = inputAnalyser && inBuf ? rms(inputAnalyser, inBuf) : 0;
        const output = outputAnalyser && outBuf ? rms(outputAnalyser, outBuf) : 0;
        handlers.onLevel?.({ input, output });
        levelRafId = requestAnimationFrame(tick);
      };
      levelRafId = requestAnimationFrame(tick);
    }
  }

  return { close: cleanup };
}
