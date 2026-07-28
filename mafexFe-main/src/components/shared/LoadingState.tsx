"use client";

import { Loader2 } from "lucide-react";

import { useT } from "@/i18n/use-t";

export function LoadingState({ label }: { label?: string }) {
  const t = useT();
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-muted-foreground">
      <Loader2 className="h-8 w-8 animate-spin" />
      <p className="text-sm">{label ?? t("common.loading")}</p>
    </div>
  );
}
