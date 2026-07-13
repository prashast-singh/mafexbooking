import { apiFetch } from "@/lib/api/client";
import type {
  BookingCancelBody,
  BookingCreateBody,
  BookingOut,
  BookingSeriesCancelBody,
  BookingSeriesCancelOut,
  BookingSeriesCreateBody,
  BookingSeriesOut,
  BookingSeriesPreviewOut,
  BookingUpdateBody,
} from "@/lib/types/api";

export type { BookingCreateBody } from "@/lib/types/api";

export async function createBooking(body: BookingCreateBody) {
  return apiFetch<BookingOut>("/bookings", {
    method: "POST",
    body: JSON.stringify({
      ...body,
      start_time: normalizeTime(body.start_time),
      end_time: normalizeTime(body.end_time),
    }),
  });
}

export async function previewBookingSeries(body: BookingSeriesCreateBody) {
  return apiFetch<BookingSeriesPreviewOut>("/bookings/series/preview", {
    method: "POST",
    body: JSON.stringify(normalizeSeriesBody(body)),
  });
}

export async function createBookingSeries(body: BookingSeriesCreateBody) {
  return apiFetch<BookingSeriesOut>("/bookings/series", {
    method: "POST",
    body: JSON.stringify(normalizeSeriesBody(body)),
  });
}

export async function cancelBookingSeries(seriesId: number, body: BookingSeriesCancelBody) {
  return apiFetch<BookingSeriesCancelOut>(`/bookings/series/${seriesId}/cancel`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function getBooking(id: number) {
  return apiFetch<BookingOut>(`/bookings/${id}`);
}

export async function cancelBooking(id: number, reason?: string | null) {
  const body: BookingCancelBody = { reason: reason ?? null };
  return apiFetch<BookingOut>(`/bookings/${id}/cancel`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function updateBooking(id: number, body: BookingUpdateBody) {
  const payload: BookingUpdateBody = { ...body };
  if (payload.start_time) payload.start_time = normalizeTime(payload.start_time);
  if (payload.end_time) payload.end_time = normalizeTime(payload.end_time);
  return apiFetch<BookingOut>(`/bookings/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

function normalizeSeriesBody(body: BookingSeriesCreateBody): BookingSeriesCreateBody {
  return {
    ...body,
    start_time: normalizeTime(body.start_time),
    end_time: normalizeTime(body.end_time),
  };
}

/** Backend accepts `time` as `HH:MM` or `HH:MM:SS` (Pydantic). */
function normalizeTime(t: string): string {
  if (t.length === 5) return `${t}:00`;
  return t;
}
