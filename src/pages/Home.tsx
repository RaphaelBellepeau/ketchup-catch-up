import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { Avatar } from "@/components/Avatar";
import { Pill } from "@/components/Pill";
import { users } from "@/data/mockData";

// TODO: will GET /catchups?status=upcoming, GET /groups on phase 6

type UpcomingCatchup = {
  id: string;
  title: string;
  date: string;
  time: string;
};

type GroupSummary = {
  id: string;
  name: string;
  description: string;
  status: "active" | "idle";
  statusLabel: string;
};

const upcoming: UpcomingCatchup = {
  id: "catchup-up-1",
  title: "Brunch with Léa",
  date: "Sat 10 May",
  time: "11:00",
};

const groups: GroupSummary[] = [
  {
    id: "group-1",
    name: "The classics",
    description: "Marie · Tom · every 2w",
    status: "active",
    statusLabel: "Active",
  },
  {
    id: "group-2",
    name: "Bordeaux crew",
    description: "4 friends · paused",
    status: "idle",
    statusLabel: "Idle 3w",
  },
];

const Home = () => {
  const navigate = useNavigate();
  const me = users.you;
  const userName = "Le R";

  return (
    <Layout className="bg-cream">
      <div className="flex flex-col flex-1 px-6 pt-4 pb-8">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-meta text-coral uppercase">Home</p>
            <h1 className="text-h1 text-navy mt-1">Hi {userName}</h1>
          </div>
          <Avatar
            initials={me.initials === "Y" ? "LR" : me.initials}
            color="ketchup-red"
            size="lg"
            className="text-white"
          />
        </div>

        <p className="text-body text-slate mt-2">Anyone you want to see soon?</p>

        <button
          type="button"
          onClick={() => navigate("/catchup/confirmed")}
          className="mt-5 bg-sunshine rounded-card p-5 text-left transition-transform active:scale-[0.99]"
        >
          <p className="text-meta text-navy/70 uppercase">Coming up</p>
          <p className="text-h2 text-navy mt-1">{upcoming.title}</p>
          <p className="text-body text-navy/80 mt-1">
            {upcoming.date} · {upcoming.time}
          </p>
        </button>

        <p className="text-meta text-slate uppercase mt-6">Your groups</p>

        <div className="flex flex-col gap-3 mt-3">
          {groups.map((g) => (
            <button
              key={g.id}
              type="button"
              onClick={() => console.log("Open group:", g.id)}
              className="bg-white border border-light-gray rounded-card p-4 flex items-center justify-between transition-transform active:scale-[0.99]"
            >
              <div className="text-left">
                <p className="text-h3 text-navy">{g.name}</p>
                <p className="text-body text-slate mt-1">{g.description}</p>
              </div>
              <Pill tone={g.status === "active" ? "mint" : "sunshine"}>
                {g.statusLabel}
              </Pill>
            </button>
          ))}
        </div>

        <div className="mt-auto pt-8">
          <Button
            variant="primary"
            size="lg"
            fullWidth
            onClick={() => navigate("/groups/new/friends")}
          >
            + New catch-up
          </Button>
        </div>
      </div>
    </Layout>
  );
};

export default Home;
