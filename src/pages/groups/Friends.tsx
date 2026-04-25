import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { Layout } from "@/components/Layout";
import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { friends } from "@/data/friends";
import { useGroupCreation } from "@/store/groupCreation";
import { cn } from "@/lib/utils";

const Friends = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const selected = useGroupCreation((s) => s.selectedFriendIds);
  const toggle = useGroupCreation((s) => s.toggleFriend);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return friends;
    return friends.filter((f) => f.name.toLowerCase().includes(q));
  }, [query]);

  const count = selected.length;

  return (
    <Layout>
      <div className="flex-1 flex flex-col px-6 pt-4 pb-6">
        <div className="text-meta text-slate">NEW GROUP · 1 OF 4</div>
        <h1 className="text-h1 text-navy mt-2">Add friends</h1>

        <div className="mt-4 relative">
          <Search className="w-4 h-4 text-slate absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <Input
            placeholder="Search contacts"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        <ul className="mt-4 flex-1 overflow-y-auto -mx-2">
          {filtered.map((f) => {
            const isSelected = selected.includes(f.id);
            return (
              <li key={f.id}>
                <button
                  type="button"
                  onClick={() => toggle(f.id)}
                  className={cn(
                    "w-full flex items-center gap-3 px-2 py-3 rounded-card text-left",
                    "transition-colors hover:bg-light-gray/40",
                  )}
                >
                  <Avatar initials={f.initials} color={f.avatarColor} size="md" />
                  <div className="flex-1 min-w-0">
                    <div className="text-h3 text-navy truncate">{f.name}</div>
                    <div
                      className={cn(
                        "text-body mt-0.5 flex items-center gap-1.5",
                        f.onKetchup ? "text-coral" : "text-slate",
                      )}
                    >
                      {f.onKetchup && <span className="w-1.5 h-1.5 rounded-pill bg-coral" />}
                      {f.onKetchup ? "On ketchup" : "Will be invited by call"}
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
          })}
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
