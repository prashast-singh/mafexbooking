"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { createBooking, createBookingSeries, previewBookingSeries } from "@/lib/api/bookings";
import type { BookingSeriesFrequency, BookingSeriesPreviewOut } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";
import type { BookingSlotSelection } from "./booking-selection";

const schema = z.object({
  purpose: z.string().max(500).optional(),
});

type FormValues = z.infer<typeof schema>;

type RepeatPreset = "weekly" | "biweekly" | "every3" | "every4" | "monthly";

const REPEAT_PRESETS: { value: RepeatPreset; label: string; frequency: BookingSeriesFrequency; interval: number }[] = [
  { value: "weekly", label: "Every week", frequency: "weekly", interval: 1 },
  { value: "biweekly", label: "Every 2 weeks", frequency: "weekly", interval: 2 },
  { value: "every3", label: "Every 3 weeks", frequency: "weekly", interval: 3 },
  { value: "every4", label: "Every 4 weeks", frequency: "weekly", interval: 4 },
  { value: "monthly", label: "Every month", frequency: "monthly", interval: 1 },
];

function presetConfig(preset: RepeatPreset) {
  return REPEAT_PRESETS.find((p) => p.value === preset) ?? REPEAT_PRESETS[0];
}

export function BookingForm({
  roomId,
  bookingDate,
  selection,
  canBook,
  onBooked,
}: {
  roomId: number;
  bookingDate: string;
  selection: BookingSlotSelection | null;
  canBook: boolean;
  onBooked?: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [repeatEnabled, setRepeatEnabled] = useState(false);
  const [repeatPreset, setRepeatPreset] = useState<RepeatPreset>("weekly");
  const [endMode, setEndMode] = useState<"count" | "date">("count");
  const [maxOccurrences, setMaxOccurrences] = useState("4");
  const [endDate, setEndDate] = useState("");
  const [preview, setPreview] = useState<BookingSeriesPreviewOut | null>(null);
  const [previewing, setPreviewing] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { purpose: "" },
  });

  function seriesBody(purpose: string | null) {
    if (!selection) throw new Error("No selection");
    const cfg = presetConfig(repeatPreset);
    const count = Number.parseInt(maxOccurrences, 10);
    return {
      room_id: roomId,
      unit_id: selection.unit_id,
      booking_date: bookingDate,
      start_time: selection.start_time,
      end_time: selection.end_time,
      purpose,
      frequency: cfg.frequency,
      interval: cfg.interval,
      end_date: endMode === "date" && endDate ? endDate : null,
      max_occurrences: endMode === "count" && Number.isFinite(count) ? count : null,
    };
  }

  async function onPreview() {
    if (!selection) {
      toast.error("Pick a time range first.");
      return;
    }
    if (endMode === "count") {
      const count = Number.parseInt(maxOccurrences, 10);
      if (!Number.isFinite(count) || count < 1) {
        toast.error("Enter a valid number of occurrences.");
        return;
      }
    } else if (!endDate) {
      toast.error("Pick an end date.");
      return;
    }
    setPreviewing(true);
    try {
      const purpose = form.getValues("purpose")?.trim() || null;
      const result = await previewBookingSeries(seriesBody(purpose));
      setPreview(result);
      if (result.bookable.length === 0) {
        toast.error("No dates are available for this series.");
      }
    } catch (e) {
      toast.error(formatApiError(e));
      setPreview(null);
    } finally {
      setPreviewing(false);
    }
  }

  async function onSubmit(values: FormValues) {
    if (!selection) {
      toast.error("Pick a time range first.");
      return;
    }
    setSubmitting(true);
    try {
      const purpose = values.purpose?.trim() || null;
      if (repeatEnabled) {
        if (!preview || preview.bookable.length === 0) {
          toast.error("Preview the series first to see which dates can be booked.");
          return;
        }
        const result = await createBookingSeries(seriesBody(purpose));
        const hasPending = result.bookings.some((b) => b.status === "pending");
        toast.success(
          hasPending
            ? `Series submitted: ${result.created_count} request(s) awaiting approval${result.skipped_count ? `, ${result.skipped_count} skipped` : ""}.`
            : `Series booked: ${result.created_count} confirmed${result.skipped_count ? `, ${result.skipped_count} skipped` : ""}.`,
        );
        setPreview(null);
      } else {
        const booking = await createBooking({
          room_id: roomId,
          unit_id: selection.unit_id,
          booking_date: bookingDate,
          start_time: selection.start_time,
          end_time: selection.end_time,
          purpose,
        });
        toast.success(
          booking.status === "pending"
            ? "Booking request submitted. A room admin will review it."
            : "Booking confirmed.",
        );
      }
      form.reset();
      setRepeatEnabled(false);
      onBooked?.();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSubmitting(false);
    }
  }

  if (!canBook) {
    return (
      <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm">
        Your account must be approved by an admin before you can book. You can still browse rooms and
        check availability.
      </div>
    );
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
      {selection ? (
        <div className="space-y-1 text-sm text-muted-foreground">
          <p>
            <span className="font-medium text-foreground">{selection.unit_name}</span> ·{" "}
            {selection.start_time.slice(0, 5)} – {selection.end_time.slice(0, 5)}
            {selection.slots.length > 1 && (
              <span> ({selection.slots.length} periods in range)</span>
            )}
          </p>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Select a start and end time to set your range in the grid above, then confirm your booking.
        </p>
      )}

      <div className="space-y-2">
        <Label htmlFor="purpose">Purpose (optional)</Label>
        <Textarea
          id="purpose"
          placeholder="Team sync, interview, focus block…"
          rows={3}
          {...form.register("purpose")}
        />
      </div>

      <div className="flex items-center gap-2">
        <Checkbox
          id="repeat"
          checked={repeatEnabled}
          onCheckedChange={(v) => {
            setRepeatEnabled(v === true);
            setPreview(null);
          }}
        />
        <Label htmlFor="repeat" className="cursor-pointer font-normal">
          Repeat this booking
        </Label>
      </div>

      {repeatEnabled && (
        <div className="space-y-4 rounded-lg border bg-muted/20 p-4">
          <div className="space-y-2">
            <Label>Repeat</Label>
            <Select
              value={repeatPreset}
              onValueChange={(v) => {
                setRepeatPreset(v as RepeatPreset);
                setPreview(null);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {REPEAT_PRESETS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Ends</Label>
            <div className="flex flex-wrap gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="endMode"
                  checked={endMode === "count"}
                  onChange={() => {
                    setEndMode("count");
                    setPreview(null);
                  }}
                />
                After
                <Input
                  type="number"
                  min={1}
                  max={52}
                  className="h-8 w-20"
                  value={maxOccurrences}
                  onChange={(e) => {
                    setMaxOccurrences(e.target.value);
                    setPreview(null);
                  }}
                  disabled={endMode !== "count"}
                />
                occurrences
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="endMode"
                  checked={endMode === "date"}
                  onChange={() => {
                    setEndMode("date");
                    setPreview(null);
                  }}
                />
                On
                <Input
                  type="date"
                  className="h-8 w-40"
                  value={endDate}
                  min={bookingDate}
                  onChange={(e) => {
                    setEndDate(e.target.value);
                    setPreview(null);
                  }}
                  disabled={endMode !== "date"}
                />
              </label>
            </div>
          </div>

          <Button type="button" variant="outline" disabled={previewing || !selection} onClick={() => void onPreview()}>
            {previewing ? "Previewing…" : "Preview dates"}
          </Button>

          {preview && (
            <div className="space-y-2 text-sm">
              <p>
                <span className="font-medium text-foreground">{preview.bookable.length}</span> of{" "}
                {preview.total_candidates} dates can be booked.
              </p>
              {preview.skipped.length > 0 && (
                <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3">
                  <p className="font-medium">Skipped dates</p>
                  <ul className="mt-1 list-inside list-disc text-muted-foreground">
                    {preview.skipped.map((s) => (
                      <li key={s.date}>
                        {s.date} ({s.reason})
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <Button type="submit" disabled={submitting || !selection}>
        {submitting ? "Booking…" : repeatEnabled ? "Confirm series" : "Confirm booking"}
      </Button>
    </form>
  );
}
