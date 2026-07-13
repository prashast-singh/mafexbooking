"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { createTag, deleteTag } from "@/lib/api/admin";
import { listTags } from "@/lib/api/tags";
import type { TagOut } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";

export default function AdminTagsPage() {
  const [rows, setRows] = useState<TagOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [delId, setDelId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await listTags());
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await createTag({ name: name.trim(), description: description.trim() || null });
      toast.success("Tag created.");
      setName("");
      setDescription("");
      void load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  }

  async function confirmDelete() {
    if (delId == null) return;
    try {
      await deleteTag(delId);
      toast.success("Tag deleted.");
      setDelId(null);
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-8 p-6">
      <PageHeader
        title="Tags"
        description="Restrict room visibility: tagged users only see rooms with matching tags."
      />
      <form onSubmit={onCreate} className="flex max-w-xl flex-wrap items-end gap-3 rounded-lg border p-4">
        <div className="min-w-[160px] flex-1 space-y-1">
          <Label htmlFor="tag-name">Name</Label>
          <Input id="tag-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Physics" />
        </div>
        <div className="min-w-[200px] flex-1 space-y-1">
          <Label htmlFor="tag-desc">Description (optional)</Label>
          <Input
            id="tag-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Department or group"
          />
        </div>
        <Button type="submit">Add</Button>
      </form>
      {rows.length === 0 ? (
        <EmptyState title="No tags" description="Create tags and assign them to users and rooms." />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((t) => (
                <TableRow key={t.id}>
                  <TableCell className="font-medium">{t.name}</TableCell>
                  <TableCell className="text-muted-foreground">{t.description ?? "—"}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="destructive" onClick={() => setDelId(t.id)}>
                      Delete
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <ConfirmDialog
        open={delId != null}
        onOpenChange={(o) => !o && setDelId(null)}
        title="Delete tag?"
        description="Users and rooms linked to this tag will be updated."
        confirmLabel="Delete"
        destructive
        onConfirm={confirmDelete}
      />
    </div>
  );
}
