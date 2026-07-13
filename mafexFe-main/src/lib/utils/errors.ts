import { ApiError } from "@/lib/api/client";
import type { ApiErrorDetail } from "@/lib/types/api";

export function formatApiError(err: unknown): string {
  if (err instanceof ApiError) {
    const d = err.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return d.map((x) => x.msg).join(", ");
    }
    if (d && typeof d === "object" && "message" in d) {
      return String((d as { message: string }).message);
    }
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

export function isApiErrorDetail(x: unknown): x is ApiErrorDetail {
  return x !== null && typeof x === "object";
}
