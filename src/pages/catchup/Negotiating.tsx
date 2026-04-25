import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Avatar } from "@/components/Avatar";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  negotiationMessages,
  type NegotiationMessage,
  type NegotiationSender,
} from "@/data/mockData";

const USE_REAL = import.meta.env.VITE_USE_REAL_API === "true";
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const MAX_RETRIES = 3;

const senderLabel: Record<NegotiationSender, string> = {
  you: "You",
  marie: "Marie",
  tom: "Tom · via phone",
  system: "",
};

const formatTimer = (s: number) => {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
};

const Bubble = ({ msg }: { msg: NegotiationMessage }) => {
  if (msg.sender === "system") {
    return (
      <div className="w-full text-center my-1 animate-fade-in">
        <span className="text-body italic text-slate">{msg.content}</span>
      </div>
    );
  }

  const isYou = msg.sender === "you";
  const isMarie = msg.sender === "marie";
  const isTom = msg.sender === "tom";

  return (
    <div
      className={cn(
        "flex w-full animate-fade-in",
        isYou ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[80%] px-4 py-3 rounded-card",
          isYou && "bg-ketchup-red text-white rounded-br-[5px]",
          isMarie && "bg-mint text-charcoal",
          isTom && "bg-sunshine text-charcoal",
        )}
      >
        <div
          className={cn(
            "text-[10px] font-medium opacity-70 mb-0.5",
            isTom && "italic",
          )}
        >
          {senderLabel[msg.sender]}
        </div>
        <div className="text-body">{msg.content}</div>
      </div>
    </div>
  );
};

const Negotiating = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const catchupId = (location.state as { catchupId?: string } | null)?.catchupId ?? "demo";

  const [messages, setMessages] = useState<NegotiationMessage[]>([]);
  const [progress, setProgress] = useState(0);
  const [tavilyCaption, setTavilyCaption] = useState("Tavily · gathering options…");
  const [seconds, setSeconds] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Timer count-up
  useEffect(() => {
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // Auto-scroll on new message
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // Mock mode driver
  useEffect(() => {
    if (USE_REAL) return;
    let cancelled = false;
    const timeouts: number[] = [];
    let acc = 0;

    negotiationMessages.forEach((m, i) => {
      acc += m.delay_ms;
      const id = window.setTimeout(() => {
        if (cancelled) return;
        setMessages((prev) => [...prev, m]);
        setProgress(Math.round(((i + 1) / negotiationMessages.length) * 100));
        if (m.content.toLowerCase().includes("places found")) {
          setTavilyCaption(m.content);
        }
      }, acc);
      timeouts.push(id);
    });

    const doneId = window.setTimeout(() => {
      if (!cancelled) navigate("/catchup/proposal", { state: { catchupId } });
    }, acc + 1200);
    timeouts.push(doneId);

    return () => {
      cancelled = true;
      timeouts.forEach(clearTimeout);
    };
  }, [navigate, catchupId]);

  // Real mode driver (SSE with backoff)
  useEffect(() => {
    if (!USE_REAL) return;
    let retries = 0;
    let es: EventSource | null = null;
    let reconnectTimer: number | null = null;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      const url = `${API_BASE}/catchups/${catchupId}/negotiate/stream`;
      es = new EventSource(url);

      es.onmessage = (evt) => {
        try {
          const payload = JSON.parse(evt.data);
          switch (payload.type) {
            case "message":
              setMessages((prev) => [...prev, payload.data as NegotiationMessage]);
              break;
            case "progress":
              setProgress(Number(payload.data?.value ?? 0));
              break;
            case "venue_search":
              setTavilyCaption(`Tavily · ${payload.data?.caption ?? "searching…"}`);
              break;
            case "done":
              es?.close();
              navigate("/catchup/proposal", { state: { catchupId } });
              break;
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
          toast({ title: "Connection lost", description: "Please try again." });
          return;
        }
        retries += 1;
        toast({ title: "Connection issue, retrying…" });
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

  return (
    <Layout className="bg-cream">
      <div className="flex-1 flex flex-col bg-cream px-6 pt-2 pb-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-pill bg-ketchup-red animate-pulse" />
            <span className="text-meta text-ketchup-red">NEGOTIATING · LIVE</span>
          </div>
          <span className="text-body text-slate tabular-nums">{formatTimer(seconds)}</span>
        </div>

        <h1 className="text-h1 text-navy mt-3">3 agents talking</h1>

        {/* Avatars row */}
        <div className="mt-4 flex items-center gap-3">
          <div className="flex -space-x-1">
            <Avatar initials="YO" color="ketchup-red" className="text-white ring-2 ring-cream" />
            <Avatar initials="MA" color="mint" className="ring-2 ring-cream" />
            <Avatar initials="TO" color="sunshine" className="ring-2 ring-cream" />
          </div>
          <span className="text-body text-slate">you · Marie · Tom</span>
        </div>

        {/* Bubbles */}
        <div
          ref={scrollRef}
          className="flex-1 mt-5 -mx-2 px-2 overflow-y-auto flex flex-col gap-3"
        >
          {messages.map((m) => (
            <Bubble key={m.id} msg={m} />
          ))}
        </div>

        {/* Progress + caption */}
        <div className="mt-4">
          <div className="h-1.5 w-full rounded-pill bg-light-gray overflow-hidden">
            <div
              className="h-full bg-ketchup-red transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-2 text-center text-body text-slate">{tavilyCaption}</div>
        </div>
      </div>
    </Layout>
  );
};

export default Negotiating;
