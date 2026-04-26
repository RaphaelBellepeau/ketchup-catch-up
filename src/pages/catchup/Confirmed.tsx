import { useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Avatar } from "@/components/Avatar";
import { ApiError, api } from "@/lib/api";

interface ProposalRow {
  id: string;
  catchup_id: string;
  venue: string;
  time: string;
  activity: string;
  justification: string;
}
interface CatchupRow {
  id: string;
  group_id: string;
  group?: { id: string; name: string } | null;
  status: string;
}
interface MemberRow {
  user_id: string;
  users?: { id: string; name: string; phone: string } | null;
}

const AVATAR_COLORS = ["mint", "sunshine", "lavender", "sky", "coral"];
function colorFor(key: string): string {
  let hash = 0;
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) | 0;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

export default function Confirmed() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const catchupId = (location.state as { catchupId?: string } | null)?.catchupId;

  const proposalQuery = useQuery<ProposalRow | null>({
    queryKey: ["catchups", catchupId, "proposal"],
    enabled: Boolean(catchupId),
    queryFn: async () => {
      try {
        return await api<ProposalRow>(`/catchups/${catchupId}/proposal`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });

  const catchupQuery = useQuery<CatchupRow | null>({
    queryKey: ["catchups", catchupId, "row"],
    enabled: Boolean(catchupId),
    queryFn: () => api<CatchupRow>(`/catchups/${catchupId}`),
  });

  const membersQuery = useQuery<MemberRow[]>({
    queryKey: ["groups", catchupQuery.data?.group_id, "members"],
    enabled: Boolean(catchupQuery.data?.group_id),
    queryFn: async () => {
      const group = await api<{ id: string; name: string; members?: string[] }>(
        `/groups/${catchupQuery.data!.group_id}`,
      );
      // The /groups/{id} endpoint returns member IDs; fetch their profiles.
      const ids = group.members ?? [];
      const users = await Promise.all(
        ids.map((id) =>
          api<{ id: string; name: string }>(`/users/${id}`).catch(() => null),
        ),
      );
      return users
        .filter((u): u is { id: string; name: string } => Boolean(u))
        .map((u) => ({ user_id: u.id, users: { ...u, phone: "" } }));
    },
  });

  // Demo helper: skip ahead to "the event already happened" so the home
  // screen surfaces the agent's feedback call. In production this flip
  // is driven by a scheduled job once `proposal.time` is in the past.
  const finalizeMutation = useMutation({
    mutationFn: () =>
      api(`/catchups/${catchupId}/finalize`, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["catchups"] });
      navigate("/home");
    },
  });

  if (!catchupId) {
    navigate("/home", { replace: true });
    return null;
  }

  const proposal = proposalQuery.data;
  const members = membersQuery.data ?? [];

  return (
    <div className="min-h-screen bg-cream text-navy flex flex-col">
      <div className="flex-1 px-5 pt-10 pb-6 max-w-md mx-auto w-full flex flex-col items-center">
        <div className="h-20 w-20 rounded-pill bg-mint flex items-center justify-center animate-check-pop">
          <Check className="h-10 w-10 text-navy" strokeWidth={3} />
        </div>
        <h2 className="text-h1 text-navy mt-5 text-center">It's locked in</h2>
        <p className="text-body text-slate mt-2 text-center">Everyone got the invite.</p>

        <Card className="w-full mt-6">
          {proposal ? (
            <>
              <p className="text-meta uppercase text-coral">{proposal.time}</p>
              <h3 className="text-h2 text-navy mt-1">
                {(proposal.activity || "Catch-up").replace(/^\w/, (c) => c.toUpperCase())}
                {catchupQuery.data?.group?.name ? ` with ${catchupQuery.data.group.name}` : ""}
              </h3>
              <p className="text-body text-slate mt-1">{proposal.venue}</p>
            </>
          ) : (
            <p className="text-body text-slate">Loading the agreed plan…</p>
          )}
          <div className="border-t border-light-gray/70 my-3" />
          <div className="flex items-center gap-3">
            <div className="flex -space-x-2">
              {members.slice(0, 4).map((m) => {
                const name = m.users?.name || "?";
                const initials = name.slice(0, 2).toUpperCase();
                return (
                  <Avatar
                    key={m.user_id}
                    initials={initials}
                    color={colorFor(m.user_id)}
                    size="sm"
                    className="ring-2 ring-white"
                  />
                );
              })}
            </div>
            <p className="text-body text-slate">
              {members.length} {members.length === 1 ? "member" : "members"}
            </p>
          </div>
        </Card>
      </div>

      <div className="px-5 pb-8 pt-4 max-w-md mx-auto w-full flex flex-col gap-3">
        <p className="text-meta text-slate text-center">
          Your agent will call you back after the event to debrief.
        </p>
        <Button fullWidth onClick={() => navigate("/home")}>
          Done
        </Button>
        <button
          type="button"
          onClick={() => finalizeMutation.mutate()}
          disabled={finalizeMutation.isPending}
          className="w-full h-12 rounded-btn border border-dashed border-slate/40 text-meta text-slate uppercase tracking-wider hover:bg-light-gray/40 transition-colors"
        >
          {finalizeMutation.isPending
            ? "Skipping ahead…"
            : "Skip to after the event (demo)"}
        </button>
      </div>
    </div>
  );
}
