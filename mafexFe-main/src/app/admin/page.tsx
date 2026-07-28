"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/PageHeader";
import { LoadingState } from "@/components/shared/LoadingState";
import { useT } from "@/i18n/use-t";
import { dashboardSummary } from "@/lib/api/admin";
import type { AdminDashboardSummary } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";

export default function AdminDashboardPage() {
  const t = useT();
  const [data, setData] = useState<AdminDashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setData(await dashboardSummary());
      } catch (e) {
        toast.error(formatApiError(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <LoadingState />;

  const s = data ?? {
    pending_approvals: 0,
    rooms_total: 0,
    bookings_today: 0,
    users_total: 0,
  };

  return (
    <div className="space-y-8 p-6">
      <PageHeader title={t("admin.dashboard")} description={t("admin.dashboardDescription")} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("admin.pendingApprovals")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{s.pending_approvals}</p>
            <Link href="/admin/approvals" className="text-xs text-primary underline-offset-4 hover:underline">
              {t("admin.reviewLink")}
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{t("admin.rooms")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{s.rooms_total}</p>
            <Link href="/admin/rooms" className="text-xs text-primary underline-offset-4 hover:underline">
              {t("admin.manageLink")}
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("admin.bookingsToday")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{s.bookings_today}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{t("admin.users")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{s.users_total}</p>
            <Link href="/admin/users" className="text-xs text-primary underline-offset-4 hover:underline">
              {t("admin.directoryLink")}
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
