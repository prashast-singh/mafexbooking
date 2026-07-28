"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Building2,
  CalendarDays,
  ClipboardList,
  LayoutDashboard,
  ScrollText,
  Settings2,
  Tag,
  Tags,
  Users,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { LanguageSwitcher } from "@/components/shared/LanguageSwitcher";
import { PendingCountBadge } from "@/components/shared/PendingCountBadge";
import { useAdminPendingCounts } from "@/hooks/use-admin-pending-counts";
import { useAuth } from "@/hooks/use-auth";
import { useT } from "@/i18n/use-t";

export function AdminSidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const pending = useAdminPendingCounts();
  const t = useT();

  const globalAdminLinks = [
    { href: "/admin", label: t("admin.dashboard"), icon: LayoutDashboard },
    { href: "/admin/approvals", label: t("admin.approvals"), icon: ClipboardList, badgeKey: "approvals" as const },
    {
      href: "/admin/booking-requests",
      label: t("admin.bookingRequests"),
      icon: ClipboardList,
      badgeKey: "bookings" as const,
    },
    { href: "/admin/bookings", label: t("admin.bookings"), icon: CalendarDays },
    { href: "/admin/users", label: t("admin.users"), icon: Users },
    { href: "/admin/rooms", label: t("admin.rooms"), icon: Building2 },
    { href: "/admin/amenities", label: t("admin.amenities"), icon: Tags },
    { href: "/admin/tags", label: t("admin.tags"), icon: Tag },
    { href: "/admin/booking-policy", label: t("admin.bookingPolicy"), icon: Settings2 },
    { href: "/admin/house-rules", label: t("admin.houseRules"), icon: ScrollText },
  ];

  const roomAdminLinks = [
    {
      href: "/admin/booking-requests",
      label: t("admin.bookingRequests"),
      icon: ClipboardList,
      badgeKey: "bookings" as const,
    },
    { href: "/admin/bookings", label: t("admin.bookings"), icon: CalendarDays },
  ];

  const links = user?.role === "admin" ? globalAdminLinks : roomAdminLinks;

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r bg-muted/30">
      <div className="flex h-14 items-center justify-between gap-2 border-b px-3">
        <Link
          href={user?.role === "admin" ? "/admin" : "/admin/booking-requests"}
          className="flex min-w-0 items-center gap-2 text-sm font-semibold"
        >
          <Image
            src="/mafex-logo.png"
            alt="MAFEX"
            width={24}
            height={24}
            className="h-6 w-6 shrink-0 rounded-sm object-contain"
            unoptimized
            priority
          />
          <span className="truncate">{t("common.workspace")}</span>
        </Link>
        <LanguageSwitcher />
      </div>
      <nav className="flex flex-col gap-1 p-2">
        {links.map(({ href, label, icon: Icon, ...rest }) => {
          const active = pathname === href || (href !== "/admin" && pathname.startsWith(href));
          const badgeKey = "badgeKey" in rest ? rest.badgeKey : undefined;
          const badgeCount =
            badgeKey === "approvals"
              ? pending.pending_approvals
              : badgeKey === "bookings"
                ? pending.pending_booking_requests
                : 0;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                buttonVariants({ variant: active ? "secondary" : "ghost", size: "sm" }),
                "justify-start",
                active && "bg-background shadow-sm",
                badgeCount > 0 && "font-semibold",
              )}
            >
              <Icon className="mr-2 h-4 w-4 shrink-0" />
              <span className="truncate">{label}</span>
              <PendingCountBadge count={badgeCount} className="ml-auto" />
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
          {t("common.backToSite")}
        </Link>
      </div>
    </aside>
  );
}
