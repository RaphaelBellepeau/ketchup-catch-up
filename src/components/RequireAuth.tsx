import { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useProfile } from "@/hooks/useProfile";

interface RequireAuthProps {
  children: ReactNode;
}

/**
 * Route guard for screens that need a Supabase session but do NOT require
 * onboarding to have finished (e.g. the voice onboarding screen itself).
 *
 * Redirects to /onboarding/welcome when no session.
 */
export const RequireAuth = ({ children }: RequireAuthProps) => {
  const location = useLocation();
  const { session, loading } = useProfile();

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
