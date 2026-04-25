import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Mic, X } from "lucide-react";
import { Waveform } from "@/components/Waveform";
import { openVoiceSocket, type VoiceSocketHandle } from "@/lib/voiceSocket";

const FALLBACK_DELAY_MS = 3000;

interface RouteState {
  userId?: string;
  phone?: string;
}

const VoiceCall = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as RouteState;
  const userId = state.userId ?? "demo-user";

  const [caption, setCaption] = useState("What kind of food do you usually love?");
  const [elapsed, setElapsed] = useState(0);
  const [connected, setConnected] = useState(false);
  const [showSkip, setShowSkip] = useState(false);

  const socketRef = useRef<VoiceSocketHandle | null>(null);

  // Open WS on mount.
  useEffect(() => {
    const wsBase = import.meta.env.VITE_WS_BASE_URL as string | undefined;
    let cancelled = false;

    // If no WS base configured we can't even attempt — show fallback immediately.
    if (!wsBase) {
      setShowSkip(true);
      return;
    }

    const url = `${wsBase}/ws/voice/onboarding/${encodeURIComponent(userId)}`;

    openVoiceSocket(url, {
      onOpen: () => {
        if (cancelled) return;
        setConnected(true);
      },
      onText: (text) => {
        if (cancelled) return;
        setCaption(text);
      },
      onClose: () => {
        if (cancelled) return;
        // TODO: replace with refetch(["/users/me/preferences"]) once query is wired
        console.log("[voice] WS closed → refetch /users/me/preferences");
        navigate("/onboarding/permissions", { state: { userId } });
      },
      onError: (err) => {
        console.warn("[voice] socket error", err);
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
        console.warn("[voice] failed to open socket", err);
        setShowSkip(true);
      });

    // Demo fallback: if not connected within 3s, surface skip button.
    const fallbackTimer = window.setTimeout(() => {
      if (!cancelled && !socketRef.current) {
        setShowSkip(true);
      }
    }, FALLBACK_DELAY_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(fallbackTimer);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [navigate, userId]);

  // Show fallback also if the socket attempts but never reaches OPEN.
  useEffect(() => {
    if (connected) return;
    const t = window.setTimeout(() => setShowSkip(true), FALLBACK_DELAY_MS);
    return () => window.clearTimeout(t);
  }, [connected]);

  // Call-time counter.
  useEffect(() => {
    const id = window.setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  const handleEnd = () => {
    socketRef.current?.close();
    navigate("/onboarding/permissions", { state: { userId } });
  };

  const handleSkip = () => {
    socketRef.current?.close();
    navigate("/onboarding/permissions", { state: { userId, demo: true } });
  };

  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  return (
    <div className="min-h-screen bg-cream/40">
      <div className="max-w-[420px] mx-auto min-h-screen bg-ketchup-red text-cream flex flex-col">
        {/* Status bar (cream variant for red bg) */}
        <div className="flex items-center justify-between px-6 pt-3 pb-2 text-h3">
          <span className="font-medium tabular-nums">9:42</span>
          <span className="text-cream/90 tracking-wider">• • •</span>
        </div>

        {/* Header */}
        <div className="px-6 pt-2">
          <div className="text-meta text-cream/80">
            INCOMING · {mm}:{ss}
          </div>
          <h1 className="text-h1 font-medium mt-2">ketchup agent</h1>
          <p className="text-body mt-1 text-cream/90">Calling so we can get to know you</p>
        </div>

        {/* Center: mic + waveform + caption */}
        <div className="flex-1 flex flex-col items-center justify-center px-8 gap-8">
          <div
            className="w-32 h-32 rounded-full bg-cream flex items-center justify-center shadow-lg"
            aria-label="Microphone active"
          >
            <Mic className="w-12 h-12 text-ketchup-red" strokeWidth={2} />
          </div>

          <Waveform bars={9} active className="h-12" />

          <p className="text-body italic text-cream text-center max-w-[260px] leading-relaxed">
            “{caption}”
          </p>
        </div>

        {/* Bottom controls */}
        <div className="px-8 pb-10 flex items-center justify-between">
          {/* Mute (visual only for now) */}
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
              Skip onboarding (demo mode)
            </button>
          ) : null}

          <button
            type="button"
            onClick={handleEnd}
            className="w-14 h-14 rounded-full bg-navy text-cream flex items-center justify-center"
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
