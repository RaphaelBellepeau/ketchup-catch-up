// Lists the memory rows the agent has accumulated for the current user.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useProfile } from "@/hooks/useProfile";

export type MemorySource = "onboarding" | "feedback" | "agent" | "manual" | "demo_seed" | string;

export interface MemoryRow {
  id: string;
  user_id: string;
  scope: string;
  content: string;
  source: MemorySource;
  created_at: string;
}

export function useMemories(scope?: string) {
  const { session } = useProfile();
  const userId = session?.user.id ?? null;
  const params = scope ? `?scope=${encodeURIComponent(scope)}` : "";

  return useQuery<MemoryRow[]>({
    queryKey: ["memories", userId, scope ?? null],
    enabled: Boolean(userId),
    staleTime: 30_000,
    queryFn: () => api<MemoryRow[]>(`/memories${params}`),
  });
}

export function useDeleteMemory() {
  const queryClient = useQueryClient();
  const { session } = useProfile();
  const userId = session?.user.id ?? null;
  return useMutation({
    mutationFn: (memoryId: string) =>
      api(`/memories/${memoryId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories", userId] });
    },
  });
}
