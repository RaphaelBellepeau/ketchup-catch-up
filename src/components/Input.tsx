import { InputHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, id, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={id} className="text-meta uppercase tracking-wider text-slate">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={cn(
            "h-12 w-full rounded-field border border-light-gray bg-white px-4 text-body text-navy",
            "placeholder:text-slate/70",
            "focus:outline-none focus:border-ketchup-red focus:ring-2 focus:ring-ketchup-red/20",
            "disabled:opacity-50",
            className,
          )}
          {...props}
        />
      </div>
    );
  },
);
Input.displayName = "Input";
