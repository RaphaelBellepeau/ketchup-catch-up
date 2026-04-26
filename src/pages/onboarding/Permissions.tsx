import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Calendar, User } from "lucide-react";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { Pill } from "@/components/Pill";
import { useCalendarStatus } from "@/hooks/useCalendarStatus";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const Permissions = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [contactsLinked, setContactsLinked] = useState(false);

  const {
    isConnected: calendarConnected,
    isLoading: calendarLoading,
    isConnecting: calendarConnecting,
    connect: connectCalendar,
    refetch: refetchCalendar,
  } = useCalendarStatus();

  // Pick up the `?calendar=connected` (or `=error`) marker the backend adds
  // when bouncing the user back here after the OAuth dance.
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const flag = params.get("calendar");
    if (!flag) return;
    if (flag === "connected") {
      toast({ title: "Calendar linked", description: "Google Calendar connected." });
      refetchCalendar();
    } else if (flag === "error") {
      toast({
        title: "Calendar connection failed",
        description: "We couldn't link your calendar. Try again?",
        variant: "destructive",
      });
    }
    // Strip the query param so a refresh doesn't re-toast.
    navigate(location.pathname, { replace: true });
  }, [location.search, location.pathname, navigate, refetchCalendar]);

  const handleConnectCalendar = () => {
    if (calendarConnected || calendarConnecting) return;
    connectCalendar();
  };

  const allowContacts = () => {
    // TODO: phase 6 — POST /users/sync-contacts with the user's address book.
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
            onClick={handleConnectCalendar}
            disabled={calendarConnecting || calendarLoading}
            className={cn(
              "w-full text-left rounded-card bg-sky p-4 flex items-center gap-3",
              "transition-transform active:scale-[0.99] disabled:opacity-70",
            )}
          >
            <span className="w-11 h-11 rounded-full bg-white flex items-center justify-center shrink-0">
              <Calendar className="w-5 h-5 text-navy" strokeWidth={2} />
            </span>
            <span className="flex-1 min-w-0">
              <span className="block text-h3 text-navy">Google Calendar</span>
              <span className="block text-body text-slate">
                Read your free slots
              </span>
            </span>
            <Pill tone={calendarConnected ? "mint" : "neutral"}>
              {calendarConnecting
                ? "Opening…"
                : calendarConnected
                  ? "Linked"
                  : "Connect"}
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
