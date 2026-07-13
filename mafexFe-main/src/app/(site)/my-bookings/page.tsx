"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { PurposeText } from "@/components/shared/PurposeText";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { RescheduleBookingDialog, type RescheduleTarget } from "@/features/bookings/RescheduleBookingDialog";
import { cancelBooking, cancelBookingSeries } from "@/lib/api/bookings";
import { listMyBookingSeries, listMyBookings } from "@/lib/api/users";
import type { BookingOutWithRoom, BookingSeriesOut } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";
import { useAuth } from "@/hooks/use-auth";

type CancelAction =
  | { type: "single"; bookingId: number }
  | { type: "series_all_future"; seriesId: number }
  | { type: "series_from_date"; seriesId: number; fromDate: string };

function seriesLabel(series: BookingSeriesOut) {
  const freq =
    series.frequency === "monthly"
      ? "Monthly"
      : series.interval === 1
        ? "Weekly"
        : `Every ${series.interval} weeks`;
  return `${freq} · ${series.start_time.slice(0, 5)} – ${series.end_time.slice(0, 5)}`;
}

function MyBookingsContent() {
  const { user, refresh } = useAuth();
  const [items, setItems] = useState<BookingOutWithRoom[]>([]);
  const [series, setSeries] = useState<BookingSeriesOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancelAction, setCancelAction] = useState<CancelAction | null>(null);
  const [rescheduleTarget, setRescheduleTarget] = useState<RescheduleTarget | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [bookingsRes, seriesRes] = await Promise.all([listMyBookings(0, 100), listMyBookingSeries()]);
      setItems(bookingsRes.items);
      setSeries(seriesRes);
    } catch (e) {
      toast.error(formatApiError(e));
      setItems([]);
      setSeries([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const seriesById = useMemo(() => new Map(series.map((s) => [s.id, s])), [series]);

  const standalone = items.filter((b) => !b.series_id);
  const seriesGroups = useMemo(() => {
    const grouped = new Map<number, BookingOutWithRoom[]>();
    for (const b of items) {
      if (b.series_id == null) continue;
      grouped.set(b.series_id, [...(grouped.get(b.series_id) ?? []), b]);
    }
    return [...grouped.entries()].sort((a, b) => {
      const da = a[1][0]?.booking_date ?? "";
      const db = b[1][0]?.booking_date ?? "";
      return db.localeCompare(da);
    });
  }, [items]);

  async function confirmCancel() {
    if (!cancelAction) return;
    try {
      if (cancelAction.type === "single") {
        await cancelBooking(cancelAction.bookingId);
        toast.success("Booking cancelled.");
      } else if (cancelAction.type === "series_all_future") {
        const out = await cancelBookingSeries(cancelAction.seriesId, { scope: "all_future" });
        toast.success(`Cancelled ${out.cancelled_count} future booking(s).`);
      } else {
        const out = await cancelBookingSeries(cancelAction.seriesId, {
          scope: "from_date",
          from_date: cancelAction.fromDate,
        });
        toast.success(`Cancelled ${out.cancelled_count} booking(s) from ${cancelAction.fromDate}.`);
      }
      setCancelAction(null);
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  if (loading) return <LoadingState />;

  const canCancel = user?.approval_status === "approved";

  function canModify(status: string) {
    return canCancel && (status === "confirmed" || status === "pending");
  }

  function openReschedule(b: BookingOutWithRoom) {
    setRescheduleTarget({
      bookingId: b.id,
      roomId: b.room_id,
      unitId: b.unit_id,
      bookingDate: b.booking_date,
      startTime: b.start_time,
      endTime: b.end_time,
      purpose: b.purpose,
      mode: "user",
    });
  }
  const hasAny = items.length > 0;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <PageHeader title="My bookings" description="Upcoming and past reservations." />
      {!hasAny ? (
        <div className="space-y-4">
          <EmptyState
            title="No bookings yet"
            description="Pick a room and choose a time slot to book."
          />
          <div className="flex justify-center">
            <Link href="/findroom" className={cn(buttonVariants())}>
              Browse rooms
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-8">
          {seriesGroups.map(([seriesId, bookings]) => {
            const meta = seriesById.get(seriesId);
            const upcoming = bookings.filter((b) => b.status === "confirmed" || b.status === "pending");
            const first = bookings[0];
            return (
              <div key={seriesId} className="space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium">
                      Recurring: {first?.room_name ?? `Room #${first?.room_id}`}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {meta ? seriesLabel(meta) : "Series"} · {bookings.length} occurrence(s)
                    </p>
                    {(meta?.purpose?.trim() || first?.purpose?.trim()) && (
                      <p className="text-sm text-muted-foreground">
                        Purpose: <PurposeText purpose={meta?.purpose ?? first?.purpose} className="inline" />
                      </p>
                    )}
                  </div>
                  {canCancel && upcoming.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCancelAction({ type: "series_all_future", seriesId })}
                      >
                        Cancel all future
                      </Button>
                    </div>
                  )}
                </div>
                <div className="rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Time</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {bookings.map((b) => (
                        <TableRow key={b.id}>
                          <TableCell>{b.booking_date}</TableCell>
                          <TableCell className="whitespace-nowrap">
                            {b.start_time.slice(0, 5)} – {b.end_time.slice(0, 5)}
                          </TableCell>
                          <TableCell>
                            <StatusBadge value={b.status} />
                          </TableCell>
                          <TableCell className="text-right space-x-2">
                            {canModify(b.status) ? (
                              <>
                                <Button variant="outline" size="sm" onClick={() => openReschedule(b)}>
                                  Reschedule
                                </Button>
                                {b.status === "confirmed" && (
                                  <>
                                    <Button variant="outline" size="sm" onClick={() => setCancelAction({ type: "single", bookingId: b.id })}>
                                      Cancel
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() =>
                                        setCancelAction({
                                          type: "series_from_date",
                                          seriesId,
                                          fromDate: b.booking_date,
                                        })
                                      }
                                    >
                                      Cancel from here
                                    </Button>
                                  </>
                                )}
                              </>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            );
          })}

          {standalone.length > 0 && (
            <div className="space-y-2">
              {seriesGroups.length > 0 && <p className="font-medium">Single bookings</p>}
              <div className="rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Room</TableHead>
                      <TableHead>Location</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Time</TableHead>
                      <TableHead>Purpose</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {standalone.map((b) => (
                      <TableRow key={b.id}>
                        <TableCell>
                          <Link href={`/rooms/${b.room_id}`} className="text-primary underline-offset-4 hover:underline">
                            {b.room_name}
                          </Link>
                        </TableCell>
                        <TableCell className="max-w-[360px] truncate" title={b.room_location ?? ""}>
                          {b.room_location ?? "—"}
                        </TableCell>
                        <TableCell>{b.booking_date}</TableCell>
                        <TableCell className="whitespace-nowrap">
                          {b.start_time.slice(0, 5)} – {b.end_time.slice(0, 5)}
                        </TableCell>
                        <TableCell className="max-w-[240px]">
                          <PurposeText purpose={b.purpose} />
                        </TableCell>
                        <TableCell>
                          <StatusBadge value={b.status} />
                        </TableCell>
                        <TableCell className="text-right space-x-2">
                          {canModify(b.status) ? (
                            <>
                              <Button variant="outline" size="sm" onClick={() => openReschedule(b)}>
                                Reschedule
                              </Button>
                              {b.status === "confirmed" && (
                                <Button variant="outline" size="sm" onClick={() => setCancelAction({ type: "single", bookingId: b.id })}>
                                  Cancel
                                </Button>
                              )}
                            </>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </div>
      )}

      <RescheduleBookingDialog
        open={rescheduleTarget != null}
        onOpenChange={(o) => !o && setRescheduleTarget(null)}
        target={rescheduleTarget}
        onSaved={() => void load()}
      />

      <ConfirmDialog
        open={cancelAction != null}
        onOpenChange={(o) => !o && setCancelAction(null)}
        title={
          cancelAction?.type === "single"
            ? "Cancel booking?"
            : cancelAction?.type === "series_all_future"
              ? "Cancel all future in series?"
              : "Cancel from this date onward?"
        }
        description={
          cancelAction?.type === "series_from_date"
            ? `This cancels this and all later occurrences from ${cancelAction.fromDate}.`
            : "This frees the slot(s) for others."
        }
        confirmLabel="Cancel booking(s)"
        destructive
        onConfirm={confirmCancel}
      />
    </div>
  );
}

export default function MyBookingsPage() {
  return (
    <ProtectedRoute>
      <MyBookingsContent />
    </ProtectedRoute>
  );
}
