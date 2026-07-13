"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { PurposeText } from "@/components/shared/PurposeText";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useAuth } from "@/hooks/use-auth";
import { adminCancelBooking, adminCancelBookingSeries, listAdminBookings } from "@/lib/api/admin";
import { listMyManagedRooms } from "@/lib/api/users";
import type { AdminBookingListItem, ManagedRoomBrief } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";

type CancelTarget =
  | { type: "single"; bookingId: number }
  | { type: "series"; seriesId: number; fromDate?: string };

export default function AdminBookingsPage() {
  const { user } = useAuth();
  const isGlobalAdmin = user?.role === "admin";
  const [managedRooms, setManagedRooms] = useState<ManagedRoomBrief[]>([]);
  const [rows, setRows] = useState<AdminBookingListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [roomId, setRoomId] = useState("");
  const [status, setStatus] = useState("");
  const [userQ, setUserQ] = useState("");
  const [view, setView] = useState<"all" | "upcoming" | "past">("all");
  const [cancelTarget, setCancelTarget] = useState<CancelTarget | null>(null);

  useEffect(() => {
    if (!user || isGlobalAdmin) return;
    void listMyManagedRooms()
      .then(setManagedRooms)
      .catch(() => setManagedRooms([]));
  }, [user, isGlobalAdmin]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rid = roomId.trim() ? Number.parseInt(roomId, 10) : undefined;
      setRows(
        await listAdminBookings({
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          room_id: Number.isFinite(rid) ? rid : undefined,
          status: status || undefined,
          user_q: userQ.trim() || undefined,
          upcoming_only: view === "upcoming",
          past_only: view === "past",
          limit: 200,
        }),
      );
    } catch (e) {
      toast.error(formatApiError(e));
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, roomId, status, userQ, view]);

  useEffect(() => {
    void load();
  }, [load]);

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
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  if (loading) return <LoadingState />;

  const roomNames = Object.fromEntries(managedRooms.map((r) => [r.id, r.name]));

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
          <Input id="date-from" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="date-to">
            To
          </label>
          <Input id="date-to" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="room-id">
            Room
          </label>
          {isGlobalAdmin ? (
            <Input id="room-id" type="number" min={1} value={roomId} onChange={(e) => setRoomId(e.target.value)} />
          ) : (
            <select
              id="room-id"
              className="flex h-9 min-w-[180px] rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              value={roomId}
              onChange={(e) => setRoomId(e.target.value)}
            >
              <option value="">All my rooms</option>
              {managedRooms.map((room) => (
                <option key={room.id} value={String(room.id)}>
                  {room.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="status">
            Status
          </label>
          <Input
            id="status"
            placeholder="confirmed, pending…"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="user-q">
            User search
          </label>
          <Input
            id="user-q"
            placeholder="email or name"
            value={userQ}
            onChange={(e) => setUserQ(e.target.value)}
          />
        </div>
        <div className="flex gap-1">
          {(["all", "upcoming", "past"] as const).map((v) => (
            <Button key={v} variant={view === v ? "secondary" : "outline"} size="sm" onClick={() => setView(v)}>
              {v === "all" ? "All" : v === "upcoming" ? "Upcoming" : "Past"}
            </Button>
          ))}
        </div>
        <Button variant="outline" onClick={() => void load()}>
          Refresh
        </Button>
      </div>

      {rows.length === 0 ? (
        <EmptyState title="No bookings" description="Adjust filters or check back later." />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Room</TableHead>
                <TableHead>Unit</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Time</TableHead>
                <TableHead>Purpose</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Series</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((b) => (
                <TableRow key={b.id}>
                  <TableCell className="font-mono text-xs">{b.id}</TableCell>
                  <TableCell>
                    <div className="text-sm">{b.user_full_name}</div>
                    <div className="text-xs text-muted-foreground">{b.user_email}</div>
                  </TableCell>
                  <TableCell>{b.room_name || roomNames[b.room_id] || b.room_id}</TableCell>
                  <TableCell>{b.unit_name}</TableCell>
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
                  <TableCell className="text-xs text-muted-foreground">
                    {b.series_id ? `#${b.series_id}` : "—"}
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    {(b.status === "confirmed" || b.status === "pending") && (
                      <>
                        <Button variant="outline" size="sm" onClick={() => setCancelTarget({ type: "single", bookingId: b.id })}>
                          Cancel
                        </Button>
                        {b.series_id && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setCancelTarget({
                                type: "series",
                                seriesId: b.series_id!,
                                fromDate: b.booking_date,
                              })
                            }
                          >
                            Cancel from date
                          </Button>
                        )}
                      </>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

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
