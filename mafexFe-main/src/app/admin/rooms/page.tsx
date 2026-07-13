"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { createRoom } from "@/lib/api/admin";
import { listRooms } from "@/lib/api/rooms";
import type { RoomBrowseItem } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";
import { isValidTimeRange } from "@/lib/utils/time-params";
import { inputTimeToApi } from "@/lib/utils/time-format";

const createSchema = z
  .object({
    name: z.string().min(1),
    booking_mode: z.enum(["full_room_only", "tables_only", "hybrid", "sections_only"]),
    capacity: z.number().int().min(1),
    location: z.string().optional(),
    description: z.string().optional(),
    availability_window_start: z.string().min(1),
    availability_window_end: z.string().min(1),
  })
  .refine(
    (v) => isValidTimeRange(v.availability_window_start, v.availability_window_end),
    { message: "Availability end must be after start", path: ["availability_window_end"] },
  );

export default function AdminRoomsPage() {
  const [rows, setRows] = useState<RoomBrowseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const form = useForm<z.infer<typeof createSchema>>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      name: "",
      booking_mode: "hybrid",
      capacity: 8,
      location: "",
      description: "",
      availability_window_start: "08:00",
      availability_window_end: "20:00",
    },
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const p = await listRooms({ page: 1, limit: 100 });
      setRows(p.items);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onCreate(values: z.infer<typeof createSchema>) {
    try {
      await createRoom({
        name: values.name,
        booking_mode: values.booking_mode,
        capacity: values.capacity,
        location: values.location || null,
        description: values.description || null,
        availability_window_start: inputTimeToApi(values.availability_window_start),
        availability_window_end: inputTimeToApi(values.availability_window_end),
        is_active: true,
      });
      toast.success("Room created.");
      setOpen(false);
      form.reset();
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-8 p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <PageHeader title="Rooms" description="Create and manage bookable spaces." />
        <Dialog open={open} onOpenChange={setOpen}>
          <Button type="button" onClick={() => setOpen(true)}>
            New room
          </Button>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>New room</DialogTitle>
            </DialogHeader>
            <form onSubmit={form.handleSubmit(onCreate)} className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="name">Name</Label>
                <Input id="name" {...form.register("name")} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="booking_mode">Booking mode</Label>
                <select
                  id="booking_mode"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                  {...form.register("booking_mode")}
                >
                  <option value="full_room_only">Full room only</option>
                  <option value="tables_only">Tables only</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="sections_only">Sections only</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="capacity">Capacity</Label>
                <Input
                  id="capacity"
                  type="number"
                  min={1}
                  {...form.register("capacity", { valueAsNumber: true })}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="location">Location</Label>
                <Input id="location" {...form.register("location")} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="description">Description</Label>
                <Input id="description" {...form.register("description")} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="availability_window_start">Available from</Label>
                  <Input
                    id="availability_window_start"
                    type="time"
                    {...form.register("availability_window_start")}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="availability_window_end">Available until</Label>
                  <Input
                    id="availability_window_end"
                    type="time"
                    {...form.register("availability_window_end")}
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Daily bookable hours for this room (slot grid and bookings).
              </p>
              <Button type="submit" className="w-full">
                Create
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>
      {rows.length === 0 ? (
        <EmptyState title="No rooms" description="Create your first room to get started." />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Capacity</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Edit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell className="capitalize text-muted-foreground">
                    {r.booking_mode.replace(/_/g, " ")}
                  </TableCell>
                  <TableCell>{r.capacity}</TableCell>
                  <TableCell>
                    <StatusBadge value={r.is_active ? "active" : "inactive"} />
                  </TableCell>
                  <TableCell className="text-right">
                    <Link
                      href={`/admin/rooms/${r.id}`}
                      className={cn(buttonVariants({ size: "sm", variant: "outline" }))}
                    >
                      Edit
                    </Link>
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
