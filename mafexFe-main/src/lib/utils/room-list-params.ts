import type { RoomListParams } from "@/lib/api/rooms";

export function parseRoomListSearchParams(
  sp: Record<string, string | string[] | undefined>,
): RoomListParams {
  const one = (k: string) => {
    const v = sp[k];
    return Array.isArray(v) ? v[0] : v;
  };
  const page = Math.max(1, Number.parseInt(one("page") || "1", 10) || 1);
  const limit = Math.min(50, Math.max(1, Number.parseInt(one("limit") || "12", 10) || 12));
  const capRaw = one("capacity");
  const capacity = capRaw ? Number.parseInt(capRaw, 10) : undefined;

  const date = one("date");
  const start_time = one("start_time");
  const end_time = one("end_time");
  const hasTimeRange = Boolean(date && start_time && end_time);

  return {
    page,
    limit,
    capacity: capacity != null && !Number.isNaN(capacity) ? capacity : undefined,
    amenities: one("amenities") || undefined,
    unit_type: one("unit_type") || undefined,
    date: date || undefined,
    start_time: start_time || undefined,
    end_time: end_time || undefined,
    available: hasTimeRange ? true : undefined,
  };
}

export function mergeSearchParams(
  current: URLSearchParams,
  updates: Record<string, string | null>,
): string {
  const p = new URLSearchParams(current.toString());
  for (const [k, v] of Object.entries(updates)) {
    if (v === null || v === "") p.delete(k);
    else p.set(k, v);
  }
  return p.toString();
}

export function recordToSearchParams(
  sp: Record<string, string | string[] | undefined>,
): URLSearchParams {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(sp)) {
    if (v === undefined) continue;
    if (Array.isArray(v)) v.forEach((x) => p.append(k, x));
    else p.set(k, v);
  }
  return p;
}
