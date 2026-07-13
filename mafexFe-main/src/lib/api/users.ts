import { apiFetch } from "@/lib/api/client";
import type {
  BookingSeriesOut,
  EmailChangeRequestBody,
  EmailChangeVerifyBody,
  ManagedRoomBrief,
  PaginatedBookings,
  UserEmailHistoryOut,
  UserMeUpdateBody,
  UserPublic,
} from "@/lib/types/api";

/** `GET /users/me` — same `UserPublic` as `GET /auth/me`. */
export async function fetchUserMe() {
  return apiFetch<UserPublic>("/users/me");
}

export async function updateMe(body: UserMeUpdateBody) {
  return apiFetch<UserPublic>("/users/me", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function listMyManagedRooms() {
  return apiFetch<ManagedRoomBrief[]>("/users/me/managed-rooms");
}

/**
 * `GET /users/me/bookings` — backend `limit` is 1–100 (default 20).
 */
export async function listMyBookings(skip = 0, limit = 50) {
  const lim = Math.min(100, Math.max(1, limit));
  const sk = Math.max(0, skip);
  return apiFetch<PaginatedBookings>(`/users/me/bookings?skip=${sk}&limit=${lim}`);
}

export async function listMyBookingSeries() {
  return apiFetch<BookingSeriesOut[]>("/users/me/booking-series");
}

export async function requestEmailChangeOtp(body: EmailChangeRequestBody) {
  return apiFetch<void>("/users/me/email/request-otp", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function verifyEmailChangeOtp(body: EmailChangeVerifyBody) {
  return apiFetch<UserPublic>("/users/me/email/verify-otp", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listMyEmailHistory() {
  return apiFetch<UserEmailHistoryOut[]>("/users/me/email-history");
}
