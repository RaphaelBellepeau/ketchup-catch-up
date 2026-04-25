import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { cn } from "@/lib/utils";

const EMOJIS = ["😕", "😐", "🙂", "😄", "🤩"] as const;

interface Tag {
  label: string;
  positive: boolean;
}

const TAGS: Tag[] = [
  { label: "Great food", positive: true },
  { label: "Good vibe", positive: true },
  { label: "Too loud", positive: false },
  { label: "Pricey", positive: false },
];

const Rating = () => {
  const navigate = useNavigate();
  const [rating, setRating] = useState<number>(3);
  const [selectedTags, setSelectedTags] = useState<string[]>(["Great food", "Good vibe"]);
  const [comment, setComment] = useState("");

  const toggleTag = (label: string) => {
    setSelectedTags((prev) =>
      prev.includes(label) ? prev.filter((t) => t !== label) : [...prev, label],
    );
  };

  const handleSubmit = () => {
    // TODO: will POST /feedbacks on phase 6
    console.log("[feedback] submit", { rating, selectedTags, comment });
    navigate("/home");
  };

  return (
    <Layout>
      <div className="flex-1 flex flex-col px-6 pt-2 pb-6">
        <div className="text-meta text-coral">LAST NIGHT</div>
        <h1 className="text-h1 text-navy mt-1">How was Le Servan?</h1>
        <p className="text-body text-slate mt-2">Quick tap helps your agent learn.</p>

        {/* Emojis card */}
        <Card className="mt-5 bg-cream border-cream/60 px-3 py-4">
          <div className="flex items-center justify-around">
            {EMOJIS.map((emoji, i) => {
              const selected = rating === i;
              return (
                <button
                  key={emoji}
                  type="button"
                  onClick={() => setRating(i)}
                  aria-label={`Rate ${i + 1} of 5`}
                  aria-pressed={selected}
                  className={cn(
                    "text-3xl transition-transform duration-200 ease-out",
                    selected
                      ? "scale-125 drop-shadow-[0_4px_8px_rgba(0,0,0,0.18)]"
                      : "opacity-80 hover:scale-110",
                  )}
                >
                  {emoji}
                </button>
              );
            })}
          </div>
        </Card>

        {/* Tags */}
        <div className="text-meta uppercase tracking-wider text-slate mt-6">WHAT STOOD OUT</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {TAGS.map((tag) => {
            const active = selectedTags.includes(tag.label);
            return (
              <button
                key={tag.label}
                type="button"
                onClick={() => toggleTag(tag.label)}
                aria-pressed={active}
                className={cn(
                  "rounded-pill px-4 h-9 text-body font-medium transition-colors border",
                  active
                    ? tag.positive
                      ? "bg-mint text-navy border-mint"
                      : "bg-coral text-white border-coral"
                    : "bg-white text-navy border-light-gray hover:bg-light-gray/40",
                )}
              >
                {tag.label}
              </button>
            );
          })}
        </div>

        {/* Comment */}
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Anything else? (optional)"
          rows={3}
          className={cn(
            "mt-5 w-full rounded-field border border-light-gray bg-white px-4 py-3 text-body text-navy resize-none",
            "placeholder:text-slate/70",
            "focus:outline-none focus:border-ketchup-red focus:ring-2 focus:ring-ketchup-red/20",
          )}
        />

        <div className="flex-1" />

        {/* Submit */}
        <Button onClick={handleSubmit} fullWidth size="lg" className="mt-6">
          Send feedback
        </Button>

        <button
          type="button"
          onClick={() => navigate("/feedback/voice")}
          className="mt-4 text-body text-slate hover:text-navy transition-colors text-center"
        >
          Or tell your agent by voice →
        </button>
      </div>
    </Layout>
  );
};

export default Rating;
