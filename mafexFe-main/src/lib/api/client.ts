import type { ApiErrorDetail } from "@/lib/types/api";

const TOKEN_KEY = "mafex_access_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

function baseUrl(): string {
  // SSR (Next.js server): call the API on localhost — the public hostname may be
  // unreachable from inside the VM (firewall / hairpin NAT).
  if (typeof window === "undefined") {
    const internal = process.env.API_INTERNAL_BASE_URL;
    if (internal) return internal.replace(/\/$/, "");
  }
  const u = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!u) throw new Error("NEXT_PUBLIC_API_BASE_URL is not set");
  return u.replace(/\/$/, "");
}

export type ApiClientOptions = RequestInit & {
  /** Set false to skip Authorization header */
  auth?: boolean;
};

export class ApiError extends Error {
  status: number;
  detail: ApiErrorDetail;

  constructor(status: number, detail: ApiErrorDetail) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

function normalizeDetail(raw: unknown): ApiErrorDetail {
  if (raw && typeof raw === "object" && "detail" in raw) {
    return (raw as { detail: ApiErrorDetail }).detail;
  }
  return "Request failed";
}

export async function apiFetch<T = unknown>(
  path: string,
  options: ApiClientOptions = {},
): Promise<T> {
  const { auth = true, headers: hdr, ...rest } = options;
  const headers = new Headers(hdr);
  if (auth && getStoredToken()) {
    headers.set("Authorization", `Bearer ${getStoredToken()}`);
  }
  if (rest.body && !(rest.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${baseUrl()}${path.startsWith("/") ? path : `/${path}`}`, {
    ...rest,
    headers,
  });

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  let json: unknown = null;
  if (text) {
    try {
      json = JSON.parse(text);
    } catch {
      json = { detail: text };
    }
  }

  if (!res.ok) {
    if (res.status === 401) {
      setStoredToken(null);
    }
    throw new ApiError(res.status, normalizeDetail(json));
  }

  return json as T;
}
