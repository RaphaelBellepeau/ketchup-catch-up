// Lists the groups the current user belongs to, enriched with member_count
// and recent activity hints from the backend.

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useProfile } from "@/hooks/useProfile";

export interface GroupSummary {
  id: string;
  name: string;
  created_by: string;
  created_at: string;
  member_count: number;
  last_activity_at: string | null;
  has_open_catchup: boolean;
}

export function useGroups() {
  const { session } = useProfile();
  const userId = session?.user.id ?? null;

  return useQuery<GroupSummary[]>({
    queryKey: ["groups", userId],
    enabled: Boolean(userId),
    staleTime: 30_000,
    queryFn: () => api<GroupSummary[]>("/groups"),
  });
}
