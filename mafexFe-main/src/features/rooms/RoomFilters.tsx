"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { Filter } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { AmenityOut } from "@/lib/types/api";
import { FIND_ROOM_PATH } from "@/lib/routes";
import { isValidTimeRange } from "@/lib/utils/time-params";

const UNIT_TYPES = [
  { value: "", label: "Any unit type" },
  { value: "full_room", label: "Full room" },
  { value: "half_room", label: "Half room" },
  { value: "section", label: "Section" },
  { value: "table", label: "Table" },
];

type FilterValues = {
  date: string;
  start_time: string;
  end_time: string;
  capacity: string;
  unit_type: string;
  amenityIds: number[];
};

function readFilters(sp: URLSearchParams): FilterValues {
  const raw = sp.get("amenities");
  return {
    date: sp.get("date") ?? "",
    start_time: sp.get("start_time") ?? "",
    end_time: sp.get("end_time") ?? "",
    capacity: sp.get("capacity") ?? "",
    unit_type: sp.get("unit_type") ?? "",
    amenityIds: raw
      ? raw
          .split(",")
          .map((s) => parseInt(s, 10))
          .filter((n) => !Number.isNaN(n))
      : [],
  };
}

function hasCompleteTimeRange(filters: FilterValues): boolean {
  return Boolean(filters.date && filters.start_time && filters.end_time);
}

function buildQuery(sp: URLSearchParams, filters: FilterValues): string {
  const p = new URLSearchParams(sp.toString());
  const setOrDelete = (key: string, val: string | null) => {
    if (val && val.trim()) p.set(key, val);
    else p.delete(key);
  };
  setOrDelete("date", filters.date || null);
  setOrDelete("start_time", filters.start_time || null);
  setOrDelete("end_time", filters.end_time || null);
  setOrDelete("capacity", filters.capacity || null);
  setOrDelete("unit_type", filters.unit_type || null);
  if (hasCompleteTimeRange(filters)) p.set("available", "true");
  else p.delete("available");
  const csv = filters.amenityIds.join(",");
  if (csv) p.set("amenities", csv);
  else p.delete("amenities");
  p.set("page", "1");
  return p.toString();
}

export function RoomFilters({ amenities }: { amenities: AmenityOut[] }) {
  const router = useRouter();
  const sp = useSearchParams();
  const [pending, startTransition] = useTransition();
  const [filters, setFilters] = useState<FilterValues>(() => readFilters(sp));

  useEffect(() => {
    setFilters(readFilters(sp));
  }, [sp]);

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const timeFields = [filters.date, filters.start_time, filters.end_time];
    const anyTime = timeFields.some(Boolean);
    const allTime = hasCompleteTimeRange(filters);
    if (anyTime && !allTime) {
      toast.error("Set date, start time, and end time together to filter by availability.");
      return;
    }
    if (allTime && !isValidTimeRange(filters.start_time, filters.end_time)) {
      toast.error("End time must be after start time.");
      return;
    }
    startTransition(() => {
      router.push(`${FIND_ROOM_PATH}?${buildQuery(sp, filters)}`);
    });
  }

  function clearFilters() {
    startTransition(() => {
      router.push(FIND_ROOM_PATH);
    });
  }

  function toggleAmenity(id: number) {
    setFilters((f) => ({
      ...f,
      amenityIds: f.amenityIds.includes(id)
        ? f.amenityIds.filter((x) => x !== id)
        : [...f.amenityIds, id],
    }));
  }

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-lg border bg-card p-4 shadow-sm"
    >
      <div className="mb-3 space-y-1">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Filter className="h-4 w-4" />
          Find available rooms
        </div>
        <p className="text-xs text-muted-foreground">
          Pick a date and time range and unit type to see what you can book.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <div className="space-y-1">
          <Label htmlFor="date">Date</Label>
          <Input
            id="date"
            type="date"
            value={filters.date}
            onChange={(e) => setFilters((f) => ({ ...f, date: e.target.value }))}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="start_time">Start</Label>
          <Input
            id="start_time"
            type="time"
            value={filters.start_time}
            onChange={(e) => setFilters((f) => ({ ...f, start_time: e.target.value }))}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="end_time">End</Label>
          <Input
            id="end_time"
            type="time"
            value={filters.end_time}
            onChange={(e) => setFilters((f) => ({ ...f, end_time: e.target.value }))}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="capacity">Min capacity</Label>
          <Input
            id="capacity"
            type="number"
            min={1}
            placeholder="Any"
            value={filters.capacity}
            onChange={(e) => setFilters((f) => ({ ...f, capacity: e.target.value }))}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="unit_type">Unit type</Label>
          <select
            id="unit_type"
            value={filters.unit_type}
            onChange={(e) => setFilters((f) => ({ ...f, unit_type: e.target.value }))}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            {UNIT_TYPES.map((u) => (
              <option key={u.value || "any"} value={u.value}>
                {u.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-end">
          <Button type="submit" disabled={pending} className="w-full sm:flex-1">
            Apply
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={clearFilters}
            className="w-full sm:flex-1"
          >
            Clear
          </Button>
        </div>
      </div>
      {amenities.length > 0 && (
        <div className="mt-4 border-t pt-4">
          <p className="mb-2 text-sm font-medium">Amenities (match all selected)</p>
          <div className="flex flex-wrap gap-4">
            {amenities.map((a) => (
              <label key={a.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={filters.amenityIds.includes(a.id)}
                  onChange={() => toggleAmenity(a.id)}
                  className="size-4 rounded border-input accent-primary"
                />
                {a.name}
              </label>
            ))}
          </div>
        </div>
      )}
    </form>
  );
}
