"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { useT } from "@/i18n/use-t";
import { getHouseRules, patchHouseRules } from "@/lib/api/admin";
import { formatApiError } from "@/lib/utils/errors";

export default function AdminHouseRulesPage() {
  const t = useT();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [content, setContent] = useState("");
  const [version, setVersion] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rules = await getHouseRules();
      setContent(rules.content ?? "");
      setVersion(rules.version);
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
      const updated = await patchHouseRules({ content });
      setContent(updated.content ?? "");
      setVersion(updated.version);
      toast.success(
        updated.version !== version
          ? t("admin.houseRulesSavedBump", { version: updated.version })
          : t("admin.houseRulesSaved"),
      );
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
        title={t("admin.houseRulesTitle")}
        description={t("admin.houseRulesDescription")}
      />
      <form onSubmit={onSave} className="max-w-2xl space-y-4 rounded-lg border p-4">
        <p className="text-xs text-muted-foreground">{t("admin.currentVersion", { version })}</p>
        <div className="space-y-1">
          <Label htmlFor="house-rules-content">{t("admin.rulesText")}</Label>
          <Textarea
            id="house-rules-content"
            rows={16}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={t("admin.houseRulesPlaceholder")}
            className="min-h-[280px] font-mono text-sm"
          />
        </div>
        <Button type="submit" disabled={saving}>
          {saving ? t("common.saving") : t("admin.saveHouseRules")}
        </Button>
      </form>
    </div>
  );
}
