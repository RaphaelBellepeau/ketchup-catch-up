// Lists every other registered user — until we wire up real contact-list
// scanning. Used by the "Add friends" step of the New Group flow.

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useProfile } from "@/hooks/useProfile";

export interface DiscoverableUser {
  id: string;
  name: string;
  phone: string;
}

export function useDiscoverableUsers() {
  const { session } = useProfile();
  const userId = session?.user.id ?? null;

  return useQuery<DiscoverableUser[]>({
    queryKey: ["users", "discoverable", userId],
    enabled: Boolean(userId),
    staleTime: 60_000,
    queryFn: () => api<DiscoverableUser[]>("/users/discoverable"),
  });
}
