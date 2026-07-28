"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { useT } from "@/i18n/use-t";
import { approveUser, pendingApprovals, rejectUser } from "@/lib/api/admin";
import type { AdminUserOut } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";

export default function AdminApprovalsPage() {
  const t = useT();
  const [rows, setRows] = useState<AdminUserOut[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await pendingApprovals());
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function approve(id: number) {
    try {
      await approveUser(id);
      toast.success(t("admin.userApproved"));
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function reject(id: number) {
    try {
      await rejectUser(id);
      toast.success(t("admin.userRejected"));
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-8 p-6">
      <PageHeader
        title={t("admin.pendingApprovals")}
        description={t("admin.pendingApprovalsDescription")}
      />
      {rows.length === 0 ? (
        <EmptyState title={t("admin.noPendingUsers")} description={t("admin.noPendingUsersDescription")} />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("common.name")}</TableHead>
                <TableHead>{t("common.email")}</TableHead>
                <TableHead>{t("admin.type")}</TableHead>
                <TableHead className="min-w-[220px]">{t("admin.signupIntent")}</TableHead>
                <TableHead className="text-right">{t("common.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">{u.full_name}</TableCell>
                  <TableCell>{u.email}</TableCell>
                  <TableCell className="capitalize">{u.user_type}</TableCell>
                  <TableCell className="max-w-sm whitespace-pre-wrap text-sm text-muted-foreground">
                    {u.signup_intent?.trim() || "—"}
                  </TableCell>
                  <TableCell className="space-x-2 text-right">
                    <Button size="sm" onClick={() => void approve(u.id)}>
                      {t("admin.approve")}
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => void reject(u.id)}>
                      {t("admin.reject")}
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
