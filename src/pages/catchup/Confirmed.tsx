import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Avatar } from "@/components/Avatar";

export default function Confirmed() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-cream text-navy flex flex-col">
      <div className="flex-1 px-5 pt-10 pb-6 max-w-md mx-auto w-full flex flex-col items-center">
        <div className="h-20 w-20 rounded-pill bg-mint flex items-center justify-center animate-check-pop">
          <Check className="h-10 w-10 text-navy" strokeWidth={3} />
        </div>
        <h2 className="text-h1 text-navy mt-5 text-center">It's in your calendar</h2>
        <p className="text-body text-slate mt-2 text-center">Everyone got the invite.</p>

        <Card className="w-full mt-6">
          <p className="text-meta uppercase text-coral">Thu 1 May · 19:30</p>
          <h3 className="text-h2 text-navy mt-1">Dinner with Marie & Tom</h3>
          <p className="text-body text-slate mt-1">Le Servan · 32 rue Saint-Maur</p>
          <div className="border-t border-light-gray/70 my-3" />
          <div className="flex items-center gap-3">
            <div className="flex -space-x-2">
              <Avatar initials="YO" color="ketchup-red" size="sm" className="text-white ring-2 ring-white" />
              <Avatar initials="MA" color="mint" size="sm" className="ring-2 ring-white" />
              <Avatar initials="TO" color="sunshine" size="sm" className="ring-2 ring-white" />
            </div>
            <p className="text-body text-slate">3 confirmed</p>
          </div>
        </Card>

        <button
          type="button"
          className="w-full mt-3 rounded-btn border border-light-gray bg-cream px-5 h-12 text-h3 text-navy hover:bg-white/60 transition-colors"
          onClick={() => console.log("[mock] open google calendar")}
        >
          Open in Google Calendar
        </button>
        <button
          type="button"
          className="w-full mt-2 rounded-btn border border-light-gray bg-cream px-5 h-12 text-h3 text-navy hover:bg-white/60 transition-colors"
          onClick={() => console.log("[mock] get directions")}
        >
          Get directions
        </button>
      </div>

      <div className="px-5 pb-8 pt-4 max-w-md mx-auto w-full">
        <Button fullWidth onClick={() => navigate("/home")}>
          Done
        </Button>
      </div>
    </div>
  );
}
