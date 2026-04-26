import { cn } from "@/lib/utils";

interface KetchupSpinnerProps {
  /** Width & height of the spinner in px (default 120) */
  size?: number;
  /** Optional label shown below the spinner */
  label?: string;
  /** Additional classes on the wrapper div */
  className?: string;
}

export const KetchupSpinner = ({
  size = 120,
  label,
  className,
}: KetchupSpinnerProps) => {
  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-3", className)}
    >
      <img
        src="/Nice_logo.svg"
        alt="Loading"
        className="animate-spin-slow"
        style={{ width: size, height: size }}
      />
      {label && (
        <span className="text-body text-slate animate-pulse select-none">
          {label}
        </span>
      )}

      <style>{`
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        .animate-spin-slow {
          animation: spin-slow 1.5s linear infinite;
        }
      `}</style>
    </div>
  );
};
