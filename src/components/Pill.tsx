import { HTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

type Tone = "neutral" | "mint" | "sky" | "lavender" | "sunshine" | "blush" | "coral";

interface PillProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

const tones: Record<Tone, string> = {
  neutral: "bg-light-gray text-navy",
  mint: "bg-mint text-navy",
  sky: "bg-sky text-navy",
  lavender: "bg-lavender text-navy",
  sunshine: "bg-sunshine text-navy",
  blush: "bg-blush text-navy",
  coral: "bg-coral text-white",
};

export const Pill = forwardRef<HTMLSpanElement, PillProps>(
  ({ className, tone = "neutral", ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-pill px-3 py-1 text-meta uppercase tracking-wider",
          tones[tone],
          className,
        )}
        {...props}
      />
    );
  },
);
Pill.displayName = "Pill";
