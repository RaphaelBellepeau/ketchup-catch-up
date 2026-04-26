import { useEffect, useState } from "react";

const SplashScreen = ({ children }: { children: React.ReactNode }) => {
  const [visible, setVisible] = useState(true);
  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    const fadeTimer = setTimeout(() => setFadeOut(true), 1000);
    const removeTimer = setTimeout(() => setVisible(false), 1500);
    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(removeTimer);
    };
  }, []);

  if (!visible) return <>{children}</>;

  return (
    <>
      {/* Splash overlay — matches Layout's phone-screen shell */}
      <div className="min-h-screen bg-cream/40">
        <div
          className={`max-w-[420px] mx-auto min-h-screen bg-cream flex items-center justify-center transition-opacity duration-500 ${
            fadeOut ? "opacity-0" : "opacity-100"
          }`}
        >
          <img
            src="/Nice_logo.svg"
            alt="Ketchup logo"
            className="w-[60vw] max-w-[280px] h-auto animate-splash-pop"
          />
        </div>
      </div>

      {/* Pre-render children underneath so the app is ready when splash fades */}
      <div className="hidden">{children}</div>

      <style>{`
        @keyframes splash-pop {
          0% { transform: scale(0.6); opacity: 0; }
          100% { transform: scale(1); opacity: 1; }
        }
        .animate-splash-pop {
          animation: splash-pop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
        }
      `}</style>
    </>
  );
};

export default SplashScreen;
