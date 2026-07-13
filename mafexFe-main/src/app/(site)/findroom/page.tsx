import Link from "next/link";

import { RoomCard } from "@/features/rooms/RoomCard";
import { RoomFilters } from "@/features/rooms/RoomFilters";
import { listAmenities } from "@/lib/api/amenities";
import { listRooms } from "@/lib/api/rooms";
import { PageHeader } from "@/components/shared/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import {
  mergeSearchParams,
  parseRoomListSearchParams,
  recordToSearchParams,
} from "@/lib/utils/room-list-params";
import { formatApiError } from "@/lib/utils/errors";
import { ApiError } from "@/lib/api/client";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export const dynamic = "force-dynamic";

export default async function FindRoomPage({ searchParams }: PageProps) {
  const raw = await searchParams;
  const params = parseRoomListSearchParams(raw);
  const sp = recordToSearchParams(raw);

  let amenities;
  try {
    amenities = await listAmenities();
  } catch (e) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-10">
        <ErrorState title="Could not load filters" message={formatApiError(e)} />
      </div>
    );
  }

  let page;
  try {
    page = await listRooms(params);
  } catch (e) {
    const msg = e instanceof ApiError ? formatApiError(e) : "Failed to load rooms.";
    return (
      <div className="mx-auto max-w-7xl px-4 py-10">
        <ErrorState title="Could not load rooms" message={msg} />
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(page.total / page.limit));
  const prevPage = page.page > 1 ? page.page - 1 : null;
  const nextPage = page.page < totalPages ? page.page + 1 : null;

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-8">
      <PageHeader
        title="Meeting rooms"
        description="Pick a date and time range and unit type to see what you can book."
      />
      <RoomFilters amenities={amenities} />
      {page.items.length === 0 ? (
        <EmptyState
          title="No rooms match"
          description="Try clearing filters or picking another date."
        />
      ) : (
        <>
          <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {page.items.map((room) => (
              <RoomCard key={room.id} room={room} />
            ))}
          </div>
          <div className="flex items-center justify-between border-t pt-6 text-sm text-muted-foreground">
            <span>
              Page {page.page} of {totalPages} · {page.total} rooms
            </span>
            <div className="flex gap-2">
              {prevPage != null ? (
                <Link
                  href={`/findroom?${mergeSearchParams(sp, { page: String(prevPage) })}`}
                  className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                >
                  Previous
                </Link>
              ) : (
                <Button variant="outline" size="sm" disabled>
                  Previous
                </Button>
              )}
              {nextPage != null ? (
                <Link
                  href={`/findroom?${mergeSearchParams(sp, { page: String(nextPage) })}`}
                  className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                >
                  Next
                </Link>
              ) : (
                <Button variant="outline" size="sm" disabled>
                  Next
                </Button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
