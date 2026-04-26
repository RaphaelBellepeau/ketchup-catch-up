import { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useProfile } from "@/hooks/useProfile";
import { KetchupSpinner } from "@/components/KetchupSpinner";

interface RequireOnboardedProps {
  children: ReactNode;
}

/**
 * Route guard for screens that require both:
 *   - an authenticated Supabase session, AND
 *   - a backend profile with `onboarded_at` set.
 *
 * Redirect rules:
 *   - no session       → /onboarding/welcome
 *   - session, !onboarded → /onboarding/voice-call
 *   - onboarded        → render children
 */
export const RequireOnboarded = ({ children }: RequireOnboardedProps) => {
  const location = useLocation();
  const { session, isOnboarded, loading } = useProfile();

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-cream">
        <KetchupSpinner size={140} label="Loading…" />
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/onboarding/welcome" replace state={{ from: location.pathname }} />;
  }

  if (!isOnboarded) {
    return <Navigate to="/onboarding/voice-call" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
};
