import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Mic } from "lucide-react";
import { Layout } from "@/components/Layout";
import { Waveform } from "@/components/Waveform";
import { openVoiceSocket, type VoiceSocketHandle } from "@/lib/voiceSocket";

const FALLBACK_DELAY_MS = 3000;

interface RouteState {
  userId?: string;
  catchupId?: string;
}

const FeedbackVoice = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as RouteState;
  const userId = state.userId ?? "demo-user";
  const catchupId = state.catchupId ?? "demo";

  const [active, setActive] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [showWriteFallback, setShowWriteFallback] = useState(false);
  const socketRef = useRef<VoiceSocketHandle | null>(null);

  const handleStart = () => {
    if (active || connecting) return;
    const wsBase = import.meta.env.VITE_WS_BASE_URL as string | undefined;

    if (!wsBase) {
      // No WS configured — surface fallback right away.
      setShowWriteFallback(true);
      return;
    }

    setConnecting(true);
    const url = `${wsBase}/ws/voice/feedback/${encodeURIComponent(userId)}?catchup_id=${encodeURIComponent(catchupId)}`;

    let cancelled = false;
    openVoiceSocket(url, {
      onOpen: () => {
        if (cancelled) return;
        setActive(true);
        setConnecting(false);
      },
      onClose: () => {
        if (cancelled) return;
        navigate("/home");
      },
      onError: (err) => {
        console.warn("[feedback-voice] socket error", err);
      },
    })
      .then((handle) => {
        if (cancelled) {
          handle.close();
          return;
        }
        socketRef.current = handle;
      })
      .catch((err) => {
        console.warn("[feedback-voice] failed to open socket", err);
        setConnecting(false);
        setShowWriteFallback(true);
      });

    // 3s fallback if the socket never opens.
    window.setTimeout(() => {
      if (!cancelled && !socketRef.current) {
        setShowWriteFallback(true);
      }
    }, FALLBACK_DELAY_MS);
  };

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  const handleSkip = () => {
    socketRef.current?.close();
    navigate("/home");
  };

  return (
    <Layout className="bg-cream">
      <div className="flex-1 flex flex-col bg-cream px-6 pt-2 pb-6">
        <div className="text-meta text-coral">OR…</div>
        <h1 className="text-h1 text-navy mt-1">Tell your agent</h1>
        <p className="text-body text-slate mt-2">
          A 30-second debrief, like a friend asking how it went.
        </p>

        <div className="flex-1 flex flex-col items-center justify-center gap-6">
          <button
            type="button"
            onClick={handleStart}
            aria-label={active ? "Recording feedback" : "Start voice feedback"}
            disabled={connecting}
            className="w-28 h-28 rounded-full bg-ketchup-red flex items-center justify-center shadow-lg active:scale-95 transition-transform disabled:opacity-70"
          >
            <Mic className="w-11 h-11 text-white" strokeWidth={2} />
          </button>

          <Waveform bars={9} active={active} className="h-10" />

          <p className="text-body italic text-slate text-center max-w-[260px] leading-relaxed">
            {active
              ? "Listening… speak freely."
              : connecting
                ? "Connecting…"
                : "Tap to start. Your agent will ask a few questions."}
          </p>

          {showWriteFallback && (
            <button
              type="button"
              onClick={() => navigate("/feedback/rating")}
              className="text-body text-slate underline hover:text-navy transition-colors"
            >
              Voice not available, write it instead →
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={handleSkip}
          className="w-full h-14 rounded-btn border border-light-gray text-navy text-h3 font-medium hover:bg-light-gray/40 transition-colors"
        >
          Skip this time
        </button>
      </div>
    </Layout>
  );
};

export default FeedbackVoice;
