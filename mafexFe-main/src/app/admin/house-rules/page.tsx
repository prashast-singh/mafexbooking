"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { getHouseRules, patchHouseRules } from "@/lib/api/admin";
import { formatApiError } from "@/lib/utils/errors";

export default function AdminHouseRulesPage() {
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
          ? `House rules saved (version ${updated.version}). Users must accept again.`
          : "House rules saved.",
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
        title="House rules"
        description="Terms users must accept before using Workspace. Saving changed text bumps the version and prompts everyone to re-accept."
      />
      <form onSubmit={onSave} className="max-w-2xl space-y-4 rounded-lg border p-4">
        <p className="text-xs text-muted-foreground">Current version: {version}</p>
        <div className="space-y-1">
          <Label htmlFor="house-rules-content">Rules text</Label>
          <Textarea
            id="house-rules-content"
            rows={16}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Leave empty to disable the acceptance gate until you publish rules."
            className="min-h-[280px] font-mono text-sm"
          />
        </div>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save house rules"}
        </Button>
      </form>
    </div>
  );
}
