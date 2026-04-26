// Thin fetch wrapper for the Catch-Up backend.
// Auto-attaches the Supabase JWT and a JSON content-type for write methods.
//
// Reads the base URL from VITE_API_BASE_URL. If unset, calls fail loudly so
// we don't accidentally hit a relative path during development.

import { supabase } from "@/lib/supabase";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

if (!API_BASE_URL) {
   
  console.warn("[api] VITE_API_BASE_URL is not set — backend calls will fail");
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  /** JSON body — will be stringified and Content-Type set automatically. */
  json?: unknown;
  /** If true, skip attaching the Authorization header even when a session exists. */
  anonymous?: boolean;
}

/**
 * Make an authenticated request to the Catch-Up backend.
 *
 * Returns the parsed JSON body on success. Throws `ApiError` on non-2xx.
 * For 204 / empty responses, resolves to `null`.
 */
export async function api<T = unknown>(
  path: string,
  { json, anonymous, headers, ...init }: RequestOptions = {},
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;

  const finalHeaders = new Headers(headers);

  if (!anonymous) {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  }

  let body: BodyInit | undefined;
  if (json !== undefined) {
    finalHeaders.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }

  const res = await fetch(url, { ...init, headers: finalHeaders, body });

  if (res.status === 204 || res.headers.get("content-length") === "0") {
    if (!res.ok) {
      throw new ApiError(res.status, null, res.statusText || "Request failed");
    }
    return null as T;
  }

  const contentType = res.headers.get("content-type") ?? "";
  const parsed: unknown = contentType.includes("application/json")
    ? await res.json().catch(() => null)
    : await res.text();

  if (!res.ok) {
    const message =
      typeof parsed === "object" && parsed !== null && "detail" in parsed
        ? String((parsed as { detail: unknown }).detail)
        : res.statusText || "Request failed";
    throw new ApiError(res.status, parsed, message);
  }

  return parsed as T;
}
