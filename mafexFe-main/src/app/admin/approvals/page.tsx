"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { approveUser, pendingApprovals, rejectUser } from "@/lib/api/admin";
import type { AdminUserOut } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";

export default function AdminApprovalsPage() {
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
      toast.success("User approved.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function reject(id: number) {
    try {
      await rejectUser(id);
      toast.success("User rejected.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-8 p-6">
      <PageHeader title="Pending approvals" description="Approve or reject new signups." />
      {rows.length === 0 ? (
        <EmptyState title="No pending users" description="New signups will appear here." />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">{u.full_name}</TableCell>
                  <TableCell>{u.email}</TableCell>
                  <TableCell className="capitalize">{u.user_type}</TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button size="sm" onClick={() => void approve(u.id)}>
                      Approve
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => void reject(u.id)}>
                      Reject
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
