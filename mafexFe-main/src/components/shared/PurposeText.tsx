import { cn } from "@/lib/utils";

export function PurposeText({
  purpose,
  className,
}: {
  purpose: string | null | undefined;
  className?: string;
}) {
  const text = purpose?.trim();
  if (!text) {
    return <span className={cn("text-muted-foreground", className)}>—</span>;
  }
  return (
    <span className={cn("line-clamp-2", className)} title={text}>
      {text}
    </span>
  );
}
