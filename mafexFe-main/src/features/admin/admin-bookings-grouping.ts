import type { AdminBookingListItem } from "@/lib/types/api";

export type AdminBookingRow =
  | { kind: "single"; booking: AdminBookingListItem }
  | { kind: "series"; seriesId: number; bookings: AdminBookingListItem[] };

function sortByDateDesc(bookings: AdminBookingListItem[]) {
  return [...bookings].sort((a, b) => {
    const byDate = b.booking_date.localeCompare(a.booking_date);
    if (byDate !== 0) return byDate;
    return b.start_time.localeCompare(a.start_time);
  });
}

export function groupAdminBookings(rows: AdminBookingListItem[]): AdminBookingRow[] {
  const standalone: AdminBookingListItem[] = [];
  const seriesMap = new Map<number, AdminBookingListItem[]>();

  for (const booking of rows) {
    if (booking.series_id == null) {
      standalone.push(booking);
      continue;
    }
    const list = seriesMap.get(booking.series_id) ?? [];
    list.push(booking);
    seriesMap.set(booking.series_id, list);
  }

  const result: AdminBookingRow[] = standalone.map((booking) => ({ kind: "single", booking }));
  for (const [seriesId, bookings] of seriesMap.entries()) {
    result.push({ kind: "series", seriesId, bookings: sortByDateDesc(bookings) });
  }

  return result.sort((a, b) => {
    const dateA = a.kind === "single" ? a.booking.booking_date : a.bookings[0]?.booking_date ?? "";
    const dateB = b.kind === "single" ? b.booking.booking_date : b.bookings[0]?.booking_date ?? "";
    return dateB.localeCompare(dateA);
  });
}

export function seriesFrequencyLabel(booking: AdminBookingListItem): string | null {
  if (!booking.series_frequency) return null;
  if (booking.series_frequency === "monthly") {
    const interval = booking.series_interval ?? 1;
    return interval === 1 ? "Monthly" : `Every ${interval} months`;
  }
  const interval = booking.series_interval ?? 1;
  return interval === 1 ? "Weekly" : `Every ${interval} weeks`;
}

export function statusSummary(bookings: AdminBookingListItem[]): string {
  const counts = new Map<string, number>();
  for (const b of bookings) {
    counts.set(b.status, (counts.get(b.status) ?? 0) + 1);
  }
  if (counts.size === 1) {
    return bookings[0]?.status ?? "—";
  }
  return [...counts.entries()]
    .map(([status, count]) => `${count} ${status}`)
    .join(", ");
}

export function dateRangeLabel(bookings: AdminBookingListItem[]): string {
  const sorted = sortByDateDesc(bookings);
  const first = sorted[sorted.length - 1]?.booking_date;
  const last = sorted[0]?.booking_date;
  if (!first || !last) return "—";
  if (first === last) return first;
  return `${first} – ${last}`;
}
