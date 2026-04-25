import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost";
type Size = "md" | "lg" | "sm";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  fullWidth?: boolean;
}

const variants: Record<Variant, string> = {
  primary: "bg-ketchup-red text-white hover:bg-ketchup-red/90 active:bg-ketchup-red/95",
  secondary: "bg-navy text-cream hover:bg-navy/90 active:bg-navy/95",
  ghost: "bg-transparent text-navy hover:bg-light-gray/60",
};

const sizes: Record<Size, string> = {
  sm: "h-10 px-4 text-body",
  md: "h-12 px-5 text-h3",
  lg: "h-14 px-6 text-h3",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", fullWidth, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-btn font-medium transition-colors",
          "disabled:opacity-50 disabled:pointer-events-none",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ketchup-red focus-visible:ring-offset-2",
          variants[variant],
          sizes[size],
          fullWidth && "w-full",
          className,
        )}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";
