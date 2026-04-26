import { useEffect, useRef, useState } from "react";
import { Layout } from "@/components/Layout";
import { Avatar } from "@/components/Avatar";
import { cn } from "@/lib/utils";

const API = "http://127.0.0.1:8000";

// ── Message shape from the backend ───────────────────────────────────────────
interface BackendMsg {
  agent_name: string; // "raphael_agent" | "marie_agent" | "thomas_agent" | "orchestrator" | "system"
  role: string;       // "schedule" | "thinking" | "slot" | "info" | "error" | "done"
  content: string;
  data: Record<string, unknown>;
  timestamp: string;
}

// ── Map agent_name → bubble colour ───────────────────────────────────────────
const agentColor: Record<string, string> = {
  "raphaël_agent": "bg-ketchup-red text-white",
  "marie_agent":   "bg-mint text-charcoal",
  "thomas_agent":  "bg-sunshine text-charcoal",
  orchestrator:    "bg-navy text-white",
  system:          "",
};

const agentLabel: Record<string, string> = {
  "raphaël_agent": "🧑‍💻 Raphaël",
  "marie_agent":   "👩‍🎨 Marie",
  "thomas_agent":  "🧘 Thomas",
  orchestrator:    "🧠 Orchestrateur",
  system:          "",
};

const formatTimer = (s: number) => {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
};

/** Convert **bold** markdown to <strong> tags for display. */
const parseBold = (text: string) =>
  text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

// ── Single chat bubble ────────────────────────────────────────────────────────
const Bubble = ({ msg }: { msg: BackendMsg }) => {
  const key = msg.agent_name.toLowerCase();

  // System / info messages → centred italic
  if (msg.agent_name === "system") {
    if (msg.role === "done") return null;
    return (
      <div className="w-full text-center my-1 animate-fade-in">
        <span className="text-body italic text-slate"
          dangerouslySetInnerHTML={{ __html: parseBold(msg.content) }} />
      </div>
    );
  }

  const isOrchestrator = msg.agent_name === "orchestrator";
  const colorClass = agentColor[key] ?? "bg-light-gray text-charcoal";
  const label = agentLabel[key] ?? msg.agent_name;

  // Orchestrator slot result → highlight card
  if (msg.role === "slot") {
    return (
      <div className="w-full animate-fade-in">
        <div className="bg-navy text-white rounded-card px-4 py-3 border-2 border-ketchup-red">
          <div className="text-[10px] font-semibold opacity-70 mb-1">{label}</div>
          <div className="text-body whitespace-pre-wrap"
            dangerouslySetInnerHTML={{ __html: parseBold(msg.content) }} />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex w-full animate-fade-in",
        isOrchestrator ? "justify-center" : "justify-start",
      )}
    >
      <div className={cn("max-w-[85%] px-4 py-3 rounded-card", colorClass)}>
        <div className="text-[10px] font-semibold opacity-70 mb-0.5">{label}</div>
        <div className="text-body whitespace-pre-wrap"
          dangerouslySetInnerHTML={{ __html: parseBold(msg.content) }} />
      </div>
    </div>
  );
};

// ── Page ─────────────────────────────────────────────────────────────────────
const Negotiating = () => {
  const [messages, setMessages] = useState<BackendMsg[]>([]);
  const [progress, setProgress] = useState(0);
  const [seconds, setSeconds] = useState(0);
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Count-up timer
  useEffect(() => {
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // Auto-scroll on new message
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // 1. POST /demo/negotiate  →  2. listen to SSE /demo/negotiate/stream
  useEffect(() => {
    let es: EventSource | null = null;
    let cancelled = false;

    const run = async () => {
      try {
        setStatus("running");

        // Kick off the negotiation on the backend
        await fetch(`${API}/demo/negotiate`, { method: "POST" });

        if (cancelled) return;

        // Open SSE stream
        es = new EventSource(`${API}/demo/negotiate/stream`);
        let msgCount = 0;
        const TOTAL_EXPECTED = 8; // ~8 events for Phase 1

        es.onmessage = (evt) => {
          if (cancelled) return;
          try {
            const msg: BackendMsg = JSON.parse(evt.data);

            setMessages((prev) => [...prev, msg]);
            msgCount++;
            setProgress(Math.min(Math.round((msgCount / TOTAL_EXPECTED) * 100), 95));

            if (msg.role === "done") {
              setProgress(100);
              setStatus("done");
              es?.close();
            }
          } catch {
            // ignore malformed events
          }
        };

        es.onerror = () => {
          if (!cancelled) setStatus("error");
          es?.close();
        };
      } catch (err) {
        if (!cancelled) setStatus("error");
        console.error("[negotiating]", err);
      }
    };

    run();

    return () => {
      cancelled = true;
      es?.close();
    };
  }, []);

  const members = [
    { initials: "RA", color: "ketchup-red", label: "Raphaël" },
    { initials: "MA", color: "mint",        label: "Marie"   },
    { initials: "TH", color: "sunshine",    label: "Thomas"  },
  ];

  return (
    <Layout className="bg-cream">
      <div className="flex-1 flex flex-col bg-cream px-6 pt-2 pb-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-pill bg-ketchup-red animate-pulse" />
            <span className="text-meta text-ketchup-red">
              {status === "done" ? "NÉGOCIATION TERMINÉE" : "NÉGOCIATION · LIVE"}
            </span>
          </div>
          <span className="text-body text-slate tabular-nums">{formatTimer(seconds)}</span>
        </div>

        <h1 className="text-h1 text-navy mt-3">3 agents négocient</h1>

        {/* Avatars */}
        <div className="mt-4 flex items-center gap-3">
          <div className="flex -space-x-1">
            {members.map((m) => (
              <Avatar
                key={m.initials}
                initials={m.initials}
                color={m.color}
                className={cn(
                  "ring-2 ring-cream",
                  m.color === "ketchup-red" && "text-white",
                )}
              />
            ))}
          </div>
          <span className="text-body text-slate">
            {members.map((m) => m.label).join(" · ")}
          </span>
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          className="flex-1 mt-5 -mx-2 px-2 overflow-y-auto flex flex-col gap-3"
        >
          {messages.length === 0 && status === "running" && (
            <div className="text-center text-body italic text-slate mt-8 animate-pulse">
              Connexion aux agents…
            </div>
          )}
          {messages.map((m, i) => (
            <Bubble key={i} msg={m} />
          ))}
          {status === "error" && (
            <div className="text-center text-body text-ketchup-red mt-4">
              ❌ Erreur de connexion au backend. Le serveur est-il démarré ?
            </div>
          )}
        </div>

        {/* Progress bar */}
        <div className="mt-4">
          <div className="h-1.5 w-full rounded-pill bg-light-gray overflow-hidden">
            <div
              className="h-full bg-ketchup-red transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-2 text-center text-body text-slate">
            {status === "done"
              ? "✅ Créneau trouvé par Gemini"
              : status === "error"
              ? "Erreur — vérifier le backend"
              : "Gemini analyse les agendas…"}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Negotiating;
