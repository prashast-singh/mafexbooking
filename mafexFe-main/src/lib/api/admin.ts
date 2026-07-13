import { apiFetch } from "@/lib/api/client";
import type {
  AdminBookingDetailOut,
  AdminBookingListItem,
  AdminDashboardSummary,
  AdminRoleUpdateBody,
  AdminUserOut,
  AmenityCreateBody,
  AmenityOut,
  AmenityUpdateBody,
  BookableUnitCreateBody,
  BookableUnitOut,
  BookableUnitUpdateBody,
  BookingOut,
  PendingBookingOut,
  BookingPolicyOut,
  BookingPolicyUpdateBody,
  BookingSeriesCancelBody,
  BookingSeriesCancelOut,
  InternalDomainCreateBody,
  InternalDomainOut,
  RoomAdminOut,
  RoomAmenityAttachBody,
  RoomCreateBody,
  RoomImageOut,
  RoomUpdateBody,
  UnitConflictCreateBody,
  UnitConflictCreateResponse,
  UnitConflictListItem,
  UserEmailHistoryOut,
} from "@/lib/types/api";

export type BookingDecisionBody = { reason?: string | null };

export type RoomAdminMappingOut = {
  id: number;
  room_id: number;
  user_id: number;
  user_email: string;
  user_full_name: string;
  created_at: string;
};

export async function dashboardSummary() {
  return apiFetch<AdminDashboardSummary>("/admin/dashboard/summary");
}

const ADMIN_LIST_MAX = 100;

export async function listAdminUsers(params?: {
  approval_status?: string;
  q?: string;
  skip?: number;
  limit?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.approval_status) sp.set("approval_status", params.approval_status);
  if (params?.q) sp.set("q", params.q);
  if (params?.skip != null) sp.set("skip", String(Math.max(0, params.skip)));
  if (params?.limit != null) {
    sp.set("limit", String(Math.min(ADMIN_LIST_MAX, Math.max(1, params.limit))));
  }
  const q = sp.toString();
  return apiFetch<AdminUserOut[]>(`/admin/users${q ? `?${q}` : ""}`);
}

export async function pendingApprovals() {
  return apiFetch<AdminUserOut[]>("/admin/users/pending-approvals");
}

export async function approveUser(userId: number) {
  return apiFetch<AdminUserOut>(`/admin/users/${userId}/approve`, { method: "POST" });
}

export async function rejectUser(userId: number) {
  return apiFetch<AdminUserOut>(`/admin/users/${userId}/reject`, { method: "POST" });
}

export async function patchUserRole(userId: number, role: AdminRoleUpdateBody["role"]) {
  const body: AdminRoleUpdateBody = { role };
  return apiFetch<AdminUserOut>(`/admin/users/${userId}/role`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function listUserEmailHistory(userId: number) {
  return apiFetch<UserEmailHistoryOut[]>(`/admin/users/${userId}/email-history`);
}

export async function createAmenity(body: AmenityCreateBody) {
  return apiFetch<AmenityOut>("/admin/amenities", { method: "POST", body: JSON.stringify(body) });
}

export async function updateAmenity(id: number, body: AmenityUpdateBody) {
  return apiFetch<AmenityOut>(`/admin/amenities/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteAmenity(id: number) {
  return apiFetch<void>(`/admin/amenities/${id}`, { method: "DELETE" });
}

export async function createRoom(body: RoomCreateBody) {
  return apiFetch<RoomAdminOut>("/admin/rooms", { method: "POST", body: JSON.stringify(body) });
}

export async function updateRoom(roomId: number, body: RoomUpdateBody) {
  return apiFetch<RoomAdminOut>(`/admin/rooms/${roomId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteRoom(roomId: number) {
  return apiFetch<void>(`/admin/rooms/${roomId}`, { method: "DELETE" });
}

export async function listRoomAmenities(roomId: number) {
  return apiFetch<AmenityOut[]>(`/admin/rooms/${roomId}/amenities`);
}

export async function attachRoomAmenity(roomId: number, amenityId: number) {
  const body: RoomAmenityAttachBody = { amenity_id: amenityId };
  return apiFetch<AmenityOut[]>(`/admin/rooms/${roomId}/amenities`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function detachRoomAmenity(roomId: number, amenityId: number) {
  return apiFetch<AmenityOut[]>(`/admin/rooms/${roomId}/amenities/${amenityId}`, {
    method: "DELETE",
  });
}

export async function uploadRoomImage(roomId: number, file: File, sortOrder = 0) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("sort_order", String(sortOrder));
  return apiFetch<RoomImageOut>(`/admin/rooms/${roomId}/images`, {
    method: "POST",
    body: fd,
  });
}

export async function deleteRoomImage(roomId: number, imageId: number) {
  return apiFetch<void>(`/admin/rooms/${roomId}/images/${imageId}`, { method: "DELETE" });
}

export async function createBookableUnit(roomId: number, body: BookableUnitCreateBody) {
  return apiFetch<BookableUnitOut>(`/admin/rooms/${roomId}/bookable-units`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateBookableUnit(unitId: number, body: BookableUnitUpdateBody) {
  return apiFetch<BookableUnitOut>(`/admin/bookable-units/${unitId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteBookableUnit(unitId: number) {
  return apiFetch<void>(`/admin/bookable-units/${unitId}`, { method: "DELETE" });
}

export async function listRoomAdmins(roomId: number) {
  return apiFetch<RoomAdminMappingOut[]>(`/admin/rooms/${roomId}/admins`);
}

export async function addRoomAdmin(roomId: number, userId: number) {
  return apiFetch<RoomAdminMappingOut>(`/admin/rooms/${roomId}/admins`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
}

export async function deleteRoomAdmin(roomId: number, userId: number) {
  return apiFetch<void>(`/admin/rooms/${roomId}/admins/${userId}`, { method: "DELETE" });
}

export async function listPendingBookings(params?: { room_id?: number; skip?: number; limit?: number }) {
  const sp = new URLSearchParams();
  if (params?.room_id) sp.set("room_id", String(params.room_id));
  if (params?.skip != null) sp.set("skip", String(Math.max(0, params.skip)));
  if (params?.limit != null) sp.set("limit", String(Math.max(1, params.limit)));
  const q = sp.toString();
  return apiFetch<PendingBookingOut[]>(`/admin/bookings/pending${q ? `?${q}` : ""}`);
}

export async function approvePendingBooking(bookingId: number, body: BookingDecisionBody = {}) {
  return apiFetch<BookingOut>(`/admin/bookings/${bookingId}/approve`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function denyPendingBooking(bookingId: number, body: BookingDecisionBody = {}) {
  return apiFetch<BookingOut>(`/admin/bookings/${bookingId}/deny`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listAdminBookings(params?: {
  date_from?: string;
  date_to?: string;
  room_id?: number;
  status?: string;
  user_q?: string;
  series_id?: number;
  booking_kind?: "all" | "single" | "series";
  upcoming_only?: boolean;
  past_only?: boolean;
  skip?: number;
  limit?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.date_from) sp.set("date_from", params.date_from);
  if (params?.date_to) sp.set("date_to", params.date_to);
  if (params?.room_id) sp.set("room_id", String(params.room_id));
  if (params?.status) sp.set("status", params.status);
  if (params?.user_q) sp.set("user_q", params.user_q);
  if (params?.series_id) sp.set("series_id", String(params.series_id));
  if (params?.booking_kind && params.booking_kind !== "all") sp.set("booking_kind", params.booking_kind);
  if (params?.upcoming_only) sp.set("upcoming_only", "true");
  if (params?.past_only) sp.set("past_only", "true");
  if (params?.skip != null) sp.set("skip", String(Math.max(0, params.skip)));
  if (params?.limit != null) sp.set("limit", String(Math.max(1, params.limit)));
  const q = sp.toString();
  return apiFetch<AdminBookingListItem[]>(`/admin/bookings${q ? `?${q}` : ""}`);
}

export async function getAdminBooking(bookingId: number) {
  return apiFetch<AdminBookingDetailOut>(`/admin/bookings/${bookingId}`);
}

export async function adminCancelBooking(bookingId: number, body: BookingDecisionBody = {}) {
  return apiFetch<BookingOut>(`/admin/bookings/${bookingId}/cancel`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function adminCancelBookingSeries(seriesId: number, body: BookingSeriesCancelBody) {
  return apiFetch<BookingSeriesCancelOut>(`/admin/bookings/series/${seriesId}/cancel`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function addUnitConflict(unitId: number, body: UnitConflictCreateBody) {
  return apiFetch<UnitConflictCreateResponse>(`/admin/bookable-units/${unitId}/conflicts`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listUnitConflicts(unitId: number) {
  return apiFetch<UnitConflictListItem[]>(`/admin/bookable-units/${unitId}/conflicts`);
}

export async function deleteUnitConflict(unitId: number, conflictUnitId: number) {
  return apiFetch<void>(
    `/admin/bookable-units/${unitId}/conflicts/${conflictUnitId}`,
    { method: "DELETE" },
  );
}

export async function listInternalDomains() {
  return apiFetch<InternalDomainOut[]>("/admin/config/internal-domains");
}

export async function createInternalDomain(body: InternalDomainCreateBody) {
  return apiFetch<InternalDomainOut>("/admin/config/internal-domains", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteInternalDomain(domainId: number) {
  return apiFetch<void>(`/admin/config/internal-domains/${domainId}`, { method: "DELETE" });
}

export async function getBookingPolicy() {
  return apiFetch<BookingPolicyOut>("/admin/config/booking-policy");
}

export async function patchBookingPolicy(body: BookingPolicyUpdateBody) {
  return apiFetch<BookingPolicyOut>("/admin/config/booking-policy", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}
