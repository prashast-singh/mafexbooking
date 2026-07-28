"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/hooks/use-auth";
import { useT } from "@/i18n/use-t";
import { acceptMyHouseRules, getMyHouseRules } from "@/lib/api/users";
import { formatApiError } from "@/lib/utils/errors";

export function HouseRulesGate() {
  const { user, loading, refresh, logout } = useAuth();
  const t = useT();
  const [content, setContent] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);

  const mustAccept =
    !!user && user.approval_status === "approved" && !!user.must_accept_house_rules;

  useEffect(() => {
    if (!mustAccept) {
      setContent(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const rules = await getMyHouseRules();
        if (!cancelled) setContent(rules.content);
      } catch (e) {
        if (!cancelled) toast.error(formatApiError(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mustAccept, user?.house_rules_version]);

  async function onAccept() {
    setAccepting(true);
    try {
      await acceptMyHouseRules();
      await refresh();
      toast.success(t("houseRules.accepted"));
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setAccepting(false);
    }
  }

  if (loading || !mustAccept) return null;

  return (
    <Dialog
      open
      onOpenChange={() => {
        /* blocking — ignore dismiss */
      }}
    >
      <DialogContent showCloseButton={false} className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("houseRules.title")}</DialogTitle>
          <DialogDescription>{t("houseRules.description")}</DialogDescription>
        </DialogHeader>
        <div className="max-h-[50vh] overflow-y-auto whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-sm">
          {content === null ? t("houseRules.loading") : content || t("houseRules.empty")}
        </div>
        <DialogFooter className="sm:justify-between">
          <Button type="button" variant="outline" onClick={logout} disabled={accepting}>
            {t("common.logOut")}
          </Button>
          <Button type="button" onClick={() => void onAccept()} disabled={accepting || content === null}>
            {accepting ? t("common.accepting") : t("common.accept")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
