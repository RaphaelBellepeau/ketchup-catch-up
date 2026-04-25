import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatusBarProps {
  className?: string;
}

/** iOS-style status bar with time and signal/wifi/battery indicators. */
const StatusBar = ({ className }: StatusBarProps) => {
  return (
    <div
      className={cn(
        "flex items-center justify-between px-6 pt-3 pb-2 text-navy text-h3",
        className,
      )}
    >
      <span className="font-medium tabular-nums">9:41</span>
      <div className="flex items-center gap-1.5">
        {/* Signal dots */}
        <div className="flex items-end gap-[2px]">
          <span className="w-[3px] h-[4px] rounded-pill bg-navy" />
          <span className="w-[3px] h-[6px] rounded-pill bg-navy" />
          <span className="w-[3px] h-[8px] rounded-pill bg-navy" />
          <span className="w-[3px] h-[10px] rounded-pill bg-navy" />
        </div>
        {/* Wifi */}
        <svg width="15" height="11" viewBox="0 0 15 11" fill="none" aria-hidden="true">
          <path
            d="M7.5 10.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM2 5.5a8 8 0 0 1 11 0M4 7.5a5 5 0 0 1 7 0"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
        {/* Battery */}
        <div className="ml-1 flex items-center">
          <div className="w-6 h-3 rounded-[3px] border border-navy flex items-center p-[1px]">
            <div className="h-full w-[80%] bg-navy rounded-[1.5px]" />
          </div>
          <div className="w-[2px] h-[6px] bg-navy rounded-r-[1px]" />
        </div>
      </div>
    </div>
  );
};

interface LayoutProps {
  children: ReactNode;
  /** Hide status bar (e.g. for splash screens). */
  hideStatusBar?: boolean;
  className?: string;
}

export const Layout = ({ children, hideStatusBar, className }: LayoutProps) => {
  return (
    <div className="min-h-screen bg-cream/40">
      <div
        className={cn(
          "max-w-[420px] mx-auto min-h-screen bg-white flex flex-col",
          className,
        )}
      >
        {hideStatusBar && <StatusBar />}
        <main className="flex-1 flex flex-col">{children}</main>
      </div>
    </div>
  );
};
