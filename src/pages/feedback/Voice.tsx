import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Mic } from "lucide-react";
import { Layout } from "@/components/Layout";
import { Waveform } from "@/components/Waveform";
import { useProfile } from "@/hooks/useProfile";
import { openVoiceCall, type VoiceCallHandle } from "@/lib/voiceClient";

const FALLBACK_DELAY_MS = 4000;

interface RouteState {
  catchupId?: string;
}

const FeedbackVoice = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { session, profile } = useProfile();
  const state = (location.state ?? {}) as RouteState;
  void state.catchupId; // reserved for when the WS supports a catchup_id query param

  const [active, setActive] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [showWriteFallback, setShowWriteFallback] = useState(false);
  const handleRef = useRef<VoiceCallHandle | null>(null);

  const handleStart = () => {
    if (active || connecting) return;
    const userId = session?.user.id ?? profile?.id;
    if (!userId) {
      setShowWriteFallback(true);
      return;
    }

    setConnecting(true);
    const cancelled = false;

    openVoiceCall({
      taskType: "feedback",
      userId,
      handlers: {
        onConnected: () => {
          if (cancelled) return;
          setActive(true);
          setConnecting(false);
        },
        onClose: () => {
          if (cancelled) return;
          navigate("/home");
        },
        onError: (err) => {
           
          console.warn("[feedback-voice] error", err);
          setConnecting(false);
        },
      },
    })
      .then((h) => {
        if (cancelled) {
          h.close();
          return;
        }
        handleRef.current = h;
      })
      .catch((err) => {
         
        console.warn("[feedback-voice] failed to open", err);
        setConnecting(false);
        setShowWriteFallback(true);
      });

    window.setTimeout(() => {
      if (!cancelled && !handleRef.current) {
        setShowWriteFallback(true);
      }
    }, FALLBACK_DELAY_MS);
  };

  useEffect(() => {
    return () => {
      handleRef.current?.close();
      handleRef.current = null;
    };
  }, []);

  const handleSkip = () => {
    handleRef.current?.close();
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
