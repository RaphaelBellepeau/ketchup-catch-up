import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { format, differenceInCalendarDays } from "date-fns";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { Calendar } from "@/components/ui/calendar";
import { useGroupCreation, type Vibe } from "@/store/groupCreation";
import { cn } from "@/lib/utils";

const vibes: { id: Vibe; label: string; emoji: string }[] = [
  { id: "dinner", label: "Dinner", emoji: "🍽️" },
  { id: "drinks", label: "Drinks", emoji: "🍷" },
  { id: "brunch", label: "Brunch", emoji: "🥐" },
  { id: "activity", label: "Activity", emoji: "🎳" },
];

// Mock submission — pretends to POST and returns a fake catchup id.
// TODO: will POST /catchups + POST /catchups/:id/negotiate on phase 6
const launchAgent = async (payload: unknown): Promise<{ catchup_id: string }> => {
  console.log("[group] launchAgent payload", payload);
  await new Promise((r) => setTimeout(r, 300));
  return { catchup_id: `catchup-${Math.random().toString(36).slice(2, 8)}` };
};

function formatDate(d: Date | null): string {
  return d ? format(d, "EEE d MMM") : "—";
}

const WindowPage = () => {
  const navigate = useNavigate();
  const state = useGroupCreation();

  const today = useMemo(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }, []);

  const range = useMemo(
    () => ({
      from: state.fromDate ?? undefined,
      to: state.untilDate ?? undefined,
    }),
    [state.fromDate, state.untilDate],
  );

  const dayCount =
    state.fromDate && state.untilDate
      ? differenceInCalendarDays(state.untilDate, state.fromDate) + 1
      : 0;

  const hasValidRange = Boolean(state.fromDate && state.untilDate);

  const handleLaunch = async () => {
    if (!hasValidRange) return;
    const { catchup_id } = await launchAgent({
      name: state.name,
      friends: state.selectedFriendIds,
      frequency: state.frequency,
      from: state.fromDate?.toISOString(),
      until: state.untilDate?.toISOString(),
      vibe: state.vibe,
    });
    navigate("/catchup/negotiating", { state: { catchupId: catchup_id } });
  };

  return (
    <Layout>
      <div className="flex-1 flex flex-col px-6 pt-4 pb-6">
        <div className="text-meta text-slate">NEW GROUP · 4 OF 4</div>
        <h1 className="text-h1 text-navy mt-2">When do you want to meet?</h1>
        <p className="text-body text-slate mt-2">
          Tap a start day, then an end day. Your agent will negotiate inside this window.
        </p>

        {/* Selected range summary */}
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-card bg-mint p-4">
            <div className="text-meta text-navy/70">From</div>
            <div className="text-h2 text-navy mt-1">{formatDate(state.fromDate)}</div>
          </div>
          <div className="rounded-card bg-blush p-4">
            <div className="text-meta text-navy/70">Until</div>
            <div className="text-h2 text-navy mt-1">{formatDate(state.untilDate)}</div>
          </div>
        </div>
        {hasValidRange && (
          <div className="mt-2 text-meta text-slate">
            {dayCount} {dayCount === 1 ? "day" : "days"} window
          </div>
        )}

        {/* Inline calendar */}
        <div className="mt-3 rounded-card bg-white border border-light-gray flex justify-center">
          <Calendar
            mode="range"
            selected={range}
            onSelect={(r) =>
              state.setWindow(r?.from ?? null, r?.to ?? null)
            }
            numberOfMonths={1}
            disabled={{ before: today }}
            weekStartsOn={1}
          />
        </div>

        {/* Vibe */}
        <div className="mt-5 border-t border-light-gray pt-4">
          <div className="text-meta text-slate">WHAT KIND OF MOMENT</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {vibes.map((v) => {
              const active = state.vibe === v.id;
              return (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => state.setVibe(v.id)}
                  className={cn(
                    "rounded-pill px-4 h-10 text-body border inline-flex items-center gap-1.5",
                    active
                      ? "bg-ketchup-red border-ketchup-red text-white"
                      : "bg-white border-light-gray text-navy",
                  )}
                >
                  <span aria-hidden="true">{v.emoji}</span>
                  {v.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex-1" />

        <Button
          variant="primary"
          size="lg"
          fullWidth
          onClick={handleLaunch}
          disabled={!hasValidRange}
        >
          Launch my agent
        </Button>
      </div>
    </Layout>
  );
};

export default WindowPage;
