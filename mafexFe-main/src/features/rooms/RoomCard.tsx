import Image from "next/image";
import Link from "next/link";
import { MapPin, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import type { RoomBrowseItem } from "@/lib/types/api";
import { mediaUrl } from "@/lib/utils/asset-url";

export function RoomCard({ room }: { room: RoomBrowseItem }) {
  const thumb = mediaUrl(room.thumbnail_url);

  return (
    <Card className="overflow-hidden transition-shadow hover:shadow-md">
      <Link href={`/rooms/${room.id}`} className="block">
        <div className="relative aspect-[16/10] w-full bg-muted">
          {thumb ? (
            <Image
              src={thumb}
              alt={room.name}
              fill
              className="object-cover"
              sizes="(max-width:768px) 100vw, 33vw"
              unoptimized
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              No image
            </div>
          )}
        </div>
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <h3 className="line-clamp-2 font-semibold leading-tight">{room.name}</h3>
            <Badge variant="outline" className="shrink-0 capitalize">
              {room.booking_mode.replace(/_/g, " ")}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-2 pb-2 text-sm text-muted-foreground">
          {room.location && (
            <p className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5 shrink-0" />
              <span className="line-clamp-1">{room.location}</span>
            </p>
          )}
          <p className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5 shrink-0" />
            Capacity {room.capacity}
          </p>
          {room.description && (
            <p className="line-clamp-2 text-xs">{room.description}</p>
          )}
          <div className="flex flex-wrap gap-1 pt-1">
            {room.amenities.slice(0, 4).map((a) => (
              <Badge key={a.id} variant="secondary" className="text-xs font-normal">
                {a.name}
              </Badge>
            ))}
            {room.amenities.length > 4 && (
              <Badge variant="outline" className="text-xs">
                +{room.amenities.length - 4}
              </Badge>
            )}
          </div>
        </CardContent>
        <CardFooter className="border-t bg-muted/30 py-2 text-xs text-muted-foreground">
          View availability & book →
        </CardFooter>
      </Link>
    </Card>
  );
}
