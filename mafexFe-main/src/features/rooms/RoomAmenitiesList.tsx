import { Badge } from "@/components/ui/badge";
import type { AmenityBrief } from "@/lib/types/api";

export function RoomAmenitiesList({ amenities }: { amenities: AmenityBrief[] }) {
  if (amenities.length === 0) {
    return <p className="text-sm text-muted-foreground">No amenities listed.</p>;
  }

  return (
    <ul className="flex flex-wrap gap-2">
      {amenities.map((a) => (
        <li key={a.id}>
          <Badge variant="secondary" className="gap-1 font-normal">
            {a.icon && <span className="text-muted-foreground">{a.icon}</span>}
            {a.name}
          </Badge>
        </li>
      ))}
    </ul>
  );
}
