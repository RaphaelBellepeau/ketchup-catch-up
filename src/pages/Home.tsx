import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { Avatar } from "@/components/Avatar";
import { Pill } from "@/components/Pill";
import { useProfile } from "@/hooks/useProfile";
import { useGroups, type GroupSummary } from "@/hooks/useGroups";
import { useCatchups, type CatchupRow } from "@/hooks/useCatchups";

const UPCOMING_STATUSES = "negotiating,proposed,accepted";

function getInitials(name: string, fallback: string): string {
  const cleaned = name.trim();
  if (!cleaned) return fallback;
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function getFirstName(name: string, phone: string): string {
  const trimmed = name.trim();
  if (trimmed) return trimmed.split(/\s+/)[0];
  // Fallback when the user hasn't set a name yet — use a friendly stub
  // rather than the phone number.
  return phone ? "you" : "there";
}

function relativeFromNow(iso: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diffDays = Math.floor((Date.now() - then) / (1000 * 60 * 60 * 24));
  if (diffDays < 1) return "today";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

function catchupTitle(c: CatchupRow): string {
  const vibe = c.vibe?.trim() || "Catch-up";
  const groupName = c.group?.name?.trim();
  return groupName ? `${vibe} · ${groupName}` : vibe;
}

function catchupSubtitle(c: CatchupRow): string {
  if (c.proposal?.time) return c.proposal.time;
  return c.time_window || c.status;
}

function groupSubtitle(g: GroupSummary): string {
  const memberLabel = g.member_count === 1 ? "1 member" : `${g.member_count} members`;
  if (g.has_open_catchup) return `${memberLabel} · catch-up in progress`;
  if (g.last_activity_at) return `${memberLabel} · last ${relativeFromNow(g.last_activity_at)}`;
  return memberLabel;
}

const Home = () => {
  const navigate = useNavigate();
  const { profile } = useProfile();
  const groupsQuery = useGroups();
  const upcomingQuery = useCatchups({ status: UPCOMING_STATUSES });

  const name = profile?.name ?? "";
  const phone = profile?.phone ?? "";
  const initials = getInitials(name, phone.slice(-2) || "?");
  const firstName = getFirstName(name, phone);

  const upcoming = upcomingQuery.data?.[0] ?? null;
  const groups = groupsQuery.data ?? [];
  const isLoading = groupsQuery.isLoading || upcomingQuery.isLoading;

  return (
    <Layout className="bg-cream">
      <div className="flex flex-col flex-1 px-6 pt-4 pb-8">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-meta text-coral uppercase">Home</p>
            <h1 className="text-h1 text-navy mt-1">Hi {firstName}</h1>
          </div>
          <Avatar initials={initials} color="ketchup-red" size="lg" className="text-white" />
        </div>

        <p className="text-body text-slate mt-2">Anyone you want to see soon?</p>

        {/* Coming up */}
        {upcoming ? (
          <button
            type="button"
            onClick={() =>
              navigate(
                upcoming.status === "accepted"
                  ? "/catchup/confirmed"
                  : upcoming.status === "proposed"
                    ? "/catchup/proposal"
                    : "/catchup/negotiating",
                { state: { catchupId: upcoming.id } },
              )
            }
            className="mt-5 bg-sunshine rounded-card p-5 text-left transition-transform active:scale-[0.99]"
          >
            <p className="text-meta text-navy/70 uppercase">Coming up</p>
            <p className="text-h2 text-navy mt-1">{catchupTitle(upcoming)}</p>
            <p className="text-body text-navy/80 mt-1">{catchupSubtitle(upcoming)}</p>
          </button>
        ) : !isLoading ? (
          <div className="mt-5 bg-cream-dark/40 rounded-card p-5 text-center">
            <p className="text-meta text-slate uppercase">Coming up</p>
            <p className="text-body text-navy/80 mt-2">
              Nothing on the radar yet — start a catch-up below.
            </p>
          </div>
        ) : null}

        {/* Groups */}
        <p className="text-meta text-slate uppercase mt-6">Your groups</p>

        <div className="flex flex-col gap-3 mt-3">
          {isLoading && groups.length === 0 ? (
            <div className="text-body text-slate">Loading…</div>
          ) : groups.length === 0 ? (
            <div className="bg-white border border-light-gray rounded-card p-4 text-body text-slate">
              No groups yet. Tap below to start your first catch-up.
            </div>
          ) : (
            groups.map((g) => (
              <button
                key={g.id}
                type="button"
                onClick={() => console.log("Open group:", g.id)}
                className="bg-white border border-light-gray rounded-card p-4 flex items-center justify-between transition-transform active:scale-[0.99]"
              >
                <div className="text-left min-w-0 flex-1">
                  <p className="text-h3 text-navy truncate">{g.name}</p>
                  <p className="text-body text-slate mt-1 truncate">{groupSubtitle(g)}</p>
                </div>
                <Pill tone={g.has_open_catchup ? "mint" : "sunshine"}>
                  {g.has_open_catchup ? "Active" : "Idle"}
                </Pill>
              </button>
            ))
          )}
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
