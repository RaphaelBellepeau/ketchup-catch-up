// Lists catchups visible to the current user. The backend joins the parent
// group and the most recent proposal so the UI can render in one query.

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useProfile } from "@/hooks/useProfile";

export type CatchupStatus =
  | "pending"
  | "negotiating"
  | "proposed"
  | "accepted"
  | "done";

export interface CatchupRow {
  id: string;
  group_id: string;
  type: string;
  status: CatchupStatus;
  time_window: string;
  vibe: string;
  created_at: string;
  group: { id: string; name: string } | null;
  proposal: {
    id: string;
    catchup_id: string;
    venue: string;
    time: string;
    activity: string;
    justification: string;
    created_at: string;
  } | null;
  /** True when the current user has already submitted feedback for this catchup. */
  has_my_feedback: boolean;
}

interface UseCatchupsOptions {
  /** Pass a single status or a comma-separated list (forwarded as ?status=). */
  status?: string;
  groupId?: string;
}

export function useCatchups({ status, groupId }: UseCatchupsOptions = {}) {
  const { session } = useProfile();
  const userId = session?.user.id ?? null;

  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (groupId) params.set("group_id", groupId);
  const qs = params.toString();
  const path = qs ? `/catchups?${qs}` : "/catchups";

  return useQuery<CatchupRow[]>({
    queryKey: ["catchups", userId, status ?? null, groupId ?? null],
    enabled: Boolean(userId),
    staleTime: 15_000,
    queryFn: () => api<CatchupRow[]>(path),
  });
}
