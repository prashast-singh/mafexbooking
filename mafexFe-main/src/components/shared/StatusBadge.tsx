import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const variants: Record<string, string> = {
  active: "bg-emerald-600 hover:bg-emerald-600",
  inactive: "bg-zinc-500 hover:bg-zinc-500",
  approved: "bg-emerald-600 hover:bg-emerald-600",
  pending: "bg-amber-500 hover:bg-amber-500",
  rejected: "bg-red-600 hover:bg-red-600",
  confirmed: "bg-blue-600 hover:bg-blue-600",
  cancelled: "bg-zinc-500 hover:bg-zinc-500",
  completed: "bg-violet-600 hover:bg-violet-600",
  internal: "bg-slate-600 hover:bg-slate-600",
  external: "bg-slate-500 hover:bg-slate-500",
  admin: "bg-purple-600 hover:bg-purple-600",
  user: "bg-slate-400 hover:bg-slate-400",
};

export function StatusBadge({ value }: { value: string }) {
  const key = value.toLowerCase();
  const cls = variants[key] ?? "bg-zinc-600 hover:bg-zinc-600";
  return (
    <Badge className={cn("text-white capitalize", cls)} variant="default">
      {value.replace(/_/g, " ")}
    </Badge>
  );
}
