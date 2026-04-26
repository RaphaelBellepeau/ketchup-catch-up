import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { Layout } from "@/components/Layout";
import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { useDiscoverableUsers, type DiscoverableUser } from "@/hooks/useDiscoverableUsers";
import { useGroupCreation } from "@/store/groupCreation";
import { cn } from "@/lib/utils";

// Stable color picker so the same user always gets the same chip color.
const AVATAR_COLORS = ["mint", "sunshine", "lavender", "sky", "coral"];

function colorFor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) | 0;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function initialsFor(name: string, phone: string): string {
  const trimmed = name.trim();
  if (trimmed) {
    const parts = trimmed.split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  // Fallback: last two digits of the phone — never blank.
  return phone.slice(-2) || "?";
}

function displayName(u: DiscoverableUser): string {
  return u.name?.trim() || u.phone;
}

const Friends = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const selected = useGroupCreation((s) => s.selectedFriendIds);
  const toggle = useGroupCreation((s) => s.toggleFriend);

  const usersQuery = useDiscoverableUsers();
  const users = usersQuery.data ?? [];

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        u.name?.toLowerCase().includes(q) || u.phone?.toLowerCase().includes(q),
    );
  }, [users, query]);

  const count = selected.length;

  return (
    <Layout>
      <div className="flex-1 flex flex-col px-6 pt-4 pb-6">
        <div className="text-meta text-slate">NEW GROUP · 1 OF 4</div>
        <h1 className="text-h1 text-navy mt-2">Add friends</h1>

        <div className="mt-4 relative">
          <Search className="w-4 h-4 text-slate absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <Input
            placeholder="Search friends"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        <ul className="mt-4 flex-1 overflow-y-auto -mx-2">
          {usersQuery.isLoading && users.length === 0 ? (
            <li className="px-2 py-3 text-body text-slate">Loading friends…</li>
          ) : filtered.length === 0 ? (
            <li className="px-2 py-3 text-body text-slate">
              {query ? "No matches." : "No friends on Ketchup yet."}
            </li>
          ) : (
            filtered.map((u) => {
              const isSelected = selected.includes(u.id);
              const name = displayName(u);
              return (
                <li key={u.id}>
                  <button
                    type="button"
                    onClick={() => toggle(u.id)}
                    className={cn(
                      "w-full flex items-center gap-3 px-2 py-3 rounded-card text-left",
                      "transition-colors hover:bg-light-gray/40",
                    )}
                  >
                    <Avatar
                      initials={initialsFor(u.name, u.phone)}
                      color={colorFor(u.id)}
                      size="md"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-h3 text-navy truncate">{name}</div>
                      <div className="text-body mt-0.5 flex items-center gap-1.5 text-coral">
                        <span className="w-1.5 h-1.5 rounded-pill bg-coral" />
                        On ketchup
                      </div>
                    </div>
                    <span
                      className={cn(
                        "w-6 h-6 rounded-md border-2 flex items-center justify-center shrink-0",
                        isSelected
                          ? "bg-ketchup-red border-ketchup-red"
                          : "border-light-gray bg-white",
                      )}
                      aria-hidden="true"
                    />
                  </button>
                </li>
              );
            })
          )}
        </ul>

        <Button
          variant="primary"
          size="lg"
          fullWidth
          disabled={count === 0}
          onClick={() => navigate("/groups/new/name")}
        >
          {count} selected · Continue
        </Button>
      </div>
    </Layout>
  );
};

export default Friends;
