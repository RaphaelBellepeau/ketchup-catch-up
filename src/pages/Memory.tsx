import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Trash2 } from "lucide-react";
import { Layout } from "@/components/Layout";
import { useMemories, useDeleteMemory, type MemoryRow } from "@/hooks/useMemories";
import { cn } from "@/lib/utils";

// Friendlier titles and a stable color per scope. Anything we haven't
// explicitly mapped lands in "Other" with a neutral color.
const SCOPE_META: Record<
  string,
  { title: string; tone: string }
> = {
  location_summary: { title: "Where you live", tone: "bg-sky" },
  weekly_summary: { title: "Your schedule", tone: "bg-mint" },
  personality_summary: { title: "Your vibe", tone: "bg-lavender" },
  experience: { title: "Past meet-ups", tone: "bg-blush" },
  preferences: { title: "What you like", tone: "bg-sunshine" },
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
  // Known scopes first, in a stable display order.
  for (const scope of SCOPE_ORDER) {
    const list = map.get(scope);
    if (!list || !list.length) continue;
    const meta = metaFor(scope);
    groups.push({ scope, ...meta, rows: list });
    map.delete(scope);
  }
  // Remaining unknown scopes alphabetically.
  for (const [scope, list] of [...map.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    const meta = metaFor(scope);
    groups.push({ scope, ...meta, rows: list });
  }
  return groups;
}

const Memory = () => {
  const navigate = useNavigate();
  const memoriesQuery = useMemories();
  const deleteMutation = useDeleteMemory();

  const groups = useMemo(
    () => groupMemories(memoriesQuery.data ?? []),
    [memoriesQuery.data],
  );

  const total = memoriesQuery.data?.length ?? 0;

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

        <p className="text-meta text-coral uppercase mt-3">What I've learned</p>
        <h1 className="text-h1 text-navy mt-1">Your agent's memory</h1>
        <p className="text-body text-slate mt-2">
          {memoriesQuery.isLoading
            ? "Loading…"
            : total === 0
              ? "Nothing yet — your agent will pick things up as you onboard, debrief, and chat."
              : `${total} ${total === 1 ? "thing" : "things"} your agent remembers about you.`}
        </p>

        {memoriesQuery.isError && (
          <div className="mt-4 text-body text-ketchup-red">
            Couldn't load memories. Try refreshing.
          </div>
        )}

        <div className="flex flex-col gap-5 mt-6">
          {groups.map((g) => (
            <section key={g.scope}>
              <p className="text-meta text-slate uppercase mb-2">{g.title}</p>
              <div className="flex flex-col gap-2">
                {g.rows.map((m) => (
                  <div
                    key={m.id}
                    className={cn(
                      g.tone,
                      "rounded-card p-4 flex items-start gap-3",
                    )}
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

export default Memory;
