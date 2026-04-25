import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";

// TODO: will GET /memories on phase 6
type MemoryItem = {
  id: string;
  scope: "self" | `friend:${string}`;
  label: string;
  content: string;
  tone: "blush" | "mint" | "lavender";
};

const memoryItems: MemoryItem[] = [
  {
    id: "self-1",
    scope: "self",
    label: "ABOUT YOU",
    content:
      "Modern French > bistro. Likes 7:30pm starts on weeknights. 11ème is a sweet spot.",
    tone: "blush",
  },
  {
    id: "friend-marie",
    scope: "friend:marie",
    label: "WITH MARIE",
    content:
      "Quiet places, early evenings. Loved Le Servan — okay to suggest again.",
    tone: "mint",
  },
  {
    id: "friend-tom",
    scope: "friend:tom",
    label: "WITH TOM",
    content:
      "Last seen 6 months ago. Prefers bars over restos — try that next.",
    tone: "lavender",
  },
];

const toneClasses: Record<MemoryItem["tone"], string> = {
  blush: "bg-blush",
  mint: "bg-mint",
  lavender: "bg-lavender",
};

const Memory = () => {
  const navigate = useNavigate();

  const handleCardClick = (item: MemoryItem) => {
    // TODO: open edit modal — will PATCH /memories/:id on phase 6
    console.log("Edit memory:", item.id);
  };

  const handleEditAll = () => {
    // TODO: navigate to full memory list with PATCH/DELETE actions on phase 6
    console.log("Open full memory editor");
  };

  return (
    <Layout className="bg-cream">
      <div className="flex flex-col flex-1 px-6 pt-4 pb-8">
        <p className="text-meta text-coral uppercase">What I've learned</p>
        <h1 className="text-h1 text-navy mt-1">Your agent's memory</h1>

        <div className="flex flex-col gap-4 mt-6">
          {memoryItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => handleCardClick(item)}
              className={`${toneClasses[item.tone]} rounded-card p-5 text-left cursor-pointer transition-transform active:scale-[0.99]`}
            >
              <p className="text-meta text-slate uppercase">{item.label}</p>
              <p className="text-body text-navy mt-2 leading-relaxed">
                {item.content}
              </p>
            </button>
          ))}
        </div>

        <div className="mt-auto pt-8">
          <Button
            variant="ghost"
            fullWidth
            onClick={handleEditAll}
            className="border border-light-gray bg-white"
          >
            Edit what my agent knows
          </Button>
        </div>
      </div>
    </Layout>
  );
};

export default Memory;
