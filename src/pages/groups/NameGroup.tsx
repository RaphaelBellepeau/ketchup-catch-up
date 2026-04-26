import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { Avatar } from "@/components/Avatar";
import { useDiscoverableUsers } from "@/hooks/useDiscoverableUsers";
import { useGroupCreation } from "@/store/groupCreation";
import { cn } from "@/lib/utils";

const SUGGESTED_GROUP_NAMES = ["The classics", "Bordeaux crew", "EFREI gang"];

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
  return phone.slice(-2) || "?";
}

const NameGroup = () => {
  const navigate = useNavigate();
  const name = useGroupCreation((s) => s.name);
  const setName = useGroupCreation((s) => s.setName);
  const selected = useGroupCreation((s) => s.selectedFriendIds);

  const usersQuery = useDiscoverableUsers();
  const selectedFriends = (usersQuery.data ?? []).filter((u) =>
    selected.includes(u.id),
  );

  return (
    <Layout>
      <div className="flex-1 flex flex-col px-6 pt-4 pb-6">
        <div className="text-meta text-slate">NEW GROUP · 2 OF 4</div>
        <h1 className="text-h1 text-navy mt-2">Name your group</h1>
        <p className="text-body text-slate mt-2">A short label your agent will use.</p>

        <div className="mt-4">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Group name"
          />
        </div>

        {selectedFriends.length > 0 && (
          <div className="mt-3 rounded-card bg-cream p-3 flex items-center gap-3">
            <div className="flex -space-x-2">
              {selectedFriends.slice(0, 5).map((u) => (
                <Avatar
                  key={u.id}
                  initials={initialsFor(u.name, u.phone)}
                  color={colorFor(u.id)}
                  size="sm"
                  className="ring-2 ring-cream"
                />
              ))}
            </div>
            <div className="text-body text-slate truncate">
              {selectedFriends
                .map((u) => (u.name?.trim().split(/\s+/)[0]) || u.phone)
                .join(" · ")}
            </div>
          </div>
        )}

        <div className="mt-6 border-t border-light-gray pt-4">
          <div className="text-meta text-coral">SUGGESTED BY YOUR AGENT</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {SUGGESTED_GROUP_NAMES.map((s) => {
              const active = s === name;
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() => setName(s)}
                  className={cn(
                    "rounded-pill px-4 h-9 text-body border transition-colors",
                    active
                      ? "bg-ketchup-red border-ketchup-red text-white"
                      : "bg-white border-light-gray text-navy",
                  )}
                >
                  {s}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex-1" />

        <Button
          variant="primary"
          size="lg"
          fullWidth
          disabled={!name.trim()}
          onClick={() => navigate("/groups/new/frequency")}
        >
          Create group
        </Button>
      </div>
    </Layout>
  );
};

export default NameGroup;
