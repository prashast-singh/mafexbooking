"use client";

import { ErrorState } from "@/components/shared/ErrorState";
import { useT } from "@/i18n/use-t";

export function FindRoomFiltersError({ message }: { message: string }) {
  const t = useT();
  return <ErrorState title={t("findRoom.loadFiltersError")} message={message} />;
}
