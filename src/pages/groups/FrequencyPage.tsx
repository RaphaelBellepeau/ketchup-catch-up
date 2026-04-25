import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { Pill } from "@/components/Pill";
import { useGroupCreation, type Frequency } from "@/store/groupCreation";
import { cn } from "@/lib/utils";

const options: { id: Frequency; title: string; subtitle: string }[] = [
  {
    id: "one-shot",
    title: "One-shot catch-up",
    subtitle: "Set a window. The agents arrange it once.",
  },
  {
    id: "recurring",
    title: "Recurring",
    subtitle: "Every 2 weeks, a fresh plan with the same crew.",
  },
];

const FrequencyPage = () => {
  const navigate = useNavigate();
  const frequency = useGroupCreation((s) => s.frequency);
  const setFrequency = useGroupCreation((s) => s.setFrequency);

  return (
    <Layout className="bg-cream">
      <div className="flex-1 flex flex-col px-6 pt-4 pb-6">
        <div className="text-meta text-slate">NEW GROUP · 3 OF 4</div>
        <h1 className="text-h1 text-navy mt-2">How often?</h1>
        <p className="text-body text-slate mt-2">Pick the rhythm. You can change it later.</p>

        <div className="mt-6 flex flex-col gap-3">
          {options.map((opt) => {
            const active = frequency === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => setFrequency(opt.id)}
                className={cn(
                  "w-full text-left rounded-card bg-white p-4 transition-all",
                  active ? "border-2 border-navy" : "border border-light-gray",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="text-h2 text-navy">{opt.title}</div>
                  {active && <Pill tone="mint">Picked</Pill>}
                </div>
                <p className="text-body text-slate mt-2">{opt.subtitle}</p>
              </button>
            );
          })}
        </div>

        <div className="flex-1" />

        <Button
          variant="primary"
          size="lg"
          fullWidth
          onClick={() => navigate("/groups/new/window")}
        >
          Continue
        </Button>
      </div>
    </Layout>
  );
};

export default FrequencyPage;
