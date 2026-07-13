"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { adminRescheduleBookingSeries, adminUpdateBooking } from "@/lib/api/admin";
import { rescheduleBookingSeries, updateBooking } from "@/lib/api/bookings";
import { getRoom } from "@/lib/api/rooms";
import type { BookableUnitPublic } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";
import { apiTimeToInput, inputTimeToApi } from "@/lib/utils/time-format";

export type RescheduleScope = "this_occurrence" | "all_future" | "from_date";

export type RescheduleTarget = {
  bookingId: number;
  roomId: number;
  unitId: number;
  bookingDate: string;
  startTime: string;
  endTime: string;
  purpose: string | null;
  mode: "user" | "admin";
  seriesId?: number | null;
};

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  target: RescheduleTarget | null;
  onSaved: () => void;
};

export function RescheduleBookingDialog({ open, onOpenChange, target, onSaved }: Props) {
  const [units, setUnits] = useState<BookableUnitPublic[]>([]);
  const [loadingUnits, setLoadingUnits] = useState(false);
  const [saving, setSaving] = useState(false);
  const [bookingDate, setBookingDate] = useState("");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [unitId, setUnitId] = useState("");
  const [purpose, setPurpose] = useState("");
  const [scope, setScope] = useState<RescheduleScope>("this_occurrence");

  const inSeries = target?.seriesId != null;

  useEffect(() => {
    if (!open || !target) return;
    setBookingDate(target.bookingDate);
    setStartTime(apiTimeToInput(target.startTime, "09:00"));
    setEndTime(apiTimeToInput(target.endTime, "10:00"));
    setUnitId(String(target.unitId));
    setPurpose(target.purpose ?? "");
    setScope("this_occurrence");
    setLoadingUnits(true);
    void getRoom(target.roomId)
      .then((room) => setUnits(room.bookable_units.filter((u) => u.is_active)))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => setLoadingUnits(false));
  }, [open, target]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!target) return;
    const uid = Number.parseInt(unitId, 10);
    if (!Number.isFinite(uid)) {
      toast.error("Select a unit.");
      return;
    }
    setSaving(true);
    try {
      const timeBody = {
        unit_id: uid,
        start_time: inputTimeToApi(startTime),
        end_time: inputTimeToApi(endTime),
        purpose: purpose.trim() || null,
      };

      if (inSeries && scope !== "this_occurrence" && target.seriesId != null) {
        const bulkBody = {
          anchor_booking_id: target.bookingId,
          scope: scope === "all_future" ? ("all_future" as const) : ("from_date" as const),
          ...timeBody,
        };
        if (target.mode === "admin") {
          await adminRescheduleBookingSeries(target.seriesId, bulkBody);
        } else {
          await rescheduleBookingSeries(target.seriesId, bulkBody);
        }
        toast.success("Series bookings updated.");
      } else {
        const body = {
          ...timeBody,
          booking_date: bookingDate,
        };
        if (target.mode === "admin") {
          await adminUpdateBooking(target.bookingId, body);
        } else {
          await updateBooking(target.bookingId, body);
        }
        toast.success("Booking updated.");
      }
      onOpenChange(false);
      onSaved();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Reschedule booking</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          {inSeries && (
            <div className="space-y-2">
              <Label>Apply changes to</Label>
              <div className="space-y-2 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="reschedule-scope"
                    checked={scope === "this_occurrence"}
                    onChange={() => setScope("this_occurrence")}
                  />
                  This occurrence only
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="reschedule-scope"
                    checked={scope === "all_future"}
                    onChange={() => setScope("all_future")}
                  />
                  All future in series
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="reschedule-scope"
                    checked={scope === "from_date"}
                    onChange={() => setScope("from_date")}
                  />
                  From this date onward
                </label>
              </div>
              <Alert>
                <AlertDescription className="text-xs">
                  {scope === "this_occurrence"
                    ? "Changing the date removes this occurrence from the series. Changing unit or time updates only this row."
                    : "Each occurrence keeps its scheduled date. Time, unit, and purpose apply to the selected bookings."}
                </AlertDescription>
              </Alert>
            </div>
          )}

          {(!inSeries || scope === "this_occurrence") && (
            <div className="space-y-1">
              <Label htmlFor="rs-date">Date</Label>
              <Input
                id="rs-date"
                type="date"
                value={bookingDate}
                onChange={(e) => setBookingDate(e.target.value)}
                required
              />
            </div>
          )}

          {inSeries && scope !== "this_occurrence" && (
            <p className="text-xs text-muted-foreground">
              Scheduled dates are unchanged; only time, unit, and purpose are updated.
            </p>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="rs-start">Start</Label>
              <Input
                id="rs-start"
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="rs-end">End</Label>
              <Input
                id="rs-end"
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="space-y-1">
            <Label htmlFor="rs-unit">Unit</Label>
            <select
              id="rs-unit"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              value={unitId}
              onChange={(e) => setUnitId(e.target.value)}
              disabled={loadingUnits}
              required
            >
              {units.map((u) => (
                <option key={u.id} value={String(u.id)}>
                  {u.name} ({u.booking_mode})
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="rs-purpose">Purpose</Label>
            <Input
              id="rs-purpose"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              placeholder="Optional"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
