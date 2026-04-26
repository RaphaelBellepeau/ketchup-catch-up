// Development-only "skip SMS" login.
//
// One-time Supabase setup required:
//   Dashboard → Authentication → Phone Auth → "Test phone numbers"
//   Add a row matching VITE_DEV_PHONE / VITE_DEV_OTP.
// Supabase then accepts the fixed OTP for that phone without sending SMS.
//
// At runtime this helper:
//   1. Reads VITE_DEV_PHONE / VITE_DEV_OTP from import.meta.env.
//   2. Calls signInWithOtp + verifyOtp in sequence, no UI in the middle.
//   3. Returns the resulting Supabase user id.
//
// `isDevLoginAvailable()` lets components conditionally render the button —
// it returns false in production builds and when env vars are missing.

import { supabase } from "@/lib/supabase";

export function isDevLoginAvailable(): boolean {
  if (!import.meta.env.DEV) return false;
  const phone = import.meta.env.VITE_DEV_PHONE as string | undefined;
  const otp = import.meta.env.VITE_DEV_OTP as string | undefined;
  return Boolean(phone && otp);
}

export async function devLogin(): Promise<string> {
  if (!isDevLoginAvailable()) {
    throw new Error("Dev login unavailable in this build");
  }
  const phone = import.meta.env.VITE_DEV_PHONE as string;
  const otp = import.meta.env.VITE_DEV_OTP as string;

  const sendRes = await supabase.auth.signInWithOtp({ phone });
  if (sendRes.error) {
    throw new Error(`signInWithOtp failed: ${sendRes.error.message}`);
  }

  const verifyRes = await supabase.auth.verifyOtp({
    phone,
    token: otp,
    type: "sms",
  });
  if (verifyRes.error) {
    throw new Error(`verifyOtp failed: ${verifyRes.error.message}`);
  }

  const userId = verifyRes.data.user?.id;
  if (!userId) throw new Error("No user returned from verifyOtp");
  return userId;
}
