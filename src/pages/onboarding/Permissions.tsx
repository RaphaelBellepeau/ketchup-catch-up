import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Calendar, User } from "lucide-react";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { Pill } from "@/components/Pill";
import { cn } from "@/lib/utils";

const Permissions = () => {
  const navigate = useNavigate();
  const [contactsLinked, setContactsLinked] = useState(false);
  // Calendar is "Linked" by default per design (mock state).
  const [calendarLinked] = useState(true);

  const triggerCalendarOAuth = () => {
    // TODO: will GET /calendar/auth-link and redirect to returned URL on phase 6
    console.log("[permissions] triggerCalendarOAuth → placeholder");
  };

  const allowContacts = () => {
    // TODO: will POST /users/sync-contacts on phase 6
    console.log("[permissions] allowContacts → placeholder");
    setContactsLinked(true);
  };

  return (
    <Layout>
      <div className="flex-1 flex flex-col px-6 pt-4 pb-8">
        <div className="text-meta text-slate">STEP 4 OF 4</div>
        <h1 className="text-h1 text-navy mt-2">Last connections</h1>
        <p className="text-body text-slate mt-2">Your agent needs to peek at these.</p>

        <div className="mt-6 flex flex-col gap-3">
          {/* Google Calendar */}
          <button
            type="button"
            onClick={triggerCalendarOAuth}
            className={cn(
              "w-full text-left rounded-card bg-sky p-4 flex items-center gap-3",
              "transition-transform active:scale-[0.99]",
            )}
          >
            <span className="w-11 h-11 rounded-full bg-white flex items-center justify-center shrink-0">
              <Calendar className="w-5 h-5 text-navy" strokeWidth={2} />
            </span>
            <span className="flex-1 min-w-0">
              <span className="block text-h3 text-navy">Google Calendar</span>
              <span className="block text-body text-slate">Read your free slots</span>
            </span>
            <Pill tone={calendarLinked ? "mint" : "neutral"}>
              {calendarLinked ? "Linked" : "Connect"}
            </Pill>
          </button>

          {/* Contacts */}
          <div className="w-full rounded-card bg-lavender p-4 flex items-center gap-3">
            <span className="w-11 h-11 rounded-full bg-white flex items-center justify-center shrink-0">
              <User className="w-5 h-5 text-navy" strokeWidth={2} />
            </span>
            <span className="flex-1 min-w-0">
              <span className="block text-h3 text-navy">Contacts</span>
              <span className="block text-body text-slate">Find your friends</span>
            </span>
            {contactsLinked ? (
              <Pill tone="mint">Linked</Pill>
            ) : (
              <button
                type="button"
                onClick={allowContacts}
                className="rounded-pill bg-coral text-white px-3 py-1 text-meta uppercase tracking-wider"
              >
                Allow
              </button>
            )}
          </div>
        </div>

        <div className="flex-1" />

        <Button
          variant="primary"
          size="lg"
          fullWidth
          onClick={() => navigate("/home")}
        >
          Finish setup
        </Button>
      </div>
    </Layout>
  );
};

export default Permissions;
