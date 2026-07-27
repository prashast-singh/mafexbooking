"use client";

import { cn } from "@/lib/utils";

/** Compact red count badge for pending admin attention. */
export function PendingCountBadge({
  count,
  className,
}: {
  count: number;
  className?: string;
}) {
  if (count <= 0) return null;
  const label = count > 99 ? "99+" : String(count);
  return (
    <span
      className={cn(
        "ml-1.5 inline-flex min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white",
        className,
      )}
      aria-label={`${count} pending`}
    >
      {label}
    </span>
  );
}
