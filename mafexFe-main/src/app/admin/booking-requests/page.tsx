"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { PurposeText } from "@/components/shared/PurposeText";
import { EmptyState } from "@/components/shared/EmptyState";
import { useAuth } from "@/hooks/use-auth";
import { approvePendingBooking, denyPendingBooking, listPendingBookings } from "@/lib/api/admin";
import { listRooms } from "@/lib/api/rooms";
import { listMyManagedRooms } from "@/lib/api/users";
import type { ManagedRoomBrief, PendingBookingOut, RoomBrowseItem } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";

const selectClass =
  "flex h-9 min-w-[180px] rounded-md border border-input bg-transparent px-3 py-1 text-sm";

export default function AdminBookingRequestsPage() {
  const { user } = useAuth();
  const isGlobalAdmin = user?.role === "admin";
  const [rows, setRows] = useState<PendingBookingOut[]>([]);
  const [managedRooms, setManagedRooms] = useState<ManagedRoomBrief[]>([]);
  const [allRooms, setAllRooms] = useState<RoomBrowseItem[]>([]);
  const [roomId, setRoomId] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
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

  async function deny(id: number) {
    try {
      await denyPendingBooking(id);
      toast.success("Booking denied.");
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
                  <TableCell>{b.room_name}</TableCell>
                  <TableCell>{b.unit_name}</TableCell>
                  <TableCell>{b.booking_date}</TableCell>
                  <TableCell className="whitespace-nowrap">
                    {b.start_time.slice(0, 5)} – {b.end_time.slice(0, 5)}
                  </TableCell>
                  <TableCell className="max-w-[280px]">
                    <PurposeText purpose={b.purpose} />
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button size="sm" onClick={() => void approve(b.id)}>
                      Approve
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => void deny(b.id)}>
                      Deny
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
