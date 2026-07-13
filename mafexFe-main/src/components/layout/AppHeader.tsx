"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Building2, CalendarDays, LayoutDashboard, LogIn, LogOut, Settings, UserPlus } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { FIND_ROOM_PATH } from "@/lib/routes";
import { useAuth } from "@/hooks/use-auth";

const nav = [
  { href: FIND_ROOM_PATH, label: "Rooms" },
  { href: "/my-bookings", label: "My bookings", auth: true },
];

export function AppHeader() {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isGlobalAdmin = user?.role === "admin";
  const isRoomAdmin = (user?.managed_room_ids?.length ?? 0) > 0;
  const adminHref = isGlobalAdmin ? "/admin" : "/admin/booking-requests";
  const adminLabel = isGlobalAdmin ? "Admin" : "Room admin";

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4">
        <Link href={user ? FIND_ROOM_PATH : "/login"} className="flex items-center gap-2 font-semibold">
          <Building2 className="h-5 w-5" />
          Mafex Rooms
        </Link>
        <nav className="hidden items-center gap-1 sm:flex">
          {nav.map((item) => {
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
              )}
            >
              <LayoutDashboard className="mr-1 h-4 w-4" />
              {adminLabel}
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
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem disabled className="text-xs text-muted-foreground">
                  {user.email}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push("/my-bookings")}>
                  <CalendarDays className="mr-2 h-4 w-4" />
                  My bookings
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push("/settings")}>
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </DropdownMenuItem>
                {(isGlobalAdmin || isRoomAdmin) && (
                  <DropdownMenuItem onClick={() => router.push(adminHref)}>
                    {isGlobalAdmin ? "Admin dashboard" : "Booking requests"}
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
