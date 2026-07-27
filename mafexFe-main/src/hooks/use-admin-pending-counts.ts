"use client";

import { useCallback, useEffect, useState } from "react";

import { getPendingCounts } from "@/lib/api/admin";
import { useAuth } from "@/hooks/use-auth";

const POLL_MS = 45_000;

export type AdminPendingCountsState = {
  pending_approvals: number;
  pending_booking_requests: number;
  total: number;
};

const EMPTY: AdminPendingCountsState = {
  pending_approvals: 0,
  pending_booking_requests: 0,
  total: 0,
};

export function useAdminPendingCounts(): AdminPendingCountsState {
  const { user } = useAuth();
  const isGlobalAdmin = user?.role === "admin";
  const isRoomAdmin = (user?.managed_room_ids?.length ?? 0) > 0;
  const enabled = !!user && (isGlobalAdmin || isRoomAdmin);

  const [counts, setCounts] = useState<AdminPendingCountsState>(EMPTY);

  const refresh = useCallback(async () => {
    if (!enabled) {
      setCounts(EMPTY);
      return;
    }
    try {
      const data = await getPendingCounts();
      const pending_approvals = data.pending_approvals ?? 0;
      const pending_booking_requests = data.pending_booking_requests ?? 0;
      setCounts({
        pending_approvals,
        pending_booking_requests,
        total: pending_approvals + pending_booking_requests,
      });
    } catch {
      /* keep last known counts */
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      setCounts(EMPTY);
      return;
    }

    void refresh();

    const onFocus = () => {
      void refresh();
    };
    window.addEventListener("focus", onFocus);

    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void refresh();
      }
    }, POLL_MS);

    return () => {
      window.removeEventListener("focus", onFocus);
      window.clearInterval(id);
    };
  }, [enabled, refresh]);

  return counts;
}
