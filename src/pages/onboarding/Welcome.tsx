import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { BottleLogo } from "@/components/BottleLogo";
import { supabase } from "@/lib/supabase";
import { devLogin, isDevLoginAvailable } from "@/lib/devLogin";
import { useProfile } from "@/hooks/useProfile";
import { toast } from "@/hooks/use-toast";

/** Normalize a phone number to E.164 (digits + leading +). */
const toE164 = (raw: string) => {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  const hasPlus = trimmed.startsWith("+");
  const digits = trimmed.replace(/\D/g, "");
  return hasPlus ? `+${digits}` : digits ? `+${digits}` : "";
};

const Welcome = () => {
  const navigate = useNavigate();
  const { session, isOnboarded, loading } = useProfile();
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [devSubmitting, setDevSubmitting] = useState(false);
  const devLoginEnabled = isDevLoginAvailable();

  // If the user is already signed in, skip the SMS flow entirely.
  useEffect(() => {
    if (loading || !session) return;
    navigate(isOnboarded ? "/home" : "/onboarding/voice-call", { replace: true });
  }, [loading, session, isOnboarded, navigate]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const e164 = toE164(phone);
    if (!e164) return;
    setSubmitting(true);
    try {
      const { error } = await supabase.auth.signInWithOtp({ phone: e164 });
      if (error) throw error;
      navigate("/onboarding/sms", { state: { phone: e164 } });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not send code";
      toast({ title: "Couldn't send code", description: message, variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDevLogin = async () => {
    setDevSubmitting(true);
    try {
      await devLogin();
      // The useProfile redirect effect will route us as soon as the session
      // hydrates — no need to navigate manually.
    } catch (err) {
      const message = err instanceof Error ? err.message : "Dev login failed";
      toast({ title: "Dev login failed", description: message, variant: "destructive" });
      setDevSubmitting(false);
    }
  };

  return (
    <Layout className="bg-cream">
      <div className="relative flex-1 flex flex-col bg-cream overflow-hidden">
        {/* Decorative blobs */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-20 -right-20 w-64 h-64 rounded-full bg-coral opacity-50"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-10 -left-24 w-64 h-64 rounded-full bg-mint opacity-50"
        />

        {/* Content */}
        <div className="relative flex-1 flex flex-col px-6 pt-8 pb-8">
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
            <BottleLogo size={96} />
            <h1 className="text-h1 text-ketchup-red lowercase">ketchup</h1>
            <p className="text-body text-charcoal max-w-[280px]">
              your agent talks to your friends'
              <br />
              so you actually see them
            </p>
          </div>

          <form onSubmit={handleSubmit} className="relative flex flex-col gap-3">
            <Input
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="+33 6 12 34 56 78"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              aria-label="Phone number"
            />
            <Button type="submit" variant="primary" size="lg" fullWidth disabled={submitting}>
              {submitting ? "Sending code…" : "Get a call from my agent"}
            </Button>
            <p className="text-meta normal-case tracking-normal text-slate text-center mt-1">
              No password. Just pick up.
            </p>

            {devLoginEnabled && (
              <button
                type="button"
                onClick={handleDevLogin}
                disabled={devSubmitting}
                className="mt-2 rounded-pill bg-navy text-cream py-2 text-meta uppercase tracking-wider disabled:opacity-60"
              >
                {devSubmitting ? "Signing in…" : "Dev login (skip SMS)"}
              </button>
            )}
          </form>
        </div>
      </div>
    </Layout>
  );
};

export default Welcome;
