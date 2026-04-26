import { cn } from "@/lib/utils";

interface LiveLevelsProps {
  /** 0..1 — driven by an AnalyserNode RMS. */
  inputLevel: number;
  /** 0..1 — driven by an AnalyserNode RMS on the agent's TTS output. */
  outputLevel: number;
  /** Number of bars to render. */
  bars?: number;
  className?: string;
}

/**
 * Real-time level meter. Each bar is sized by the current input or output
 * level — input bars on the left, output bars on the right, mirrored from
 * the center. When the user speaks the left half lights up; when the agent
 * speaks the right half does. Useful for diagnosing whether the mic is
 * actually picking up audio AND whether the agent is producing any.
 */
export const LiveLevels = ({
  inputLevel,
  outputLevel,
  bars = 18,
  className,
}: LiveLevelsProps) => {
  const half = Math.floor(bars / 2);
  const items = Array.from({ length: bars });

  return (
    <div
      className={cn("flex items-center justify-center gap-1 h-12", className)}
      aria-hidden="true"
    >
      {items.map((_, i) => {
        const fromCenter = Math.abs(i - half) / Math.max(1, half);
        const isLeft = i < half;
        const level = isLeft ? inputLevel : outputLevel;
        // Bars closer to the center are more responsive — they react to lower
        // levels — while edges only fire when audio is loud.
        const eased = Math.max(0, level * (1 - fromCenter * 0.6));
        const height = 6 + Math.min(40, eased * 60);
        const colorClass = isLeft ? "bg-cream" : "bg-mint";
        return (
          <span
            key={i}
            className={cn("w-1 rounded-pill transition-[height] duration-75", colorClass)}
            style={{ height: `${height}px` }}
          />
        );
      })}
    </div>
  );
};
