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
  const catchupId = state.catchupId;

  const [active, setActive] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [showWriteFallback, setShowWriteFallback] = useState(false);
  const handleRef = useRef<VoiceCallHandle | null>(null);

  const handleStart = () => {
    if (active || connecting || completed) return;
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
      catchupId,
      handlers: {
        onConnected: () => {
          if (cancelled) return;
          setActive(true);
          setConnecting(false);
        },
        onEvent: (eventType) => {
          // Backend signals when save_result fired so we can flip to a
          // confirmation state and let the user tap Done.
          if (eventType === "feedback_saved") {
            setCompleted(true);
          }
        },
        onClose: () => {
          if (cancelled) return;
          // Don't auto-route — let the user choose Done themselves.
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

  const handleDone = () => {
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
          {completed ? (
            <div className="flex flex-col items-center gap-4">
              <div className="w-24 h-24 rounded-full bg-mint flex items-center justify-center shadow-lg">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M5 12.5l4 4L19 7" stroke="#0f172a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <p className="text-h3 text-navy text-center">Thanks — saved.</p>
              <p className="text-body italic text-slate text-center max-w-[260px] leading-relaxed">
                Your agent will use this next time it negotiates for you.
              </p>
            </div>
          ) : (
            <>
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
            </>
          )}
        </div>

        {completed ? (
          <button
            type="button"
            onClick={handleDone}
            className="w-full h-14 rounded-btn bg-ketchup-red text-white text-h3 font-medium active:scale-[0.99] transition-transform"
          >
            Done
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSkip}
            className="w-full h-14 rounded-btn border border-light-gray text-navy text-h3 font-medium hover:bg-light-gray/40 transition-colors"
          >
            Skip this time
          </button>
        )}
      </div>
    </Layout>
  );
};

export default FeedbackVoice;
