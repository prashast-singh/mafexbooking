import type { RoomAvailabilityGrid } from "@/lib/types/api";

export type SlotInterval = {
  start_time: string;
  end_time: string;
};

export type BookingSlotSelection = {
  unit_id: number;
  unit_name: string;
  start_time: string;
  end_time: string;
  slots: SlotInterval[];
};

export function isSlotInSelection(
  selection: BookingSlotSelection | null,
  row: SlotInterval,
  unitId: number,
): boolean {
  if (!selection || selection.unit_id !== unitId) return false;
  return selection.slots.some(
    (s) => s.start_time === row.start_time && s.end_time === row.end_time,
  );
}

export function singleSlotSelection(
  unitId: number,
  unitName: string,
  row: SlotInterval,
): BookingSlotSelection {
  return {
    unit_id: unitId,
    unit_name: unitName,
    start_time: row.start_time,
    end_time: row.end_time,
    slots: [row],
  };
}

/** All grid rows between anchor and target for one unit; null if any cell is unavailable. */
export function rangeSelectionFromGrid(
  grid: RoomAvailabilityGrid,
  unitId: number,
  unitName: string,
  anchor: SlotInterval,
  target: SlotInterval,
): BookingSlotSelection | null {
  const rows = grid.slots;
  const anchorIdx = rows.findIndex(
    (r) => r.start_time === anchor.start_time && r.end_time === anchor.end_time,
  );
  const targetIdx = rows.findIndex(
    (r) => r.start_time === target.start_time && r.end_time === target.end_time,
  );
  if (anchorIdx === -1 || targetIdx === -1) return null;

  const lo = Math.min(anchorIdx, targetIdx);
  const hi = Math.max(anchorIdx, targetIdx);
  const slots: SlotInterval[] = [];

  for (let i = lo; i <= hi; i++) {
    const row = rows[i];
    const unit = row.units.find((u) => u.unit_id === unitId);
    if (!unit?.available) return null;
    slots.push({ start_time: row.start_time, end_time: row.end_time });
  }

  return {
    unit_id: unitId,
    unit_name: unitName,
    start_time: slots[0].start_time,
    end_time: slots[slots.length - 1].end_time,
    slots,
  };
}
