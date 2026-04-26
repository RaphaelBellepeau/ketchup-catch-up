import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, X } from "lucide-react";
import { LiveLevels } from "@/components/LiveLevels";
import { useProfile } from "@/hooks/useProfile";
import {
  loadGradbotScripts,
  openVoiceCall,
  type VoiceCallHandle,
} from "@/lib/voiceClient";

const FALLBACK_DELAY_MS = 4000;

type CallState = "idle" | "connecting" | "live" | "mic-denied" | "error";

const VoiceCall = () => {
  const navigate = useNavigate();
  const { session, profile, isOnboarded, refetch } = useProfile();
  const userId = session?.user.id ?? profile?.id ?? null;

  const [caption, setCaption] = useState("Tap to start the call");
  const [elapsed, setElapsed] = useState(0);
  const [callState, setCallState] = useState<CallState>("idle");
  const [showSkip, setShowSkip] = useState(false);
  const [inputLevel, setInputLevel] = useState(0);
  const [outputLevel, setOutputLevel] = useState(0);

  const handleRef = useRef<VoiceCallHandle | null>(null);
  // Stable refs so the effect closure can read the latest values without
  // forcing the open effect to re-run on every render.
  const refetchRef = useRef(refetch);
  const navigateRef = useRef(navigate);
  useEffect(() => {
    refetchRef.current = refetch;
    navigateRef.current = navigate;
  });

  // If the user already finished onboarding, bounce them to /home immediately.
  useEffect(() => {
    if (isOnboarded) {
      navigate("/home", { replace: true });
    }
  }, [isOnboarded, navigate]);

  // Pre-load the Gradbot bundles so the user gesture handler can move
  // straight into player.start() without long awaits in between.
  useEffect(() => {
    loadGradbotScripts().catch((err) => console.warn("[voice] preload failed", err));
  }, []);

  const startCall = useCallback(async () => {
    if (!userId) return;
    if (callState === "connecting" || callState === "live") return;

    setCallState("connecting");
    setShowSkip(false);
    setCaption("Connecting your agent…");

    let cancelled = false;
    const cleanup = () => {
      cancelled = true;
      handleRef.current?.close();
      handleRef.current = null;
    };

    try {
      const handle = await openVoiceCall({
        taskType: "onboarding",
        userId,
        handlers: {
          onConnected: () => {
            if (cancelled) return;
            setCallState("live");
            setCaption("Hi! Let's get to know you a bit.");
          },
          onTranscript: ({ text, isUser }) => {
            if (cancelled || isUser) return;
            // Display the agent's words; user words are noisy on screen.
            setCaption((prev) => (prev.endsWith(text) ? prev : `${prev} ${text}`.trim()));
          },
          onEvent: (eventType, msg) => {
            console.debug("[voice] event", eventType, msg);
          },
          onLevel: ({ input, output }) => {
            if (cancelled) return;
            setInputLevel(input);
            setOutputLevel(output);
          },
          onError: (err) => {
            console.warn("[voice] runtime error", err);
          },
          onClose: async () => {
            if (cancelled) return;
            try {
              const result = await refetchRef.current();
              if (result?.data?.onboarded_at) {
                navigateRef.current("/onboarding/permissions", { replace: true });
                return;
              }
            } catch {
              /* fall through to skip UX */
            }
            setCallState("idle");
            setShowSkip(true);
            setCaption("Hmm, I didn't catch enough. Try again or skip for the demo.");
          },
        },
      });
      if (cancelled) {
        handle.close();
        return;
      }
      handleRef.current = handle;
    } catch (err) {
      const isMicDenied =
        err instanceof DOMException &&
        (err.name === "NotAllowedError" || err.name === "SecurityError");
      console.warn("[voice] failed to open", err);
      setCallState(isMicDenied ? "mic-denied" : "error");
      setCaption(
        isMicDenied
          ? "Mic access blocked. Allow it in your browser, then tap retry."
          : "Couldn't start the call. Try again or skip for the demo.",
      );
      setShowSkip(true);
    }

    return cleanup;
  }, [userId, callState]);

  // Cleanup any active call when leaving the screen.
  useEffect(() => {
    return () => {
      handleRef.current?.close();
      handleRef.current = null;
    };
  }, []);

  // Demo-mode safety: if the user keeps the screen open without ever
  // connecting, surface the skip button after a delay.
  useEffect(() => {
    if (callState === "live") return;
    const t = window.setTimeout(() => setShowSkip(true), FALLBACK_DELAY_MS);
    return () => window.clearTimeout(t);
  }, [callState]);

  // Call timer (only ticks while live).
  useEffect(() => {
    if (callState !== "live") return;
    const id = window.setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, [callState]);

  const handleEnd = () => {
    handleRef.current?.close();
    // The onClose handler above will refetch & route appropriately.
  };

  const handleSkip = async () => {
    handleRef.current?.close();
    try {
      const result = await refetch();
      if (result?.data?.onboarded_at) {
        navigate("/onboarding/permissions", { replace: true });
        return;
      }
    } catch {
      /* fall through */
    }
    navigate("/onboarding/permissions", { state: { demo: true } });
  };

  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  const isLive = callState === "live";
  const isStarting = callState === "connecting";

  return (
    <div className="min-h-screen bg-cream/40">
      <div className="max-w-[420px] mx-auto min-h-screen bg-ketchup-red text-cream flex flex-col">
        {/* Status bar */}
        <div className="flex items-center justify-between px-6 pt-3 pb-2 text-h3">
          <span className="font-medium tabular-nums">9:42</span>
          <span className="text-cream/90 tracking-wider">• • •</span>
        </div>

        <div className="px-6 pt-2">
          <div className="text-meta text-cream/80">
            {isLive ? `LIVE · ${mm}:${ss}` : "INCOMING"}
          </div>
          <h1 className="text-h1 font-medium mt-2">ketchup agent</h1>
          <p className="text-body mt-1 text-cream/90">
            {isLive ? "Talking to your agent" : "Tap the mic to start"}
          </p>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center px-8 gap-8">
          <button
            type="button"
            onClick={startCall}
            disabled={isStarting || isLive || !userId}
            aria-label={isLive ? "Microphone active" : "Start call"}
            className="w-32 h-32 rounded-full bg-cream flex items-center justify-center shadow-lg disabled:opacity-90 active:scale-95 transition-transform"
          >
            <Mic className="w-12 h-12 text-ketchup-red" strokeWidth={2} />
          </button>

          <LiveLevels inputLevel={inputLevel} outputLevel={outputLevel} bars={18} className="h-12" />
          <div className="flex items-center gap-4 text-meta text-cream/80">
            <span>YOU</span>
            <span className="opacity-60">·</span>
            <span>AGENT</span>
          </div>

          <p className="text-body italic text-cream text-center max-w-[280px] leading-relaxed">
            "{caption}"
          </p>
        </div>

        <div className="px-8 pb-10 flex items-center justify-between">
          <button
            type="button"
            className="w-12 h-12 rounded-full bg-cream/20 flex items-center justify-center text-cream"
            aria-label="Mute microphone"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M3 3l18 18M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V5a3 3 0 0 0-5.94-.6M19 10v2a7 7 0 0 1-.11 1.23M5 10v2a7 7 0 0 0 12 5"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>

          {showSkip ? (
            <button
              type="button"
              onClick={handleSkip}
              className="rounded-pill bg-navy text-cream px-4 h-12 text-body font-medium"
            >
              Skip onboarding (demo)
            </button>
          ) : null}

          <button
            type="button"
            onClick={handleEnd}
            disabled={!isLive}
            className="w-14 h-14 rounded-full bg-navy text-cream flex items-center justify-center disabled:opacity-50"
            aria-label="End call"
          >
            <X className="w-6 h-6" strokeWidth={2.5} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default VoiceCall;
