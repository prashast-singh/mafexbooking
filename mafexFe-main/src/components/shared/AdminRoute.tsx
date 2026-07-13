"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { LoadingState } from "@/components/shared/LoadingState";
import { getStoredToken } from "@/lib/api/client";
import { useAuth } from "@/hooks/use-auth";

const ROOM_ADMIN_PATHS = ["/admin/booking-requests", "/admin/bookings"];

function canAccessAdminPath(
  pathname: string,
  role: string,
  managedRoomIds: number[],
): boolean {
  if (role === "admin") return true;
  if (managedRoomIds.length === 0) return false;
  return ROOM_ADMIN_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const isGlobalAdmin = user?.role === "admin";
  const isRoomAdmin = (user?.managed_room_ids?.length ?? 0) > 0;
  const hasAccess = user ? canAccessAdminPath(pathname, user.role, user.managed_room_ids ?? []) : false;

  useEffect(() => {
    if (loading) return;
    if (!getStoredToken()) {
      router.replace("/login");
      return;
    }
    if (!user) return;
    if (isGlobalAdmin) return;
    if (!isRoomAdmin) {
      router.replace("/findroom");
      return;
    }
    if (!hasAccess) {
      router.replace("/admin/booking-requests");
    }
  }, [loading, user, router, pathname, isGlobalAdmin, isRoomAdmin, hasAccess]);

  if (loading) return <LoadingState />;
  if (!getStoredToken() || !user) return null;
  if (!isGlobalAdmin && !isRoomAdmin) return null;
  if (!isGlobalAdmin && !hasAccess) return null;
  return <>{children}</>;
}
