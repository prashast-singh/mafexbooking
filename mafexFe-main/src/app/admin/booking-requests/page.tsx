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
import { useT } from "@/i18n/use-t";
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
  const t = useT();
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
      toast.success(t("admin.bookingApproved"));
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
        toast.success(t("admin.bookingDenied"));
      } else {
        const out = await denySeriesPending(denyAction.seriesId, { reason });
        toast.success(t("admin.deniedCount", { count: out.processed_count }));
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
      toast.success(t("admin.approvedCount", { count: out.processed_count }));
      void load(roomId, true);
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  if (initialLoading && !hasLoadedOnce.current) return <LoadingState />;

  const roomOptions = isGlobalAdmin ? allRooms : managedRooms;

  return (
    <div className="space-y-8 p-6">
      <PageHeader
        title={t("admin.bookingRequests")}
        description={t("admin.bookingRequestsDescription")}
      />
      <div className="flex flex-wrap items-end gap-2">
        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="room-id">
            {t("common.room")}
          </label>
          <select
            id="room-id"
            className={selectClass}
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
          >
            <option value="">{isGlobalAdmin ? t("admin.allRooms") : t("admin.allMyRooms")}</option>
            {roomOptions.map((room) => (
              <option key={room.id} value={String(room.id)}>
                {room.name}
              </option>
            ))}
          </select>
        </div>
        <Button variant="outline" onClick={() => void load(roomId, true)} disabled={refreshing}>
          {t("common.refresh")}
        </Button>
      </div>

      {refreshing && <p className="text-sm text-muted-foreground">{t("admin.updatingRequests")}</p>}

      {rows.length === 0 ? (
        <EmptyState
          title={t("admin.noPendingBookings")}
          description={t("admin.noPendingBookingsDescription")}
        />
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
        title={denyAction?.type === "series" ? t("admin.denySeriesPending") : t("admin.denyBooking")}
        description={t("admin.denyReasonDescription")}
        confirmLabel={t("admin.deny")}
        destructive
        onConfirm={confirmDeny}
      >
        <div className="space-y-2 pt-2">
          <Label htmlFor="deny-reason">{t("admin.reasonOptional")}</Label>
          <Input
            id="deny-reason"
            value={denyReason}
            onChange={(e) => setDenyReason(e.target.value)}
            placeholder={t("admin.reasonPlaceholder")}
          />
        </div>
      </ConfirmDialog>
    </div>
  );
}
