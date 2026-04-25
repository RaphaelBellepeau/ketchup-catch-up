import { ReactNode, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

interface RequireAuthProps {
  children: ReactNode;
}

/**
 * Route guard. Redirects to /onboarding/welcome when there is no Supabase session.
 * Sets up an onAuthStateChange listener BEFORE getSession() to avoid races.
 */
export const RequireAuth = ({ children }: RequireAuthProps) => {
  const location = useLocation();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Listener first
    const { data: sub } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
      setLoading(false);
    });

    // Then hydrate existing session
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });

    return () => {
      sub.subscription.unsubscribe();
    };
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-cream">
        <div className="text-meta text-slate">Loading…</div>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/onboarding/welcome" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
};
