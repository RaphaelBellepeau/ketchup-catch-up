import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { addDays, format } from "date-fns";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import { useGroups } from "@/hooks/useGroups";
import { useGroupCreation } from "@/store/groupCreation";
import { cn } from "@/lib/utils";

type Period = "day" | "week" | "month" | "year";
type Rate = 1 | 2 | 3 | 4;
type Vibe = "dinner" | "drinks" | "brunch" | "activity";

const PERIODS: { id: Period; label: string }[] = [
  { id: "day", label: "Days" },
  { id: "week", label: "Weeks" },
  { id: "month", label: "Months" },
  { id: "year", label: "Year" },
];

const RATES: Rate[] = [1, 2, 3, 4];

const VIBES: { id: Vibe; label: string; emoji: string }[] = [
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

function periodNoun(period: Period): string {
  return { day: "day", week: "week", month: "month", year: "year" }[period];
}

const Recurring = () => {
  const navigate = useNavigate();
  // Existing-group flow: groupId comes from the URL (Home → Recurring).
  // New-group flow: groupId is undefined, we read selected friends + name
  // from the zustand store and create the group on submit.
  const { groupId: groupIdFromUrl } = useParams<{ groupId: string }>();
  const isNewGroupFlow = !groupIdFromUrl;

  const groupsQuery = useGroups();
  const groupFromHome = (groupsQuery.data ?? []).find((g) => g.id === groupIdFromUrl);

  const creation = useGroupCreation();
  const storeVibe = creation.vibe;

  const [period, setPeriod] = useState<Period>("week");
  const [rate, setRate] = useState<Rate>(1);
  const [vibe, setVibe] = useState<Vibe>(storeVibe);
  const [submitting, setSubmitting] = useState(false);

  const window = useMemo(() => {
    const today = new Date();
    return {
      from: format(today, "yyyy-MM-dd"),
      until: format(addDays(today, 30), "yyyy-MM-dd"),
    };
  }, []);

  const hasFriendsForNewGroup =
    !isNewGroupFlow || creation.selectedFriendIds.length > 0;
  const launchDisabled =
    submitting || (isNewGroupFlow ? !hasFriendsForNewGroup : !groupIdFromUrl);

  const handleLaunch = async () => {
    if (launchDisabled) return;
    setSubmitting(true);
    try {
      let targetGroupId = groupIdFromUrl ?? "";

      if (isNewGroupFlow) {
        const group = await api<CreatedGroup>("/groups", {
          method: "POST",
          json: {
            name: creation.name.trim() || "New group",
            member_ids: creation.selectedFriendIds,
          },
        });
        targetGroupId = group.id;
      }

      const catchup = await api<CreatedCatchup>("/catchups", {
        method: "POST",
        json: {
          group_id: targetGroupId,
          type: "recurring",
          time_window: `${window.from}|${window.until}`,
          vibe,
        },
      });

      api(`/catchups/${catchup.id}/negotiate`, { method: "POST" }).catch(
        (err) => console.warn("[recurring] negotiate kick-off failed", err),
      );

      navigate("/catchup/negotiating", { state: { catchupId: catchup.id } });
    } catch (err) {
      console.warn("[recurring] launch failed", err);
      const message = err instanceof Error ? err.message : "Could not launch agents";
      toast({ title: "Couldn't start", description: message, variant: "destructive" });
      setSubmitting(false);
    }
  };

  const cadenceLabel = `${rate}× per ${periodNoun(period)}`;
  const heading = isNewGroupFlow
    ? `Lock a rhythm with ${creation.name.trim() || "your crew"}`
    : groupFromHome?.name
      ? `Lock a rhythm with ${groupFromHome.name}`
      : "Lock a rhythm";

  return (
    <Layout className="bg-cream">
      <div className="flex-1 flex flex-col px-6 pt-4 pb-6">
        <button
          type="button"
          onClick={() => navigate(isNewGroupFlow ? "/groups/new/frequency" : "/home")}
          className="text-meta text-slate uppercase tracking-wider w-fit"
        >
          ← {isNewGroupFlow ? "Back" : "Home"}
        </button>

        <div className="text-meta text-coral uppercase mt-3">
          {isNewGroupFlow ? "New group · 4 of 4" : "Recurring catch-up"}
        </div>
        <h1 className="text-h1 text-navy mt-2">{heading}</h1>
        <p className="text-body text-slate mt-2">
          Pick a cadence — your agent does the rest.
        </p>

        <div className="mt-6 text-meta text-slate uppercase">Per</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {PERIODS.map((p) => {
            const active = period === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => setPeriod(p.id)}
                className={cn(
                  "rounded-pill px-4 h-10 text-body border inline-flex items-center",
                  active
                    ? "bg-navy border-navy text-cream"
                    : "bg-white border-light-gray text-navy",
                )}
              >
                {p.label}
              </button>
            );
          })}
        </div>

        <div className="mt-5 text-meta text-slate uppercase">How many times</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {RATES.map((r) => {
            const active = rate === r;
            return (
              <button
                key={r}
                type="button"
                onClick={() => setRate(r)}
                className={cn(
                  "rounded-pill px-5 h-10 text-body border inline-flex items-center font-semibold",
                  active
                    ? "bg-ketchup-red border-ketchup-red text-white"
                    : "bg-white border-light-gray text-navy",
                )}
              >
                {r}×
              </button>
            );
          })}
        </div>

        <p className="mt-3 text-body text-slate">
          That's <span className="text-navy font-semibold">{cadenceLabel}</span>.
        </p>

        <div className="mt-6 border-t border-light-gray pt-4">
          <div className="text-meta text-slate uppercase">What kind of moment</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {VIBES.map((v) => {
              const active = vibe === v.id;
              return (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => {
                    setVibe(v.id);
                    if (isNewGroupFlow) creation.setVibe(v.id);
                  }}
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

        {isNewGroupFlow && !hasFriendsForNewGroup && (
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

export default Recurring;
