"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RoomCard } from "@/features/rooms/RoomCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { listRooms, type RoomListParams } from "@/lib/api/rooms";
import type { RoomBrowsePage } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";
import { mergeSearchParams } from "@/lib/utils/room-list-params";

type Props = {
  params: RoomListParams;
  searchParamsString: string;
};

export function FindRoomResults({ params, searchParamsString }: Props) {
  const [page, setPage] = useState<RoomBrowsePage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    void listRooms(params)
      .then(setPage)
      .catch((e) => {
        setPage(null);
        setError(formatApiError(e));
      })
      .finally(() => setLoading(false));
  }, [params, searchParamsString]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState title="Could not load rooms" message={error} />;
  if (!page || page.items.length === 0) {
    return (
      <EmptyState
        title="No rooms match"
        description="Try clearing filters or picking another date."
      />
    );
  }

  const sp = new URLSearchParams(searchParamsString);
  const totalPages = Math.max(1, Math.ceil(page.total / page.limit));
  const prevPage = page.page > 1 ? page.page - 1 : null;
  const nextPage = page.page < totalPages ? page.page + 1 : null;

  return (
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
  );
}
