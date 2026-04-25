import { Link } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { BottleLogo } from "@/components/BottleLogo";
import { Card } from "@/components/Card";
import { Pill } from "@/components/Pill";

const routes: { path: string; label: string }[] = [
  { path: "/home", label: "Home" },
  { path: "/onboarding/welcome", label: "Onboarding · Welcome" },
  { path: "/onboarding/sms", label: "Onboarding · SMS" },
  { path: "/onboarding/voice-call", label: "Onboarding · Voice call" },
  { path: "/onboarding/permissions", label: "Onboarding · Permissions" },
  { path: "/groups/new/friends", label: "New group · Friends" },
  { path: "/groups/new/name", label: "New group · Name" },
  { path: "/groups/new/frequency", label: "New group · Frequency" },
  { path: "/groups/new/window", label: "New group · Window" },
  { path: "/catchup/negotiating", label: "Catchup · Negotiating" },
  { path: "/catchup/proposal", label: "Catchup · Proposal" },
  { path: "/catchup/confirmed", label: "Catchup · Confirmed" },
  { path: "/feedback/rating", label: "Feedback · Rating" },
  { path: "/feedback/voice", label: "Feedback · Voice" },
  { path: "/memory", label: "Memory" },
];

const Index = () => {
  return (
    <Layout>
      <div className="px-6 pt-4 pb-8 flex flex-col gap-5">
        <div className="flex items-center gap-3">
          <BottleLogo size={44} />
          <div>
            <h1 className="text-h1 text-navy leading-tight">ketchup</h1>
            <p className="text-meta uppercase tracking-wider text-slate">Foundation ready</p>
          </div>
        </div>

        <Card className="flex flex-col gap-2">
          <Pill tone="mint">Setup complete</Pill>
          <p className="text-body text-charcoal">
            Design system, layout, components, mock data and routes are wired up. Pick a route below
            to start building screens.
          </p>
        </Card>

        <div className="flex flex-col gap-2">
          <h2 className="text-h2 text-navy">Routes</h2>
          <div className="flex flex-col gap-2">
            {routes.map((r) => (
              <Link
                key={r.path}
                to={r.path}
                className="flex items-center justify-between rounded-card border border-light-gray bg-white px-4 py-3 hover:border-ketchup-red transition-colors"
              >
                <span className="text-h3 text-navy">{r.label}</span>
                <span className="text-meta uppercase tracking-wider text-slate">{r.path}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Index;
