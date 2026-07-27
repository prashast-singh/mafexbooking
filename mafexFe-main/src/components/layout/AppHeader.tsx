"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { CalendarDays, LayoutDashboard, LogIn, LogOut, Settings, UserPlus } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { PendingCountBadge } from "@/components/shared/PendingCountBadge";
import { FIND_ROOM_PATH } from "@/lib/routes";
import { useAdminPendingCounts } from "@/hooks/use-admin-pending-counts";
import { useAuth } from "@/hooks/use-auth";

const nav = [
  { href: FIND_ROOM_PATH, label: "Rooms" },
  { href: "/my-bookings", label: "My bookings", auth: true },
];

export function AppHeader() {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const pending = useAdminPendingCounts();
  const isGlobalAdmin = user?.role === "admin";
  const isRoomAdmin = (user?.managed_room_ids?.length ?? 0) > 0;
  const isApproved = user?.approval_status === "approved";
  const adminHref = isGlobalAdmin ? "/admin" : "/admin/booking-requests";
  const adminLabel = isGlobalAdmin ? "Admin" : "Room admin";
  const homeHref = !user ? "/login" : isApproved ? FIND_ROOM_PATH : "/awaiting-approval";
  const hasPending = pending.total > 0;

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4">
        <Link href={homeHref} className="flex items-center gap-2 font-semibold">
          <Image
            src="/mafex-logo.png"
            alt="MAFEX"
            width={28}
            height={28}
            className="h-7 w-7 rounded-sm object-contain"
            unoptimized
            priority
          />
          Workspace
        </Link>
        <nav className="hidden items-center gap-1 sm:flex">
          {nav.map((item) => {
            if (!isApproved) return null;
            if (item.auth && !user) return null;
            const active = pathname === item.href || pathname.startsWith(`${item.href}?`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(buttonVariants({ variant: active ? "secondary" : "ghost", size: "sm" }))}
              >
                {item.label}
              </Link>
            );
          })}
          {(isGlobalAdmin || isRoomAdmin) && (
            <Link
              href={adminHref}
              className={cn(
                buttonVariants({
                  variant: pathname.startsWith("/admin") ? "secondary" : "ghost",
                  size: "sm",
                }),
                hasPending && "font-semibold text-foreground",
              )}
            >
              <LayoutDashboard className="mr-1 h-4 w-4" />
              {adminLabel}
              <PendingCountBadge count={pending.total} />
            </Link>
          )}
        </nav>
        <div className="flex items-center gap-2">
          {!loading && !user && (
            <>
              <Link href="/login" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}>
                <LogIn className="mr-1 h-4 w-4" />
                Log in
              </Link>
              <Link href="/signup" className={cn(buttonVariants({ size: "sm" }))}>
                <UserPlus className="mr-1 h-4 w-4" />
                Sign up
              </Link>
            </>
          )}
          {user && (
            <DropdownMenu>
              <DropdownMenuTrigger
                className={cn(
                  buttonVariants({ variant: "outline", size: "sm" }),
                  "max-w-[200px] truncate",
                )}
              >
                {user.full_name}
                {hasPending ? <PendingCountBadge count={pending.total} className="ml-2" /> : null}
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem disabled className="text-xs text-muted-foreground">
                  {user.email}
                </DropdownMenuItem>
                {isApproved && (
                  <DropdownMenuItem onClick={() => router.push("/my-bookings")}>
                    <CalendarDays className="mr-2 h-4 w-4" />
                    My bookings
                  </DropdownMenuItem>
                )}
                {isApproved && (
                  <DropdownMenuItem onClick={() => router.push("/settings")}>
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </DropdownMenuItem>
                )}
                {!isApproved && (
                  <DropdownMenuItem onClick={() => router.push("/awaiting-approval")}>
                    Awaiting approval
                  </DropdownMenuItem>
                )}
                {(isGlobalAdmin || isRoomAdmin) && (
                  <DropdownMenuItem
                    onClick={() => router.push(adminHref)}
                    className={cn(hasPending && "font-semibold")}
                  >
                    {isGlobalAdmin ? "Admin dashboard" : "Booking requests"}
                    <PendingCountBadge count={pending.total} className="ml-auto" />
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem
                  onClick={() => {
                    logout();
                    router.push("/");
                  }}
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>
    </header>
  );
}
