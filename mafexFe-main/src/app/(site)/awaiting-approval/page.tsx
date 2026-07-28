"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { useT } from "@/i18n/use-t";
import { FIND_ROOM_PATH } from "@/lib/routes";
import { useAuth } from "@/hooks/use-auth";

export default function AwaitingApprovalPage() {
  const { user, loading, logout, refresh } = useAuth();
  const router = useRouter();
  const t = useT();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (user.approval_status === "approved") {
      router.replace(FIND_ROOM_PATH);
    }
  }, [loading, user, router]);

  if (loading || !user) return <LoadingState />;

  if (user.approval_status === "rejected") {
    return (
      <div className="mx-auto max-w-lg px-4 py-12">
        <PageHeader
          title={t("approval.rejectedTitle")}
          description={t("approval.rejectedDescription")}
        />
        <Button variant="outline" onClick={() => logout()}>
          {t("common.logOut")}
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg px-4 py-12">
      <PageHeader
        title={t("approval.pendingTitle")}
        description={t("approval.pendingDescription")}
      />
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => void refresh()}>
          {t("approval.refreshStatus")}
        </Button>
        <Button variant="ghost" onClick={() => logout()}>
          {t("common.logOut")}
        </Button>
      </div>
    </div>
  );
}
