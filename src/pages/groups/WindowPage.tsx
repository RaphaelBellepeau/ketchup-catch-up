import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { format, differenceInCalendarDays } from "date-fns";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { Calendar } from "@/components/ui/calendar";
import { useGroupCreation, type Vibe } from "@/store/groupCreation";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const vibes: { id: Vibe; label: string; emoji: string }[] = [
  { id: "dinner", label: "Dinner", emoji: "🍽️" },
  { id: "drinks", label: "Drinks", emoji: "🍷" },
  { id: "brunch", label: "Brunch", emoji: "🥐" },
  { id: "activity", label: "Activity", emoji: "🎳" },
];

interface CreatedGroup {
  id: string;
}
interface CreatedCatchup {
  id: string;
  status: string;
}

function formatDate(d: Date | null): string {
  return d ? format(d, "EEE d MMM") : "—";
}

const WindowPage = () => {
  const navigate = useNavigate();
  const state = useGroupCreation();
  const [submitting, setSubmitting] = useState(false);

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
  const hasFriends = state.selectedFriendIds.length > 0;

  const handleLaunch = async () => {
    if (!hasValidRange || !hasFriends || submitting) return;
    setSubmitting(true);
    try {
      // 1. Create the group with the selected friends as members.
      const group = await api<CreatedGroup>("/groups", {
        method: "POST",
        json: {
          name: state.name.trim() || "New group",
          member_ids: state.selectedFriendIds,
        },
      });

      // 2. Create the catchup attached to the group.
      // We send YYYY-MM-DD (date-only) instead of a full ISO datetime so
      // the backend reasons about calendar DAYS, not absolute moments.
      // Going through .toISOString() shifted "12 May 00:00 Paris" to
      // "11 May 22:00 UTC" → the calendar view rendered 11 May. Date
      // strings are timezone-free.
      const fromYmd = format(state.fromDate!, "yyyy-MM-dd");
      const untilYmd = format(state.untilDate!, "yyyy-MM-dd");
      const catchup = await api<CreatedCatchup>("/catchups", {
        method: "POST",
        json: {
          group_id: group.id,
          type: state.frequency === "recurring" ? "recurring" : "one_shot",
          time_window: `${fromYmd}|${untilYmd}`,
          vibe: state.vibe,
        },
      });

      // 3. Kick off the agent negotiation. Fire-and-forget — the SSE on
      //    the next screen will pick up live messages.
      api(`/catchups/${catchup.id}/negotiate`, { method: "POST" }).catch((err) => {
        console.warn("[group] negotiate kick-off failed", err);
      });

      navigate("/catchup/negotiating", { state: { catchupId: catchup.id } });
    } catch (err) {
      console.warn("[group] launch failed", err);
      const message = err instanceof Error ? err.message : "Could not launch agents";
      toast({ title: "Couldn't start", description: message, variant: "destructive" });
      setSubmitting(false);
    }
  };

  const launchDisabled = !hasValidRange || !hasFriends || submitting;

  return (
    <Layout>
      <div className="flex-1 flex flex-col px-6 pt-4 pb-6">
        <div className="text-meta text-slate">NEW GROUP · 4 OF 4</div>
        <h1 className="text-h1 text-navy mt-2">When do you want to meet?</h1>
        <p className="text-body text-slate mt-2">
          Tap a start day, then an end day. Your agent will negotiate inside this window.
        </p>

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

        <div className="mt-3 rounded-card bg-white border border-light-gray flex justify-center">
          <Calendar
            mode="range"
            selected={range}
            onSelect={(r) => state.setWindow(r?.from ?? null, r?.to ?? null)}
            numberOfMonths={1}
            disabled={{ before: today }}
            weekStartsOn={1}
          />
        </div>

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

        {!hasFriends && (
          <p className="mt-3 text-meta text-coral">
            Add at least one friend before launching the agents.
          </p>
        )}

        <div className="flex-1" />

        <Button
          variant="primary"
          size="lg"
          fullWidth
          onClick={handleLaunch}
          disabled={launchDisabled}
        >
          {submitting ? "Launching agents…" : "Launch my agent"}
        </Button>
      </div>
    </Layout>
  );
};

export default WindowPage;
