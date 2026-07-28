"use client";

import { useEffect, useRef } from "react";
import { toast } from "sonner";

import { useT } from "@/i18n/use-t";
import { cn } from "@/lib/utils";
import type { RoomAvailabilityGrid } from "@/lib/types/api";
import {
  isSlotInSelection,
  rangeSelectionFromGrid,
  singleSlotSelection,
  type BookingSlotSelection,
  type SlotInterval,
} from "./booking-selection";

export type { BookingSlotSelection, SlotInterval };

type AvailabilityGridProps = {
  grid: RoomAvailabilityGrid | null;
  loading?: boolean;
  selected: BookingSlotSelection | null;
  onSelect: (s: BookingSlotSelection | null) => void;
};

export function AvailabilityGrid({ grid, loading, selected, onSelect }: AvailabilityGridProps) {
  const t = useT();
  const rangeAnchorRef = useRef<{
    unit_id: number;
    unit_name: string;
    slot: SlotInterval;
  } | null>(null);

  useEffect(() => {
    if (!selected) rangeAnchorRef.current = null;
  }, [selected]);

  function handleSlotClick(
    row: SlotInterval,
    unitId: number,
    unitName: string,
  ) {
    if (!grid) return;

    const anchor = rangeAnchorRef.current;
    const alreadySelected =
      selected &&
      selected.unit_id === unitId &&
      isSlotInSelection(selected, row, unitId) &&
      selected.slots.length === 1;

    if (alreadySelected) {
      rangeAnchorRef.current = null;
      onSelect(null);
      return;
    }

    if (!anchor || anchor.unit_id !== unitId) {
      rangeAnchorRef.current = { unit_id: unitId, unit_name: unitName, slot: row };
      onSelect(singleSlotSelection(unitId, unitName, row));
      return;
    }

    const sameAsAnchor =
      anchor.slot.start_time === row.start_time && anchor.slot.end_time === row.end_time;
    if (sameAsAnchor) {
      return;
    }

    const range = rangeSelectionFromGrid(grid, unitId, unitName, anchor.slot, row);
    if (!range) {
      toast.error(t("availability.rangeUnavailable"));
      rangeAnchorRef.current = { unit_id: unitId, unit_name: unitName, slot: row };
      onSelect(singleSlotSelection(unitId, unitName, row));
      return;
    }

    rangeAnchorRef.current = { unit_id: unitId, unit_name: unitName, slot: row };
    onSelect(range);
  }

  if (loading) {
    return <p className="text-sm text-muted-foreground">{t("availability.loading")}</p>;
  }
  if (!grid || grid.slots.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("availability.empty")}</p>;
  }

  const instruction = !selected
    ? t("availability.selectStart")
    : selected.slots.length === 1
      ? t("availability.selectEnd")
      : t("availability.rangeSelected", {
          start: selected.start_time.slice(0, 5),
          end: selected.end_time.slice(0, 5),
        });

  return (
    <div className="space-y-2">
      <p className="rounded-md border border-dashed bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{t("availability.timeRange")}</span>{" "}
        {instruction}
      </p>
      <div className="overflow-x-auto rounded-lg border">
      <table className="w-full min-w-[480px] border-collapse text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-3 py-2 text-left font-medium">{t("availability.time")}</th>
            {grid.slots[0]?.units.map((u) => (
              <th key={u.unit_id} className="px-2 py-2 text-center font-medium">
                <div className="max-w-[120px] truncate" title={u.unit_name}>
                  {u.unit_name}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grid.slots.map((row) => (
            <tr key={`${row.start_time}-${row.end_time}`} className="border-b last:border-0">
              <td className="whitespace-nowrap px-3 py-2 text-muted-foreground">
                {row.start_time.slice(0, 5)} – {row.end_time.slice(0, 5)}
              </td>
              {row.units.map((u) => {
                const isSel = isSlotInSelection(selected, row, u.unit_id);
                return (
                  <td key={u.unit_id} className="px-1 py-1 text-center">
                    {u.available ? (
                      <button
                        type="button"
                        onClick={() => handleSlotClick(row, u.unit_id, u.unit_name)}
                        className={cn(
                          "w-full rounded-md px-2 py-1.5 text-xs font-medium transition-colors",
                          isSel
                            ? "bg-primary text-primary-foreground"
                            : "bg-emerald-500/15 text-emerald-800 hover:bg-emerald-500/25 dark:text-emerald-200",
                        )}
                      >
                        {isSel ? t("availability.selected") : t("availability.free")}
                      </button>
                    ) : (
                      <span
                        className="block rounded-md bg-muted px-2 py-1.5 text-xs text-muted-foreground"
                        title={u.reason ?? t("availability.unavailable")}
                      >
                        —
                      </span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="border-t bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
        {t("availability.windowHint", {
          start: grid.availability_window_start.slice(0, 5),
          end: grid.availability_window_end.slice(0, 5),
          minutes: grid.slot_minutes,
        })}
      </p>
      </div>
    </div>
  );
}
