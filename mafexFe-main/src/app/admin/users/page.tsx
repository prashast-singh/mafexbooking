"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import {
  deleteAdminUser,
  listAdminUsers,
  listUserEmailHistory,
  patchUserRole,
  patchUserStatus,
  patchUserTags,
} from "@/lib/api/admin";
import { listTags } from "@/lib/api/tags";
import type { AdminUserOut, TagOut, UserEmailHistoryOut } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";

function accountStatusLabel(user: AdminUserOut): string {
  if (!user.is_active) return "Inactive";
  if (user.deactivate_at) {
    const at = new Date(user.deactivate_at);
    if (at.getTime() > Date.now()) {
      return `Active until ${at.toLocaleString()}`;
    }
  }
  return "Active";
}

export default function AdminUsersPage() {
  const [rows, setRows] = useState<AdminUserOut[]>([]);
  const [allTags, setAllTags] = useState<TagOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [historyByUser, setHistoryByUser] = useState<Record<number, UserEmailHistoryOut[]>>({});
  const [loadingHistoryId, setLoadingHistoryId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminUserOut | null>(null);
  const [scheduleUserId, setScheduleUserId] = useState<number | null>(null);
  const [scheduleDate, setScheduleDate] = useState("");
  const [scheduleTime, setScheduleTime] = useState("23:59");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await listAdminUsers({ limit: 100 }));
      setAllTags(await listTags());
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

  async function deactivateUser(id: number) {
    try {
      await patchUserStatus(id, { is_active: false });
      toast.success("User deactivated.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function reactivateUser(id: number) {
    try {
      await patchUserStatus(id, { is_active: true, deactivate_at: null });
      toast.success("User reactivated.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function applySchedule(userId: number) {
    if (!scheduleDate) {
      toast.error("Pick a date.");
      return;
    }
    const iso = `${scheduleDate}T${scheduleTime}:00`;
    try {
      await patchUserStatus(userId, { deactivate_at: new Date(iso).toISOString() });
      toast.success("Deactivation scheduled.");
      setScheduleUserId(null);
      setScheduleDate("");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function clearSchedule(userId: number) {
    try {
      await patchUserStatus(userId, { deactivate_at: null });
      toast.success("Schedule cleared.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    try {
      await deleteAdminUser(deleteTarget.id);
      toast.success("User deleted.");
      setDeleteTarget(null);
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function toggleUserTag(user: AdminUserOut, tagId: number, checked: boolean) {
    const current = user.tag_ids ?? [];
    const next = checked ? [...new Set([...current, tagId])] : current.filter((id) => id !== tagId);
    try {
      await patchUserTags(user.id, next);
      setRows((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, tag_ids: next } : u)),
      );
      toast.success("Tags updated.");
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
      <PageHeader title="Users" description="Directory, roles, account status, and tags." />
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Approval</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Account</TableHead>
              <TableHead>Tags</TableHead>
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
                  <TableCell className="text-sm">
                    <StatusBadge value={u.is_active ? "active" : "inactive"} />
                    <div className="mt-1 text-xs text-muted-foreground">{accountStatusLabel(u)}</div>
                  </TableCell>
                  <TableCell className="max-w-[220px]">
                    <div className="flex flex-wrap gap-2">
                      {allTags.map((t) => {
                        const on = (u.tag_ids ?? []).includes(t.id);
                        return (
                          <label key={t.id} className="flex items-center gap-1 text-xs">
                            <input
                              type="checkbox"
                              checked={on}
                              onChange={(e) => void toggleUserTag(u, t.id, e.target.checked)}
                            />
                            {t.name}
                          </label>
                        );
                      })}
                      {allTags.length === 0 && <span className="text-xs text-muted-foreground">—</span>}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex flex-wrap justify-end gap-2">
                      <Button size="sm" variant="ghost" onClick={() => void toggleHistory(u)}>
                        {expandedId === u.id ? "Hide history" : "History"}
                      </Button>
                      {u.is_active ? (
                        <Button size="sm" variant="outline" onClick={() => void deactivateUser(u.id)}>
                          Deactivate
                        </Button>
                      ) : (
                        <Button size="sm" variant="outline" onClick={() => void reactivateUser(u.id)}>
                          Reactivate
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setScheduleUserId(scheduleUserId === u.id ? null : u.id);
                          setScheduleDate("");
                        }}
                      >
                        Schedule
                      </Button>
                      {u.deactivate_at && (
                        <Button size="sm" variant="ghost" onClick={() => void clearSchedule(u.id)}>
                          Clear schedule
                        </Button>
                      )}
                      {u.role === "admin" ? (
                        <Button size="sm" variant="outline" onClick={() => void setRole(u.id, "user")}>
                          Make user
                        </Button>
                      ) : (
                        <Button size="sm" variant="outline" onClick={() => void setRole(u.id, "admin")}>
                          Make admin
                        </Button>
                      )}
                      <Button size="sm" variant="destructive" onClick={() => setDeleteTarget(u)}>
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
                {scheduleUserId === u.id && (
                  <TableRow>
                    <TableCell colSpan={7} className="bg-muted/20">
                      <div className="flex flex-wrap items-end gap-3 py-2">
                        <div className="space-y-1">
                          <Label htmlFor={`sched-date-${u.id}`}>Deactivate on</Label>
                          <Input
                            id={`sched-date-${u.id}`}
                            type="date"
                            value={scheduleDate}
                            onChange={(e) => setScheduleDate(e.target.value)}
                          />
                        </div>
                        <div className="space-y-1">
                          <Label htmlFor={`sched-time-${u.id}`}>Time</Label>
                          <Input
                            id={`sched-time-${u.id}`}
                            type="time"
                            value={scheduleTime}
                            onChange={(e) => setScheduleTime(e.target.value)}
                          />
                        </div>
                        <Button size="sm" onClick={() => void applySchedule(u.id)}>
                          Set schedule
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )}
                {expandedId === u.id && (
                  <TableRow>
                    <TableCell colSpan={7} className="bg-muted/30">
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

      <ConfirmDialog
        open={deleteTarget != null}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title="Delete user permanently?"
        description={
          deleteTarget
            ? `This permanently deletes ${deleteTarget.full_name} (${deleteTarget.email}) and all their bookings and series. This cannot be undone.`
            : undefined
        }
        confirmLabel="Delete user"
        destructive
        onConfirm={confirmDelete}
      />
    </div>
  );
}
