// Tracks whether the current user has connected Google Calendar.
//
// The connect flow is a server-side OAuth redirect: clicking "Connect"
// fetches `/calendar/auth-link` and bounces the browser to Google. After
// consent, Google → backend `/calendar/callback` → backend → frontend
// `/onboarding/permissions?calendar=connected`. We refetch on mount and
// also expose `connect()` and `disconnect()`.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useProfile } from "@/hooks/useProfile";

interface CalendarStatus {
  connected: boolean;
}

interface AuthLinkResponse {
  url: string;
}

export function useCalendarStatus() {
  const queryClient = useQueryClient();
  const { session } = useProfile();
  const userId = session?.user.id ?? null;

  const statusQuery = useQuery<CalendarStatus>({
    queryKey: ["calendar", "status", userId],
    enabled: Boolean(userId),
    staleTime: 30_000,
    queryFn: () => api<CalendarStatus>("/calendar/status"),
  });

  const connectMutation = useMutation({
    mutationFn: async () => {
      const res = await api<AuthLinkResponse>("/calendar/auth-link");
      // Hand off the tab to Google's consent screen. We won't return here;
      // Google → backend callback → backend redirects back to /permissions.
      window.location.href = res.url;
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: () => api<CalendarStatus>("/calendar/disconnect", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendar", "status", userId] });
    },
  });

  return {
    isConnected: Boolean(statusQuery.data?.connected),
    isLoading: statusQuery.isLoading,
    isConnecting: connectMutation.isPending,
    isDisconnecting: disconnectMutation.isPending,
    connect: connectMutation.mutate,
    disconnect: disconnectMutation.mutate,
    refetch: statusQuery.refetch,
  };
}
