import { apiFetch } from "@/lib/api/client";
import type { AvailabilitySearchResponse, RoomAvailabilityGrid } from "@/lib/types/api";

export async function getRoomAvailability(roomId: number, date: string) {
  return apiFetch<RoomAvailabilityGrid>(
    `/availability/rooms/${roomId}?date=${encodeURIComponent(date)}`,
    { auth: false },
  );
}

export type SearchParams = {
  date: string;
  capacity?: number;
  amenities?: string;
  unit_type?: string;
  start_time?: string;
  end_time?: string;
};

export async function searchAvailability(params: SearchParams) {
  const sp = new URLSearchParams();
  sp.set("date", params.date);
  if (params.capacity != null) sp.set("capacity", String(params.capacity));
  if (params.amenities) sp.set("amenities", params.amenities);
  if (params.unit_type) sp.set("unit_type", params.unit_type);
  if (params.start_time) sp.set("start_time", params.start_time);
  if (params.end_time) sp.set("end_time", params.end_time);
  return apiFetch<AvailabilitySearchResponse>(`/availability/search?${sp.toString()}`, {
    auth: false,
  });
}
