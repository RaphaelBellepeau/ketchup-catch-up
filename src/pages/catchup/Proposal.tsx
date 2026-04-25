import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
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
import { cn } from "@/lib/utils";

const REFUSE_REASONS = [
  { id: "wrong-day", label: "Wrong day" },
  { id: "wrong-place", label: "Wrong place" },
  { id: "too-expensive", label: "Too expensive" },
  { id: "other", label: "Other" },
];

export default function Proposal() {
  const navigate = useNavigate();
  const location = useLocation();
  const catchupId = (location.state as { catchupId?: string } | null)?.catchupId ?? "catchup-mock";

  const [refuseOpen, setRefuseOpen] = useState(false);
  const [selectedReason, setSelectedReason] = useState<string | null>(null);

  const handleAccept = () => {
    // TODO: will POST /catchups/:id/vote with vote=accept then POST /catchups/:id/finalize on phase 6
    console.log("[mock] accept catchup", catchupId);
    navigate("/catchup/confirmed", { state: { catchupId } });
  };

  const handleSubmitRefuse = () => {
    if (!selectedReason) return;
    // TODO: will POST /catchups/:id/vote with vote=refuse, reason on phase 6
    console.log("[mock] refuse catchup", catchupId, "reason:", selectedReason);
    setRefuseOpen(false);
    navigate("/catchup/negotiating", {
      state: { catchupId, rejectionReason: selectedReason },
    });
  };

  return (
    <div className="min-h-screen bg-white text-navy flex flex-col">
      <div className="flex-1 px-5 pt-10 pb-6 max-w-md mx-auto w-full">
        <p className="text-meta uppercase text-coral mb-3">Proposal ready</p>
        <h2 className="text-h1 text-navy">Thursday, May 1</h2>
        <p className="text-body text-slate mt-2">7:30 pm · Le Servan · 11ème</p>

        <Card className="bg-cream border-cream/0 mt-5">
          <p className="text-meta uppercase text-slate mb-2">Why this place</p>
          <p className="text-body text-navy leading-relaxed">
            Modern French. Quiet enough to talk. Marie liked a similar spot last month. 12 min from each of you.
          </p>
        </Card>

        <Card className="bg-mint border-mint/0 mt-3 flex items-center justify-between">
          <p className="text-body text-navy">All 3 agents agreed</p>
          <Pill className="bg-navy text-cream">Confirmed</Pill>
        </Card>
      </div>

      <div className="px-5 pb-8 pt-4 max-w-md mx-auto w-full">
        <div className="flex gap-3">
          <Button
            variant="ghost"
            className="flex-1 border border-light-gray"
            onClick={() => setRefuseOpen(true)}
          >
            Refuse
          </Button>
          <Button
            variant="primary"
            className="basis-0 grow-[1.4]"
            onClick={handleAccept}
          >
            Accept
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
            disabled={!selectedReason}
            onClick={handleSubmitRefuse}
            className="mt-2"
          >
            Send feedback
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
