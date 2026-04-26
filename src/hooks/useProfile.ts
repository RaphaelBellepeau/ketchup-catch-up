// Fetches the current user's backend profile (/users/me).
// Returns null when unauthenticated; never throws on 401 so guards can react.

import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import { ApiError, api } from "@/lib/api";

export interface BackendUserProfile {
  id: string;
  phone: string;
  name: string;
  created_at: string;
  /** ISO timestamp set when the user finishes voice onboarding. */
  onboarded_at: string | null;
}

export interface UseProfileResult {
  /** Supabase session — null while not signed in. */
  session: Session | null;
  /** Backend profile — null if unauthenticated or 404. */
  profile: BackendUserProfile | null;
  /** True only when we have a session AND backend confirmed onboarded_at. */
  isOnboarded: boolean;
  /** True while either Supabase session or backend profile are still loading. */
  loading: boolean;
  /** Re-fetch the backend profile (useful after the voice call ends). */
  refetch: () => Promise<unknown>;
}

/**
 * Subscribe to the Supabase session. The Supabase client persists to
 * localStorage so this hydrates immediately on refresh in most cases.
 */
function useSupabaseSession(): { session: Session | null; ready: boolean } {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Subscribe first so we don't miss events that fire during getSession().
    const { data: sub } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
      setReady(true);
    });
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setReady(true);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  return { session, ready };
}

export function useProfile(): UseProfileResult {
  const { session, ready: sessionReady } = useSupabaseSession();
  const userId = session?.user.id ?? null;

  // IMPORTANT: keep the queryKey scoped to the user id, NOT the access_token.
  // Supabase silently rotates the access token (every ~hour by default, or on
  // demand), and re-keying on every rotation re-instantiates the query → that
  // bumps `isLoading` back to true → RequireAuth unmounts its children → any
  // long-lived child (e.g. the voice WebSocket) gets torn down. The token is
  // attached fresh at request time inside api.ts, so we don't need it here.
  const profileQuery = useQuery<BackendUserProfile | null>({
    queryKey: ["users", "me", userId],
    enabled: Boolean(userId),
    staleTime: 30_000,
    placeholderData: keepPreviousData, // never blank out during a refetch
    retry: (count, err) => {
      if (err instanceof ApiError && (err.status === 401 || err.status === 404)) {
        return false;
      }
      return count < 2;
    },
    queryFn: async () => {
      try {
        return await api<BackendUserProfile>("/users/me");
      } catch (err) {
        // Treat 404 as "user row not yet created" — same UX as not onboarded.
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });

  const profile = profileQuery.data ?? null;
  const isOnboarded = Boolean(session && profile?.onboarded_at);

  // Loading is true while we still don't know enough to decide:
  //   - Supabase session not yet resolved, OR
  //   - we have a session and the very first profile fetch hasn't returned.
  // Subsequent background refetches don't flip this back to true (keeps
  // RequireAuth stable so its children don't unmount mid-call).
  const loading =
    !sessionReady || (Boolean(session) && profileQuery.data === undefined && profileQuery.isFetching);

  return {
    session,
    profile,
    isOnboarded,
    loading,
    refetch: profileQuery.refetch,
  };
}
