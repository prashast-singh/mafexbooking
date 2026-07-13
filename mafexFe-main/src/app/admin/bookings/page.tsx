"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { AdminBookingsTable, type CancelTarget } from "@/features/admin/AdminBookingsTable";
import { RescheduleBookingDialog, type RescheduleTarget } from "@/features/bookings/RescheduleBookingDialog";
import { useAuth } from "@/hooks/use-auth";
import { adminCancelBooking, adminCancelBookingSeries, listAdminBookings } from "@/lib/api/admin";
import { listRooms } from "@/lib/api/rooms";
import { listMyManagedRooms } from "@/lib/api/users";
import type { AdminBookingListItem, ManagedRoomBrief, RoomBrowseItem } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";

type BookingKind = "all" | "single" | "series";
type BookingStatus = "" | "confirmed" | "pending" | "cancelled" | "denied";

type AppliedFilters = {
  dateFrom: string;
  dateTo: string;
  roomId: string;
  status: BookingStatus;
  bookingKind: BookingKind;
  seriesId: string;
  userQ: string;
  view: "all" | "upcoming" | "past";
};

const defaultFilters: AppliedFilters = {
  dateFrom: "",
  dateTo: "",
  roomId: "",
  status: "",
  bookingKind: "all",
  seriesId: "",
  userQ: "",
  view: "all",
};

const selectClass =
  "flex h-9 min-w-[140px] rounded-md border border-input bg-transparent px-3 py-1 text-sm";

export default function AdminBookingsPage() {
  const { user } = useAuth();
  const isGlobalAdmin = user?.role === "admin";
  const [managedRooms, setManagedRooms] = useState<ManagedRoomBrief[]>([]);
  const [allRooms, setAllRooms] = useState<RoomBrowseItem[]>([]);
  const [rows, setRows] = useState<AdminBookingListItem[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [draft, setDraft] = useState<AppliedFilters>(defaultFilters);
  const [applied, setApplied] = useState<AppliedFilters>(defaultFilters);
  const [cancelTarget, setCancelTarget] = useState<CancelTarget | null>(null);
  const [rescheduleTarget, setRescheduleTarget] = useState<RescheduleTarget | null>(null);
  const hasLoadedOnce = useRef(false);

  useEffect(() => {
    if (!user) return;
    if (isGlobalAdmin) {
      void listRooms({ limit: 100 })
        .then((page) => setAllRooms(page.items))
        .catch(() => setAllRooms([]));
      return;
    }
    void listMyManagedRooms()
      .then(setManagedRooms)
      .catch(() => setManagedRooms([]));
  }, [user, isGlobalAdmin]);

  const fetchBookings = useCallback(async (filters: AppliedFilters, isRefresh: boolean) => {
    if (isRefresh) setRefreshing(true);
    else setInitialLoading(true);
    try {
      const rid = filters.roomId.trim() ? Number.parseInt(filters.roomId, 10) : undefined;
      const sid = filters.seriesId.trim() ? Number.parseInt(filters.seriesId, 10) : undefined;
      setRows(
        await listAdminBookings({
          date_from: filters.dateFrom || undefined,
          date_to: filters.dateTo || undefined,
          room_id: Number.isFinite(rid) ? rid : undefined,
          status: filters.status || undefined,
          booking_kind: filters.bookingKind,
          series_id: Number.isFinite(sid) ? sid : undefined,
          user_q: filters.userQ.trim() || undefined,
          upcoming_only: filters.view === "upcoming",
          past_only: filters.view === "past",
          limit: 200,
        }),
      );
    } catch (e) {
      toast.error(formatApiError(e));
      setRows([]);
    } finally {
      setInitialLoading(false);
      setRefreshing(false);
      hasLoadedOnce.current = true;
    }
  }, []);

  useEffect(() => {
    void fetchBookings(applied, hasLoadedOnce.current);
  }, [applied, fetchBookings]);

  function applyFilters() {
    setApplied({ ...draft });
  }

  function applyView(view: AppliedFilters["view"]) {
    const next = { ...draft, view };
    setDraft(next);
    setApplied(next);
  }

  function onSelectChange<K extends keyof AppliedFilters>(key: K, value: AppliedFilters[K]) {
    const next = { ...draft, [key]: value };
    setDraft(next);
    setApplied(next);
  }

  async function confirmCancel() {
    if (!cancelTarget) return;
    try {
      if (cancelTarget.type === "single") {
        await adminCancelBooking(cancelTarget.bookingId);
        toast.success("Booking cancelled.");
      } else if (cancelTarget.fromDate) {
        const out = await adminCancelBookingSeries(cancelTarget.seriesId, {
          scope: "from_date",
          from_date: cancelTarget.fromDate,
        });
        toast.success(`Cancelled ${out.cancelled_count} booking(s).`);
      } else {
        const out = await adminCancelBookingSeries(cancelTarget.seriesId, { scope: "all_future" });
        toast.success(`Cancelled ${out.cancelled_count} future booking(s).`);
      }
      setCancelTarget(null);
      void fetchBookings(applied, true);
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  if (initialLoading && !hasLoadedOnce.current) return <LoadingState />;

  const roomNames = Object.fromEntries(
    (isGlobalAdmin ? allRooms.map((r) => [r.id, r.name]) : managedRooms.map((r) => [r.id, r.name])),
  );

  return (
    <div className="space-y-8 p-6">
      <PageHeader
        title={isGlobalAdmin ? "All bookings" : "Room bookings"}
        description={
          isGlobalAdmin
            ? "View and cancel past and upcoming bookings."
            : managedRooms.length > 0
              ? `Manage bookings for: ${managedRooms.map((r) => r.name).join(", ")}`
              : "View and cancel bookings for rooms you administer."
        }
      />

      <div className="flex flex-wrap items-end gap-2">
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="date-from">
            From
          </label>
          <Input
            id="date-from"
            type="date"
            value={draft.dateFrom}
            onChange={(e) => setDraft((d) => ({ ...d, dateFrom: e.target.value }))}
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="date-to">
            To
          </label>
          <Input
            id="date-to"
            type="date"
            value={draft.dateTo}
            onChange={(e) => setDraft((d) => ({ ...d, dateTo: e.target.value }))}
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="room-id">
            Room
          </label>
          <select
            id="room-id"
            className={selectClass}
            value={draft.roomId}
            onChange={(e) => onSelectChange("roomId", e.target.value)}
          >
            <option value="">{isGlobalAdmin ? "All rooms" : "All my rooms"}</option>
            {(isGlobalAdmin ? allRooms : managedRooms).map((room) => (
              <option key={room.id} value={String(room.id)}>
                {room.name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="status">
            Status
          </label>
          <select
            id="status"
            className={selectClass}
            value={draft.status}
            onChange={(e) => onSelectChange("status", e.target.value as BookingStatus)}
          >
            <option value="">All statuses</option>
            <option value="confirmed">Confirmed</option>
            <option value="pending">Pending</option>
            <option value="cancelled">Cancelled</option>
            <option value="denied">Denied</option>
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="booking-kind">
            Booking type
          </label>
          <select
            id="booking-kind"
            className={selectClass}
            value={draft.bookingKind}
            onChange={(e) => onSelectChange("bookingKind", e.target.value as BookingKind)}
          >
            <option value="all">All types</option>
            <option value="single">Single</option>
            <option value="series">Series</option>
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="series-id">
            Series #
          </label>
          <Input
            id="series-id"
            type="number"
            min={1}
            placeholder="e.g. 12"
            value={draft.seriesId}
            onChange={(e) => setDraft((d) => ({ ...d, seriesId: e.target.value }))}
            disabled={draft.bookingKind === "single"}
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="user-q">
            User search
          </label>
          <Input
            id="user-q"
            placeholder="email or name"
            value={draft.userQ}
            onChange={(e) => setDraft((d) => ({ ...d, userQ: e.target.value }))}
            onKeyDown={(e) => {
              if (e.key === "Enter") applyFilters();
            }}
          />
        </div>
        <div className="flex gap-1">
          {(["all", "upcoming", "past"] as const).map((v) => (
            <Button key={v} variant={draft.view === v ? "secondary" : "outline"} size="sm" onClick={() => applyView(v)}>
              {v === "all" ? "All" : v === "upcoming" ? "Upcoming" : "Past"}
            </Button>
          ))}
        </div>
        <Button onClick={applyFilters} disabled={refreshing}>
          Search
        </Button>
        <Button variant="outline" onClick={() => void fetchBookings(applied, true)} disabled={refreshing}>
          Refresh
        </Button>
      </div>

      {refreshing && <p className="text-sm text-muted-foreground">Updating bookings…</p>}

      {rows.length === 0 ? (
        <EmptyState title="No bookings" description="Adjust filters or check back later." />
      ) : (
        <AdminBookingsTable
          rows={rows}
          roomNames={roomNames}
          onCancel={setCancelTarget}
          onEdit={(b) =>
            setRescheduleTarget({
              bookingId: b.id,
              roomId: b.room_id,
              unitId: b.unit_id,
              bookingDate: b.booking_date,
              startTime: b.start_time,
              endTime: b.end_time,
              purpose: b.purpose,
              mode: "admin",
              seriesId: b.series_id,
            })
          }
        />
      )}

      <RescheduleBookingDialog
        open={rescheduleTarget != null}
        onOpenChange={(o) => !o && setRescheduleTarget(null)}
        target={rescheduleTarget}
        onSaved={() => void fetchBookings(applied, true)}
      />

      <ConfirmDialog
        open={cancelTarget != null}
        onOpenChange={(o) => !o && setCancelTarget(null)}
        title={cancelTarget?.type === "single" ? "Cancel booking?" : "Cancel series bookings?"}
        description="This action cannot be undone."
        confirmLabel="Cancel booking(s)"
        destructive
        onConfirm={confirmCancel}
      />
    </div>
  );
}
