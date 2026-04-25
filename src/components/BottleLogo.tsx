import { cn } from "@/lib/utils";

interface BottleLogoProps {
  size?: number;
  className?: string;
}

/** Simple ketchup-bottle mark used as the brand logo. */
export const BottleLogo = ({ size = 48, className }: BottleLogoProps) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("text-ketchup-red", className)}
      aria-label="Ketchup logo"
    >
      {/* Cap */}
      <rect x="24" y="6" width="16" height="6" rx="2" fill="#0D1B2A" />
      {/* Neck */}
      <rect x="26" y="12" width="12" height="6" fill="#0D1B2A" />
      {/* Bottle body */}
      <path
        d="M20 22c0-2 1-3 3-4l4-2h10l4 2c2 1 3 2 3 4v28a6 6 0 0 1-6 6H26a6 6 0 0 1-6-6V22z"
        fill="currentColor"
      />
      {/* Label */}
      <rect x="24" y="30" width="16" height="14" rx="2" fill="#FFF3E0" />
      {/* Drip */}
      <circle cx="50" cy="20" r="3" fill="currentColor" />
    </svg>
  );
};
