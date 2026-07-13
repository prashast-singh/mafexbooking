"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { listAdminUsers, listUserEmailHistory, patchUserRole } from "@/lib/api/admin";
import type { AdminUserOut, UserEmailHistoryOut } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";

export default function AdminUsersPage() {
  const [rows, setRows] = useState<AdminUserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [historyByUser, setHistoryByUser] = useState<Record<number, UserEmailHistoryOut[]>>({});
  const [loadingHistoryId, setLoadingHistoryId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await listAdminUsers({ limit: 100 }));
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function setRole(id: number, role: "user" | "admin") {
    try {
      await patchUserRole(id, role);
      toast.success("Role updated.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function toggleHistory(user: AdminUserOut) {
    if (expandedId === user.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(user.id);
    if (historyByUser[user.id]) return;
    setLoadingHistoryId(user.id);
    try {
      const history = await listUserEmailHistory(user.id);
      setHistoryByUser((prev) => ({ ...prev, [user.id]: history }));
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoadingHistoryId(null);
    }
  }

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-8 p-6">
      <PageHeader title="Users" description="Directory, roles, and email history." />
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Approval</TableHead>
              <TableHead>Role</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((u) => (
              <Fragment key={u.id}>
                <TableRow>
                  <TableCell className="font-medium">{u.full_name}</TableCell>
                  <TableCell>{u.email}</TableCell>
                  <TableCell>
                    <StatusBadge value={u.approval_status} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge value={u.role} />
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button size="sm" variant="ghost" onClick={() => void toggleHistory(u)}>
                      {expandedId === u.id ? "Hide history" : "Email history"}
                    </Button>
                    {u.role === "admin" ? (
                      <Button size="sm" variant="outline" onClick={() => void setRole(u.id, "user")}>
                        Make user
                      </Button>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => void setRole(u.id, "admin")}>
                        Make admin
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
                {expandedId === u.id && (
                  <TableRow>
                    <TableCell colSpan={5} className="bg-muted/30">
                      {loadingHistoryId === u.id ? (
                        <p className="text-sm text-muted-foreground">Loading email history…</p>
                      ) : (
                        <div className="space-y-2 py-2">
                          <p className="text-sm">
                            <span className="font-medium">Current:</span> {u.email}
                          </p>
                          {(historyByUser[u.id] ?? []).length === 0 ? (
                            <p className="text-sm text-muted-foreground">No previous emails recorded.</p>
                          ) : (
                            <ul className="text-sm space-y-1">
                              {(historyByUser[u.id] ?? []).map((h) => (
                                <li key={h.id}>
                                  {h.email}{" "}
                                  <span className="text-muted-foreground">
                                    (changed {h.changed_at.slice(0, 10)})
                                  </span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
