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
import { createAmenity, deleteAmenity } from "@/lib/api/admin";
import { listAmenities } from "@/lib/api/amenities";
import type { AmenityOut } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";

export default function AdminAmenitiesPage() {
  const [rows, setRows] = useState<AmenityOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [icon, setIcon] = useState("");
  const [delId, setDelId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await listAmenities());
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
      await createAmenity({ name: name.trim(), icon: icon.trim() || null });
      toast.success("Amenity created.");
      setName("");
      setIcon("");
      void load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  }

  async function confirmDelete() {
    if (delId == null) return;
    try {
      await deleteAmenity(delId);
      toast.success("Amenity deleted.");
      setDelId(null);
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-8 p-6">
      <PageHeader title="Amenities" description="Labels used when filtering rooms." />
      <form onSubmit={onCreate} className="flex max-w-xl flex-wrap items-end gap-3 rounded-lg border p-4">
        <div className="min-w-[160px] flex-1 space-y-1">
          <Label htmlFor="am-name">Name</Label>
          <Input id="am-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Whiteboard" />
        </div>
        <div className="min-w-[120px] flex-1 space-y-1">
          <Label htmlFor="am-icon">Icon hint (optional)</Label>
          <Input id="am-icon" value={icon} onChange={(e) => setIcon(e.target.value)} placeholder="board" />
        </div>
        <Button type="submit">Add</Button>
      </form>
      {rows.length === 0 ? (
        <EmptyState title="No amenities" description="Create tags that rooms can link to." />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Icon</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-medium">{a.name}</TableCell>
                  <TableCell className="text-muted-foreground">{a.icon ?? "—"}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="destructive" onClick={() => setDelId(a.id)}>
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
        title="Delete amenity?"
        description="Rooms linked to it may need to be updated separately."
        confirmLabel="Delete"
        destructive
        onConfirm={confirmDelete}
      />
    </div>
  );
}
