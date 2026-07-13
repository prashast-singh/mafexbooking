"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { AdminBookingRequestsTable } from "@/features/admin/AdminBookingRequestsTable";
import { useAuth } from "@/hooks/use-auth";
import {
  approvePendingBooking,
  approveSeriesPending,
  denyPendingBooking,
  denySeriesPending,
  listPendingBookings,
} from "@/lib/api/admin";
import { listRooms } from "@/lib/api/rooms";
import { listMyManagedRooms } from "@/lib/api/users";
import type { ManagedRoomBrief, PendingBookingOut, RoomBrowseItem } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";

const selectClass =
  "flex h-9 min-w-[180px] rounded-md border border-input bg-transparent px-3 py-1 text-sm";

type DenyAction =
  | { type: "single"; bookingId: number }
  | { type: "series"; seriesId: number };

export default function AdminBookingRequestsPage() {
  const { user } = useAuth();
  const isGlobalAdmin = user?.role === "admin";
  const [rows, setRows] = useState<PendingBookingOut[]>([]);
  const [managedRooms, setManagedRooms] = useState<ManagedRoomBrief[]>([]);
  const [allRooms, setAllRooms] = useState<RoomBrowseItem[]>([]);
  const [roomId, setRoomId] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [denyAction, setDenyAction] = useState<DenyAction | null>(null);
  const [denyReason, setDenyReason] = useState("");
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

  const load = useCallback(
    async (selectedRoomId: string, isRefresh: boolean) => {
      if (isRefresh) setRefreshing(true);
      else setInitialLoading(true);
      try {
        const rid = selectedRoomId.trim() ? Number.parseInt(selectedRoomId, 10) : undefined;
        setRows(
          await listPendingBookings({
            room_id: Number.isFinite(rid) ? rid : undefined,
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
    },
    [],
  );

  useEffect(() => {
    void load(roomId, hasLoadedOnce.current);
  }, [roomId, load]);

  async function approve(id: number) {
    try {
      await approvePendingBooking(id);
      toast.success("Booking approved.");
      void load(roomId, true);
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function confirmDeny() {
    if (!denyAction) return;
    const reason = denyReason.trim() || null;
    try {
      if (denyAction.type === "single") {
        await denyPendingBooking(denyAction.bookingId, { reason });
        toast.success("Booking denied.");
      } else {
        const out = await denySeriesPending(denyAction.seriesId, { reason });
        toast.success(`Denied ${out.processed_count} booking(s).`);
      }
      setDenyAction(null);
      setDenyReason("");
      void load(roomId, true);
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function approveSeries(seriesId: number) {
    try {
      const out = await approveSeriesPending(seriesId);
      toast.success(`Approved ${out.processed_count} booking(s).`);
      void load(roomId, true);
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  if (initialLoading && !hasLoadedOnce.current) return <LoadingState />;

  const roomOptions = isGlobalAdmin ? allRooms : managedRooms;

  return (
    <div className="space-y-8 p-6">
      <PageHeader title="Booking requests" description="Approve or deny pending bookings." />
      <div className="flex flex-wrap items-end gap-2">
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="room-id">
            Room
          </label>
          <select
            id="room-id"
            className={selectClass}
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
          >
            <option value="">{isGlobalAdmin ? "All rooms" : "All my rooms"}</option>
            {roomOptions.map((room) => (
              <option key={room.id} value={String(room.id)}>
                {room.name}
              </option>
            ))}
          </select>
        </div>
        <Button variant="outline" onClick={() => void load(roomId, true)} disabled={refreshing}>
          Refresh
        </Button>
      </div>

      {refreshing && <p className="text-sm text-muted-foreground">Updating requests…</p>}

      {rows.length === 0 ? (
        <EmptyState title="No pending bookings" description="Requests will appear here." />
      ) : (
        <AdminBookingRequestsTable
          rows={rows}
          onApprove={(id) => void approve(id)}
          onDeny={(id) => setDenyAction({ type: "single", bookingId: id })}
          onApproveSeries={(seriesId) => void approveSeries(seriesId)}
          onDenySeries={(seriesId) => setDenyAction({ type: "series", seriesId })}
        />
      )}

      <ConfirmDialog
        open={denyAction != null}
        onOpenChange={(o) => {
          if (!o) {
            setDenyAction(null);
            setDenyReason("");
          }
        }}
        title={denyAction?.type === "series" ? "Deny all pending in series?" : "Deny booking?"}
        description="Optionally provide a reason — it will be emailed to the user."
        confirmLabel="Deny"
        destructive
        onConfirm={confirmDeny}
      >
        <div className="space-y-2 pt-2">
          <Label htmlFor="deny-reason">Reason (optional)</Label>
          <Input
            id="deny-reason"
            value={denyReason}
            onChange={(e) => setDenyReason(e.target.value)}
            placeholder="Not available on this date"
          />
        </div>
      </ConfirmDialog>
    </div>
  );
}
