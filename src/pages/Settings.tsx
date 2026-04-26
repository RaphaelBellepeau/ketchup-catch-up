import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Calendar, Trash2, Unlink } from "lucide-react";
import { Layout } from "@/components/Layout";
import { Pill } from "@/components/Pill";
import { useCalendarStatus } from "@/hooks/useCalendarStatus";
import { useMemories, useDeleteMemory, type MemoryRow } from "@/hooks/useMemories";
import { cn } from "@/lib/utils";

// ── Memory grouping (same display logic as before) ──────

const SCOPE_META: Record<
  string,
  { title: string; tone: string }
> = {
  location_summary: { title: "Where you live", tone: "bg-sky" },
  weekly_summary: { title: "Your schedule", tone: "bg-mint" },
  personality_summary: { title: "Your vibe", tone: "bg-lavender" },
  experience: { title: "Past meet-ups", tone: "bg-blush" },
  preferences: { title: "What you like", tone: "bg-sunshine" },
  relationship: { title: "Group dynamics", tone: "bg-coral/40" },
  social: { title: "Group dynamics", tone: "bg-coral/40" },
  cuisine: { title: "Food", tone: "bg-blush" },
  budget: { title: "Budget", tone: "bg-mint" },
  location: { title: "Where you hang", tone: "bg-sky" },
  schedule: { title: "Schedule", tone: "bg-mint" },
};

const SCOPE_ORDER = [
  "location_summary",
  "weekly_summary",
  "personality_summary",
  "preferences",
  "experience",
  "relationship",
  "social",
  "cuisine",
  "budget",
  "location",
  "schedule",
];

const SOURCE_LABEL: Record<string, string> = {
  onboarding: "from onboarding",
  feedback: "from feedback",
  demo_seed: "demo",
  agent: "learned",
  manual: "added",
};

function metaFor(scope: string) {
  return SCOPE_META[scope] ?? { title: "Other", tone: "bg-cream-dark/40" };
}

interface Group {
  scope: string;
  title: string;
  tone: string;
  rows: MemoryRow[];
}

function groupMemories(rows: MemoryRow[]): Group[] {
  const map = new Map<string, MemoryRow[]>();
  for (const r of rows) {
    const key = r.scope || "other";
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(r);
  }
  const groups: Group[] = [];
  for (const scope of SCOPE_ORDER) {
    const list = map.get(scope);
    if (!list || !list.length) continue;
    groups.push({ scope, ...metaFor(scope), rows: list });
    map.delete(scope);
  }
  for (const [scope, list] of [...map.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    groups.push({ scope, ...metaFor(scope), rows: list });
  }
  return groups;
}

// ── Page ─────────────────────────────────────────────────

const Settings = () => {
  const navigate = useNavigate();

  const memoriesQuery = useMemories();
  const deleteMutation = useDeleteMemory();
  const {
    isConnected: calendarConnected,
    isLoading: calendarLoading,
    isConnecting: calendarConnecting,
    isDisconnecting,
    connect: connectCalendar,
    disconnect: disconnectCalendar,
  } = useCalendarStatus();

  const groups = useMemo(
    () => groupMemories(memoriesQuery.data ?? []),
    [memoriesQuery.data],
  );
  const total = memoriesQuery.data?.length ?? 0;

  const handleDisconnectCalendar = () => {
    if (
      confirm(
        "Disconnect Google Calendar? Your agent will lose access to your free/busy times until you reconnect.",
      )
    ) {
      disconnectCalendar();
    }
  };

  return (
    <Layout className="bg-cream">
      <div className="flex flex-col flex-1 px-6 pt-4 pb-8">
        <button
          type="button"
          onClick={() => navigate("/home")}
          className="self-start inline-flex items-center gap-1 text-meta text-slate hover:text-navy transition-colors"
          aria-label="Back to home"
        >
          <ArrowLeft className="w-4 h-4" /> Home
        </button>

        <p className="text-meta text-coral uppercase mt-3">Settings</p>
        <h1 className="text-h1 text-navy mt-1">Your agent</h1>

        {/* ── Connections ────────────────────────────────── */}
        <p className="text-meta text-slate uppercase mt-6">Connections</p>
        <div className="mt-3 rounded-card bg-sky p-4 flex items-center gap-3">
          <span className="w-11 h-11 rounded-full bg-white flex items-center justify-center shrink-0">
            <Calendar className="w-5 h-5 text-navy" strokeWidth={2} />
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-h3 text-navy">Google Calendar</p>
            <p className="text-body text-slate truncate">
              {calendarConnected
                ? "Reads free slots, writes accepted catch-ups."
                : "Connect to read free slots and write events."}
            </p>
          </div>
          {calendarConnected ? (
            <button
              type="button"
              onClick={handleDisconnectCalendar}
              disabled={isDisconnecting}
              className="rounded-pill bg-navy text-cream px-3 h-9 inline-flex items-center gap-1.5 text-meta uppercase tracking-wider disabled:opacity-60"
              aria-label="Disconnect Google Calendar"
            >
              <Unlink className="w-3.5 h-3.5" />
              {isDisconnecting ? "Unlinking…" : "Unlink"}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => connectCalendar()}
              disabled={calendarConnecting || calendarLoading}
              className="rounded-pill bg-coral text-white px-3 h-9 text-meta uppercase tracking-wider disabled:opacity-60"
            >
              {calendarConnecting ? "Opening…" : "Connect"}
            </button>
          )}
        </div>

        {/* ── Memory ─────────────────────────────────────── */}
        <div className="mt-7 flex items-baseline justify-between">
          <p className="text-meta text-slate uppercase">Agent memory</p>
          {total > 0 && (
            <Pill tone="sunshine">
              {total} {total === 1 ? "thing" : "things"}
            </Pill>
          )}
        </div>
        <p className="text-body text-slate mt-1">
          {memoriesQuery.isLoading
            ? "Loading…"
            : total === 0
              ? "Nothing yet — your agent will pick things up as you onboard, debrief, and chat."
              : "What your agent remembers about you. Tap the trash icon to forget."}
        </p>

        {memoriesQuery.isError && (
          <div className="mt-3 text-body text-ketchup-red">
            Couldn't load memories. Try refreshing.
          </div>
        )}

        <div className="flex flex-col gap-5 mt-4">
          {groups.map((g) => (
            <section key={g.scope}>
              <p className="text-meta text-slate uppercase mb-2">{g.title}</p>
              <div className="flex flex-col gap-2">
                {g.rows.map((m) => (
                  <div
                    key={m.id}
                    className={cn(g.tone, "rounded-card p-4 flex items-start gap-3")}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-body text-navy leading-relaxed">{m.content}</p>
                      <p className="text-meta text-navy/60 uppercase tracking-wider mt-2">
                        {SOURCE_LABEL[m.source] ?? m.source}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm("Delete this memory?")) {
                          deleteMutation.mutate(m.id);
                        }
                      }}
                      disabled={deleteMutation.isPending}
                      className="shrink-0 w-8 h-8 rounded-full bg-white/60 flex items-center justify-center text-navy/70 hover:bg-white hover:text-navy transition-colors"
                      aria-label="Delete this memory"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>

        <div className="mt-auto pt-8 text-center text-meta text-slate">
          Your agent uses these to negotiate on your behalf.
        </div>
      </div>
    </Layout>
  );
};

export default Settings;
