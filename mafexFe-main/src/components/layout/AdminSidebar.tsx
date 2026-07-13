"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Armchair,
  Building2,
  CalendarDays,
  ClipboardList,
  LayoutDashboard,
  Tags,
  Users,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/hooks/use-auth";

const globalAdminLinks = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/approvals", label: "Approvals", icon: ClipboardList },
  { href: "/admin/booking-requests", label: "Booking requests", icon: ClipboardList },
  { href: "/admin/bookings", label: "Bookings", icon: CalendarDays },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/rooms", label: "Rooms", icon: Building2 },
  { href: "/admin/amenities", label: "Amenities", icon: Tags },
];

const roomAdminLinks = [
  { href: "/admin/booking-requests", label: "Booking requests", icon: ClipboardList },
  { href: "/admin/bookings", label: "Bookings", icon: CalendarDays },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const links = user?.role === "admin" ? globalAdminLinks : roomAdminLinks;

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r bg-muted/30">
      <div className="flex h-14 items-center border-b px-4">
        <Link href={user?.role === "admin" ? "/admin" : "/admin/booking-requests"} className="flex items-center gap-2 text-sm font-semibold">
          <Armchair className="h-5 w-5" />
          {user?.role === "admin" ? "Admin" : "Room admin"}
        </Link>
      </div>
      <nav className="flex flex-col gap-1 p-2">
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/admin" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                buttonVariants({ variant: active ? "secondary" : "ghost", size: "sm" }),
                "justify-start",
                active && "bg-background shadow-sm",
              )}
            >
              <Icon className="mr-2 h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <Separator className="mt-auto" />
      <div className="p-2">
        <Link
          href="/findroom"
          className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "w-full justify-start")}
        >
          ← Back to site
        </Link>
      </div>
    </aside>
  );
}
