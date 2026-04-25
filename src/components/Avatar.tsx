import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Size = "sm" | "md" | "lg";

interface AvatarProps extends HTMLAttributes<HTMLDivElement> {
  initials: string;
  /** Tailwind brand color token name, e.g. "coral", "mint", "lavender". */
  color?: string;
  size?: Size;
  src?: string;
  alt?: string;
}

const sizes: Record<Size, string> = {
  sm: "h-8 w-8 text-meta",
  md: "h-10 w-10 text-body",
  lg: "h-14 w-14 text-h3",
};

export const Avatar = ({
  initials,
  color = "coral",
  size = "md",
  src,
  alt,
  className,
  ...props
}: AvatarProps) => {
  return (
    <div
      className={cn(
        "inline-flex items-center justify-center rounded-pill font-medium text-navy overflow-hidden",
        sizes[size],
        `bg-${color}`,
        className,
      )}
      {...props}
    >
      {src ? (
        <img src={src} alt={alt ?? initials} className="h-full w-full object-cover" />
      ) : (
        <span>{initials}</span>
      )}
    </div>
  );
};
