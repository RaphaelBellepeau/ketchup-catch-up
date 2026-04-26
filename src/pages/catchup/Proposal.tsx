import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Pill } from "@/components/Pill";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { ApiError, api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const REFUSE_REASONS = [
  { id: "wrong-day", label: "Wrong day" },
  { id: "wrong-place", label: "Wrong place" },
  { id: "too-expensive", label: "Too expensive" },
  { id: "other", label: "Other" },
];

interface ProposalRow {
  id: string;
  catchup_id: string;
  venue: string;
  time: string;
  activity: string;
  justification: string;
  created_at: string;
}

export default function Proposal() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const catchupId = (location.state as { catchupId?: string } | null)?.catchupId;

  const [refuseOpen, setRefuseOpen] = useState(false);
  const [selectedReason, setSelectedReason] = useState<string | null>(null);

  const proposalQuery = useQuery<ProposalRow | null>({
    queryKey: ["catchups", catchupId, "proposal"],
    enabled: Boolean(catchupId),
    refetchInterval: (q) => (q.state.data ? false : 1500),
    queryFn: async () => {
      try {
        return await api<ProposalRow>(`/catchups/${catchupId}/proposal`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });

  const acceptMutation = useMutation({
    mutationFn: () =>
      api(`/catchups/${catchupId}/vote`, {
        method: "POST",
        json: { vote: "accept" },
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["catchups"] });
      navigate("/catchup/confirmed", { state: { catchupId } });
    },
    onError: (err) => {
      toast({
        title: "Couldn't accept",
        description: err instanceof Error ? err.message : "Try again?",
        variant: "destructive",
      });
    },
  });

  const refuseMutation = useMutation({
    mutationFn: (reason: string) =>
      api(`/catchups/${catchupId}/vote`, {
        method: "POST",
        json: { vote: "reject", reason },
      }),
    onSuccess: async () => {
      // Drop the stale proposal from the cache so we don't flash it on
      // /negotiating before the new negotiation produces a fresh one.
      await queryClient.invalidateQueries({
        queryKey: ["catchups", catchupId, "proposal"],
      });
      queryClient.removeQueries({
        queryKey: ["catchups", catchupId, "proposal"],
      });
      setRefuseOpen(false);
      navigate("/catchup/negotiating", {
        state: { catchupId, rejectionReason: selectedReason },
      });
    },
    onError: (err) => {
      toast({
        title: "Couldn't refuse",
        description: err instanceof Error ? err.message : "Try again?",
        variant: "destructive",
      });
    },
  });

  if (!catchupId) {
    navigate("/home", { replace: true });
    return null;
  }

  const proposal = proposalQuery.data;
  const isWaiting = proposalQuery.isLoading || (!proposal && proposalQuery.isFetching);

  return (
    <div className="min-h-screen bg-white text-navy flex flex-col">
      <div className="flex-1 px-5 pt-10 pb-6 max-w-md mx-auto w-full">
        <p className="text-meta uppercase text-coral mb-3">Proposal ready</p>

        {proposal ? (
          <>
            <h2 className="text-h1 text-navy">{proposal.time}</h2>
            <p className="text-body text-slate mt-2">{proposal.venue}</p>

            {proposal.justification && (
              <Card className="bg-cream border-cream/0 mt-5">
                <p className="text-meta uppercase text-slate mb-2">Why this place</p>
                <p className="text-body text-navy leading-relaxed">{proposal.justification}</p>
              </Card>
            )}

            <Card className="bg-mint border-mint/0 mt-3 flex items-center justify-between">
              <p className="text-body text-navy">All agents agreed</p>
              <Pill className="bg-navy text-cream">Locked in</Pill>
            </Card>
          </>
        ) : isWaiting ? (
          <div className="mt-10 text-body text-slate">Waiting for the agents to land a deal…</div>
        ) : (
          <div className="mt-10 text-body text-ketchup-red">
            No proposal yet. Try refreshing or relaunching the catch-up.
          </div>
        )}
      </div>

      <div className="px-5 pb-8 pt-4 max-w-md mx-auto w-full">
        <div className="flex gap-3">
          <Button
            variant="ghost"
            className="flex-1 border border-light-gray"
            onClick={() => setRefuseOpen(true)}
            disabled={!proposal}
          >
            Refuse
          </Button>
          <Button
            variant="primary"
            className="basis-0 grow-[1.4]"
            onClick={() => acceptMutation.mutate()}
            disabled={!proposal || acceptMutation.isPending}
          >
            {acceptMutation.isPending ? "Saving…" : "Accept"}
          </Button>
        </div>
      </div>

      <Dialog open={refuseOpen} onOpenChange={setRefuseOpen}>
        <DialogContent className="bg-white rounded-card border-0">
          <DialogHeader>
            <DialogTitle className="text-h2 text-navy text-left">What didn't work?</DialogTitle>
            <DialogDescription className="text-body text-slate text-left">
              Help your agent learn what to avoid next time.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-wrap gap-2 py-2">
            {REFUSE_REASONS.map((r) => {
              const selected = selectedReason === r.id;
              return (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setSelectedReason(r.id)}
                  className={cn(
                    "rounded-pill px-4 py-2 text-body transition-colors border",
                    selected
                      ? "bg-ketchup-red text-white border-ketchup-red"
                      : "bg-white text-navy border-light-gray hover:bg-light-gray/40",
                  )}
                >
                  {r.label}
                </button>
              );
            })}
          </div>
          <Button
            fullWidth
            disabled={!selectedReason || refuseMutation.isPending}
            onClick={() => selectedReason && refuseMutation.mutate(selectedReason)}
            className="mt-2"
          >
            {refuseMutation.isPending ? "Sending…" : "Send feedback"}
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
