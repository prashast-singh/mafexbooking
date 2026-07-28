"use client";

import { PageHeader } from "@/components/shared/PageHeader";
import { useT } from "@/i18n/use-t";

export function FindRoomHeader() {
  const t = useT();
  return (
    <PageHeader title={t("findRoom.title")} description={t("findRoom.description")} />
  );
}
