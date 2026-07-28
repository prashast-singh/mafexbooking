"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { useT } from "@/i18n/use-t";
import { getBookingPolicy, patchBookingPolicy } from "@/lib/api/admin";
import { formatApiError } from "@/lib/utils/errors";

export default function AdminBookingPolicyPage() {
  const t = useT();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [slotMinutes, setSlotMinutes] = useState(30);
  const [maxHoursPerDay, setMaxHoursPerDay] = useState(8);
  const [maxAdvanceDays, setMaxAdvanceDays] = useState(30);
  const [cancellationCutoff, setCancellationCutoff] = useState(60);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const policy = await getBookingPolicy();
      setSlotMinutes(policy.slot_minutes);
      setMaxHoursPerDay(policy.max_booking_hours_per_day);
      setMaxAdvanceDays(policy.max_advance_days);
      setCancellationCutoff(policy.cancellation_cutoff_minutes);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await patchBookingPolicy({
        slot_minutes: slotMinutes,
        max_booking_hours_per_day: maxHoursPerDay,
        max_advance_days: maxAdvanceDays,
        cancellation_cutoff_minutes: cancellationCutoff,
      });
      setSlotMinutes(updated.slot_minutes);
      setMaxHoursPerDay(updated.max_booking_hours_per_day);
      setMaxAdvanceDays(updated.max_advance_days);
      setCancellationCutoff(updated.cancellation_cutoff_minutes);
      toast.success(t("admin.policySaved"));
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-8 p-6">
      <PageHeader
        title={t("admin.bookingPolicyTitle")}
        description={t("admin.bookingPolicyDescription")}
      />
      <form onSubmit={onSave} className="max-w-xl space-y-4 rounded-lg border p-4">
        <div className="space-y-1">
          <Label htmlFor="slot-minutes">{t("admin.slotMinutes")}</Label>
          <Input
            id="slot-minutes"
            type="number"
            min={15}
            max={120}
            value={slotMinutes}
            onChange={(e) => setSlotMinutes(Number.parseInt(e.target.value, 10) || 15)}
          />
          <p className="text-xs text-muted-foreground">{t("admin.slotMinutesHint")}</p>
        </div>
        <div className="space-y-1">
          <Label htmlFor="max-hours">{t("admin.maxHoursPerDay")}</Label>
          <Input
            id="max-hours"
            type="number"
            min={1}
            max={24}
            value={maxHoursPerDay}
            onChange={(e) => setMaxHoursPerDay(Number.parseInt(e.target.value, 10) || 1)}
          />
          <p className="text-xs text-muted-foreground">{t("admin.maxHoursPerDayHint")}</p>
        </div>
        <div className="space-y-1">
          <Label htmlFor="max-advance">{t("admin.maxAdvanceDays")}</Label>
          <Input
            id="max-advance"
            type="number"
            min={1}
            max={365}
            value={maxAdvanceDays}
            onChange={(e) => setMaxAdvanceDays(Number.parseInt(e.target.value, 10) || 1)}
          />
          <p className="text-xs text-muted-foreground">{t("admin.maxAdvanceDaysHint")}</p>
        </div>
        <div className="space-y-1">
          <Label htmlFor="cancel-cutoff">{t("admin.cancellationCutoff")}</Label>
          <Input
            id="cancel-cutoff"
            type="number"
            min={0}
            max={10080}
            value={cancellationCutoff}
            onChange={(e) => setCancellationCutoff(Number.parseInt(e.target.value, 10) || 0)}
          />
          <p className="text-xs text-muted-foreground">{t("admin.cancellationCutoffHint")}</p>
        </div>
        <Button type="submit" disabled={saving}>
          {saving ? t("common.saving") : t("admin.savePolicy")}
        </Button>
      </form>
    </div>
  );
}
