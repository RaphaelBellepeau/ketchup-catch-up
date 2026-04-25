import { ChangeEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";
import { toast } from "@/hooks/use-toast";

const CODE_LENGTH = 6;
const RESEND_SECONDS = 24;

/** Mask a phone number like "+33 6 12 34 56 78" → "+33 6 12 …78". */
const maskPhone = (raw: string) => {
  const trimmed = raw.trim();
  if (!trimmed) return "your phone";
  const compact = trimmed.replace(/\s+/g, " ");
  if (compact.length <= 10) return compact;
  const head = compact.slice(0, 9);
  const tail = compact.slice(-2);
  return `${head} …${tail}`;
};

const Sms = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const phone = (location.state as { phone?: string } | null)?.phone ?? "";

  const [digits, setDigits] = useState<string[]>(() => Array(CODE_LENGTH).fill(""));
  const [seconds, setSeconds] = useState(RESEND_SECONDS);
  const [verifying, setVerifying] = useState(false);
  const inputsRef = useRef<Array<HTMLInputElement | null>>([]);

  // Countdown timer
  useEffect(() => {
    if (seconds <= 0) return;
    const id = window.setTimeout(() => setSeconds((s) => s - 1), 1000);
    return () => window.clearTimeout(id);
  }, [seconds]);

  // Autofocus first cell on mount
  useEffect(() => {
    inputsRef.current[0]?.focus();
  }, []);

  const isComplete = useMemo(() => digits.every((d) => d !== ""), [digits]);

  const handleChange = (index: number) => (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, "");
    if (!value) {
      setDigits((prev) => {
        const next = [...prev];
        next[index] = "";
        return next;
      });
      return;
    }

    // Support paste of multiple digits
    setDigits((prev) => {
      const next = [...prev];
      const chars = value.split("");
      let cursor = index;
      for (const ch of chars) {
        if (cursor >= CODE_LENGTH) break;
        next[cursor] = ch;
        cursor += 1;
      }
      const focusTarget = Math.min(cursor, CODE_LENGTH - 1);
      window.setTimeout(() => inputsRef.current[focusTarget]?.focus(), 0);
      return next;
    });
  };

  const handleKeyDown = (index: number) => (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      e.preventDefault();
      setDigits((prev) => {
        const next = [...prev];
        next[index - 1] = "";
        return next;
      });
      inputsRef.current[index - 1]?.focus();
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputsRef.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < CODE_LENGTH - 1) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handleResend = async () => {
    if (seconds > 0 || !phone) return;
    try {
      const { error } = await supabase.auth.signInWithOtp({ phone });
      if (error) throw error;
      setDigits(Array(CODE_LENGTH).fill(""));
      setSeconds(RESEND_SECONDS);
      inputsRef.current[0]?.focus();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not resend code";
      toast({ title: "Couldn't resend", description: message, variant: "destructive" });
    }
  };

  const handleContinue = async () => {
    if (!isComplete || verifying || !phone) return;
    setVerifying(true);
    try {
      const token = digits.join("");
      const { data, error } = await supabase.auth.verifyOtp({ phone, token, type: "sms" });
      if (error) throw error;
      const userId = data.user?.id;
      if (!userId) throw new Error("No user returned");
      navigate("/onboarding/voice-call", { state: { userId, phone } });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Invalid code";
      toast({ title: "Verification failed", description: message, variant: "destructive" });
    } finally {
      setVerifying(false);
    }
  };

  const formatTimer = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <Layout>
      <div className="flex-1 flex flex-col px-6 pb-6">
        <div className="pt-2">
          <p className="text-meta text-slate">STEP 1 OF 4</p>
          <h1 className="text-h1 text-navy mt-3">Verify your number</h1>
          <p className="text-body text-slate mt-2">
            We just texted a code to {maskPhone(phone)}
          </p>
        </div>

        <div className="mt-8 flex justify-center gap-3">
          {digits.map((digit, index) => {
            const isActive = digit !== "" && index === digits.findIndex((d, i) => d !== "" && i === index);
            const isCurrentEmpty = digit === "" && digits.slice(0, index).every((d) => d !== "");
            const highlighted = digit !== "" || isCurrentEmpty;
            return (
              <input
                key={index}
                ref={(el) => (inputsRef.current[index] = el)}
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={CODE_LENGTH}
                value={digit}
                onChange={handleChange(index)}
                onKeyDown={handleKeyDown(index)}
                aria-label={`Digit ${index + 1}`}
                className={cn(
                  "h-16 w-16 rounded-input bg-cream text-navy text-h1 text-center font-medium",
                  "focus:outline-none border-2 transition-colors",
                  highlighted ? "border-ketchup-red text-ketchup-red" : "border-transparent",
                )}
              />
            );
          })}
        </div>

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={handleResend}
            disabled={seconds > 0}
            className={cn(
              "text-body font-medium transition-colors",
              seconds > 0 ? "text-coral cursor-default" : "text-ketchup-red hover:underline",
            )}
          >
            {seconds > 0 ? `Resend code · ${formatTimer(seconds)}` : "Resend code"}
          </button>
        </div>

        <div className="flex-1" />

        <Button
          type="button"
          variant="primary"
          size="lg"
          fullWidth
          disabled={!isComplete || verifying}
          onClick={handleContinue}
        >
          {verifying ? "Verifying…" : "Continue"}
        </Button>
      </div>
    </Layout>
  );
};

export default Sms;
