import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Mic, X } from "lucide-react";
import { LiveLevels } from "@/components/LiveLevels";
import { useProfile } from "@/hooks/useProfile";
import {
  loadGradbotScripts,
  openVoiceCall,
  type VoiceCallHandle,
} from "@/lib/voiceClient";

const FALLBACK_DELAY_MS = 4000;

type CallState =
  | "idle"
  | "connecting"
  | "live"
  | "completed"
  | "mic-denied"
  | "error";

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
  // Tracks which agent turn the current caption belongs to. When the agent
  // starts a new turn we wipe the caption so we never display the running
  // concatenation of every word the agent ever said.
  const captionTurnRef = useRef<number | null>(null);
  useEffect(() => {
    refetchRef.current = refetch;
    navigateRef.current = navigate;
  });

  // If a user lands on /voice-call when they've already onboarded — e.g. by
  // refreshing the page or hitting Back — push them forward to the next
  // logical step rather than restarting the conversation. Likewise, if they
  // don't have a name yet (skipped or hit /voice-call directly), bounce
  // them to /name first. Both only fire BEFORE any call starts so we never
  // hijack the green-check confirmation mid-completion.
  useEffect(() => {
    if (callState !== "idle") return;
    if (isOnboarded) {
      navigate("/onboarding/permissions", { replace: true });
      return;
    }
    if (profile && !profile.name?.trim()) {
      navigate("/onboarding/name", { replace: true });
    }
  }, [isOnboarded, callState, profile, navigate]);

  // Pre-load the Gradbot bundles so the user gesture handler can move
  // straight into player.start() without long awaits in between.
  useEffect(() => {
    loadGradbotScripts().catch((err) => console.warn("[voice] preload failed", err));
  }, []);

  const startCall = useCallback(async () => {
    if (!userId) return;
    if (callState === "connecting" || callState === "live" || callState === "completed") return;

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
            captionTurnRef.current = null;
          },
          onTranscript: ({ text, turnIdx, isUser }) => {
            if (cancelled || isUser) return;
            // Display the agent's words only — user words are noisy here.
            // Reset the caption when the agent starts a new turn so we
            // don't show a growing wall of every sentence ever spoken.
            setCaption((prev) => {
              const isNewTurn = captionTurnRef.current !== turnIdx;
              captionTurnRef.current = turnIdx;
              if (isNewTurn) return text.trim();
              const candidate = `${prev} ${text}`.trim();
              // Hard cap at ~180 chars so a long sentence still fits 2-3
              // lines on a phone screen — keep the tail (most recent words).
              return candidate.length > 180 ? candidate.slice(-180) : candidate;
            });
          },
          onEvent: (eventType, msg) => {
            console.debug("[voice] event", eventType, msg);
            // Backend signals the save tool completed → flip to the green-
            // check screen while the agent's final sentence plays out. The
            // user manually taps "Next" to move on (no auto-redirect).
            if (eventType === "onboarding_saved") {
              if (cancelled) return;
              setCallState("completed");
              setCaption("Information saved");
              refetchRef.current().catch(() => {
                /* refetch best-effort — guards still let user proceed */
              });
            }
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
            // If the agent already saved (and we flipped to the completed
            // screen), keep the user on it so they can tap Next. Otherwise
            // refetch — if onboarded_at is set anyway, show completed; else
            // surface the retry/skip UX.
            try {
              const result = await refetchRef.current();
              const onboarded = Boolean(result?.data?.onboarded_at);
              if (onboarded) {
                setCallState("completed");
                setCaption("Information saved");
                return;
              }
            } catch {
              /* fall through to retry UX */
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

  const handleNext = () => {
    handleRef.current?.close();
    navigate("/onboarding/permissions", { replace: true });
  };

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
  const isCompleted = callState === "completed";

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
            {isCompleted ? "ALL DONE" : isLive ? `LIVE · ${mm}:${ss}` : "INCOMING"}
          </div>
          <h1 className="text-h1 font-medium mt-2">ketchup agent</h1>
          <p className="text-body mt-1 text-cream/90">
            {isCompleted
              ? "Got everything I need"
              : isLive
                ? "Talking to your agent"
                : "Tap the mic to start"}
          </p>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center px-8 gap-8">
          {isCompleted ? (
            <div
              className="w-32 h-32 rounded-full bg-mint flex items-center justify-center shadow-lg animate-in zoom-in duration-300"
              aria-label="Information saved"
            >
              <Check className="w-16 h-16 text-navy" strokeWidth={3} />
            </div>
          ) : (
            <button
              type="button"
              onClick={startCall}
              disabled={isStarting || isLive || !userId}
              aria-label={isLive ? "Microphone active" : "Start call"}
              className="w-32 h-32 rounded-full bg-cream flex items-center justify-center shadow-lg disabled:opacity-90 active:scale-95 transition-transform"
            >
              <Mic className="w-12 h-12 text-ketchup-red" strokeWidth={2} />
            </button>
          )}

          {isCompleted ? null : (
            <>
              <LiveLevels
                inputLevel={inputLevel}
                outputLevel={outputLevel}
                bars={18}
                className="h-12"
              />
              <div className="flex items-center gap-4 text-meta text-cream/80">
                <span>YOU</span>
                <span className="opacity-60">·</span>
                <span>AGENT</span>
              </div>
            </>
          )}

          <p className="text-body italic text-cream text-center max-w-[280px] leading-relaxed">
            {isCompleted ? "Information saved." : `"${caption}"`}
          </p>
        </div>

        <div className="px-8 pb-10 flex items-center justify-between min-h-[64px]">
          {isCompleted ? (
            <button
              type="button"
              onClick={handleNext}
              className="w-full h-14 rounded-pill bg-mint text-navy text-h3 font-semibold shadow-lg active:scale-[0.99] transition-transform"
            >
              Next
            </button>
          ) : (
            <>
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
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default VoiceCall;
