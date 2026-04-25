import { cn } from "@/lib/utils";

interface WaveformProps {
  bars?: number;
  active?: boolean;
  className?: string;
}

/** Animated audio waveform placeholder for voice screens. */
export const Waveform = ({ bars = 24, active = true, className }: WaveformProps) => {
  return (
    <div
      className={cn("flex items-center justify-center gap-1 h-16", className)}
      aria-hidden="true"
    >
      {Array.from({ length: bars }).map((_, i) => (
        <span
          key={i}
          className={cn(
            "w-1 rounded-pill bg-ketchup-red origin-center",
            active ? "animate-waveform-pulse" : "opacity-40",
          )}
          style={{
            height: `${20 + ((i * 13) % 40)}px`,
            animationDelay: `${(i * 60) % 800}ms`,
          }}
        />
      ))}
    </div>
  );
};
