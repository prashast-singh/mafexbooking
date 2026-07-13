import { apiFetch } from "@/lib/api/client";
import type { RoomBrowsePage, RoomDetailPublic } from "@/lib/types/api";
import { normalizeTimeParam } from "@/lib/utils/time-params";

export type RoomListParams = {
  page?: number;
  limit?: number;
  capacity?: number;
  amenities?: string;
  unit_type?: string;
  date?: string;
  start_time?: string;
  end_time?: string;
  available?: boolean;
};

/** Backend `GET /rooms` — `limit` must be 1–100 (FastAPI `Query(..., le=100)`). */
const ROOMS_LIST_MAX_LIMIT = 100;

export function buildRoomsQuery(params: RoomListParams): string {
  const sp = new URLSearchParams();
  if (params.page != null) sp.set("page", String(params.page));
  if (params.limit != null) {
    sp.set("limit", String(Math.min(ROOMS_LIST_MAX_LIMIT, Math.max(1, params.limit))));
  }
  if (params.capacity != null) sp.set("capacity", String(params.capacity));
  if (params.amenities) sp.set("amenities", params.amenities);
  if (params.unit_type) sp.set("unit_type", params.unit_type);
  if (params.date) sp.set("date", params.date);
  const start = normalizeTimeParam(params.start_time);
  const end = normalizeTimeParam(params.end_time);
  if (start) sp.set("start_time", start);
  if (end) sp.set("end_time", end);
  if (params.available === true) sp.set("available", "true");
  const q = sp.toString();
  return q ? `?${q}` : "";
}

export async function listRooms(params: RoomListParams = {}) {
  return apiFetch<RoomBrowsePage>(`/rooms${buildRoomsQuery(params)}`, {
    cache: "no-store",
  });
}

export async function getRoom(roomId: number) {
  return apiFetch<RoomDetailPublic>(`/rooms/${roomId}`);
}
