import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
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

const WindowPage = () => {
  const navigate = useNavigate();
  const state = useGroupCreation();

  const handleLaunch = async () => {
    const { catchup_id } = await launchAgent({
      name: state.name,
      friends: state.selectedFriendIds,
      frequency: state.frequency,
      from: state.fromDate,
      until: state.untilDate,
      vibe: state.vibe,
    });
    navigate("/catchup/negotiating", { state: { catchupId: catchup_id } });
  };

  return (
    <Layout>
      <div className="flex-1 flex flex-col px-6 pt-4 pb-6">
        <div className="text-meta text-slate">WHEN & WHAT</div>
        <h1 className="text-h1 text-navy mt-2">In the next 2 weeks</h1>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-card bg-mint p-4">
            <div className="text-meta text-navy/70">From</div>
            <div className="text-h2 text-navy mt-1">{state.fromDate}</div>
          </div>
          <div className="rounded-card bg-blush p-4">
            <div className="text-meta text-navy/70">Until</div>
            <div className="text-h2 text-navy mt-1">{state.untilDate}</div>
          </div>
        </div>

        <div className="mt-6 border-t border-light-gray pt-4">
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

        <Button variant="primary" size="lg" fullWidth onClick={handleLaunch}>
          Launch my agent
        </Button>
      </div>
    </Layout>
  );
};

export default WindowPage;
