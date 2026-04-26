import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Avatar } from "@/components/Avatar";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";
const MAX_RETRIES = 3;

interface NegotiationMessage {
  agent_name: string;
  role: string;
  content: string;
  data?: Record<string, unknown>;
  timestamp?: string;
}

const formatTimer = (s: number) => {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
};

const AVATAR_COLORS = ["mint", "sunshine", "lavender", "sky", "coral"];
function colorFor(key: string): string {
  let hash = 0;
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) | 0;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function isSystemMsg(role: string): boolean {
  return role === "info" || role === "done" || role === "error";
}
function isOrchestrator(name: string): boolean {
  return name === "orchestrator" || name === "system";
}

const Bubble = ({ msg }: { msg: NegotiationMessage }) => {
  if (isOrchestrator(msg.agent_name) && isSystemMsg(msg.role)) {
    return (
      <div className="w-full text-center my-1 animate-fade-in">
        <span
          className={cn(
            "text-body italic",
            msg.role === "error" ? "text-ketchup-red" : "text-slate",
          )}
        >
          {msg.content}
        </span>
      </div>
    );
  }

  // Agent bubble (someone else's agent — left aligned, color-keyed by name).
  const color = colorFor(msg.agent_name);
  const initials = msg.agent_name.slice(0, 2).toUpperCase();
  return (
    <div className="flex w-full animate-fade-in justify-start">
      <div className="flex items-end gap-2 max-w-[85%]">
        <Avatar initials={initials} color={color} size="sm" />
        <div className={cn("px-4 py-3 rounded-card bg-cream-dark/30 text-charcoal")}>
          <div className="text-[10px] font-medium opacity-70 mb-0.5 capitalize">
            {msg.agent_name}
          </div>
          <div className="text-body">{msg.content}</div>
        </div>
      </div>
    </div>
  );
};

const Negotiating = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const catchupId = (location.state as { catchupId?: string } | null)?.catchupId;

  const [messages, setMessages] = useState<NegotiationMessage[]>([]);
  const [progress, setProgress] = useState(0);
  const [seconds, setSeconds] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Heuristic progress: bumps with every message, capped at 95% until done.
  useEffect(() => {
    setProgress(Math.min(95, messages.length * 8));
  }, [messages.length]);

  useEffect(() => {
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  useEffect(() => {
    if (!catchupId) {
      navigate("/home", { replace: true });
      return;
    }
    let cancelled = false;
    let retries = 0;
    let es: EventSource | null = null;
    let reconnectTimer: number | null = null;

    const connect = () => {
      if (cancelled) return;
      const url = `${API_BASE}/catchups/${encodeURIComponent(catchupId)}/negotiate/stream`;
      es = new EventSource(url);

      es.onmessage = (evt) => {
        try {
          const payload = JSON.parse(evt.data) as {
            type: string;
            data?: NegotiationMessage;
          };
          if (payload.type === "message" && payload.data) {
            setMessages((prev) => [...prev, payload.data!]);
            if (payload.data.role === "done") {
              setProgress(100);
              es?.close();
              window.setTimeout(() => {
                if (!cancelled) navigate("/catchup/proposal", { state: { catchupId } });
              }, 800);
            }
          } else if (payload.type === "done") {
            setProgress(100);
            es?.close();
            window.setTimeout(() => {
              if (!cancelled) navigate("/catchup/proposal", { state: { catchupId } });
            }, 600);
          }
          retries = 0;
        } catch (e) {
          console.warn("[negotiating] bad SSE payload", e);
        }
      };

      es.onerror = () => {
        es?.close();
        if (cancelled) return;
        if (retries >= MAX_RETRIES) {
          toast({
            title: "Connection lost",
            description: "Couldn't reconnect to the agent feed.",
            variant: "destructive",
          });
          return;
        }
        retries += 1;
        const backoff = Math.min(1000 * 2 ** retries, 8000);
        reconnectTimer = window.setTimeout(connect, backoff);
      };
    };

    connect();

    return () => {
      cancelled = true;
      es?.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [navigate, catchupId]);

  const lastInfoCaption = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (isOrchestrator(m.agent_name) && m.role === "info") return m.content;
    }
    return "Connecting agents…";
  }, [messages]);

  const distinctAgents = useMemo(() => {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const m of messages) {
      if (isOrchestrator(m.agent_name)) continue;
      if (seen.has(m.agent_name)) continue;
      seen.add(m.agent_name);
      out.push(m.agent_name);
    }
    return out;
  }, [messages]);

  return (
    <Layout className="bg-cream">
      <div className="flex-1 flex flex-col bg-cream px-6 pt-2 pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-pill bg-ketchup-red animate-pulse" />
            <span className="text-meta text-ketchup-red">NEGOTIATING · LIVE</span>
          </div>
          <span className="text-body text-slate tabular-nums">{formatTimer(seconds)}</span>
        </div>

        <h1 className="text-h1 text-navy mt-3">
          {distinctAgents.length > 0
            ? `${distinctAgents.length + 1} agents talking`
            : "Agents getting started…"}
        </h1>

        {distinctAgents.length > 0 && (
          <div className="mt-4 flex items-center gap-3">
            <div className="flex -space-x-1">
              {distinctAgents.slice(0, 4).map((n) => (
                <Avatar
                  key={n}
                  initials={n.slice(0, 2).toUpperCase()}
                  color={colorFor(n)}
                  className="ring-2 ring-cream"
                />
              ))}
            </div>
            <span className="text-body text-slate truncate">
              {distinctAgents.map((n) => n.split("'")[0]).join(" · ")}
            </span>
          </div>
        )}

        <div
          ref={scrollRef}
          className="flex-1 mt-5 -mx-2 px-2 overflow-y-auto flex flex-col gap-3"
        >
          {messages.map((m, i) => (
            <Bubble key={i} msg={m} />
          ))}
        </div>

        <div className="mt-4">
          <div className="h-1.5 w-full rounded-pill bg-light-gray overflow-hidden">
            <div
              className="h-full bg-ketchup-red transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-2 text-center text-body text-slate">{lastInfoCaption}</div>
        </div>
      </div>
    </Layout>
  );
};

export default Negotiating;
