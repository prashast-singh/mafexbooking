"use client";

import { format } from "date-fns";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, MapPin, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SectionCard } from "@/components/shared/SectionCard";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { useT } from "@/i18n/use-t";
import { getRoomAvailability } from "@/lib/api/availability";
import { getRoom } from "@/lib/api/rooms";
import type { RoomAvailabilityGrid, RoomDetailPublic } from "@/lib/types/api";
import { AvailabilityGrid } from "@/features/booking/AvailabilityGrid";
import type { BookingSlotSelection } from "@/features/booking/booking-selection";
import { BookingForm } from "@/features/booking/BookingForm";
import { RoomAmenitiesList } from "@/features/rooms/RoomAmenitiesList";
import { RoomImageGallery } from "@/features/rooms/RoomImageGallery";
import { useAuth } from "@/hooks/use-auth";
import { FIND_ROOM_PATH } from "@/lib/routes";
import { formatApiError } from "@/lib/utils/errors";
import { ApiError } from "@/lib/api/client";

export function RoomDetailClient({ roomId }: { roomId: number }) {
  const { user } = useAuth();
  const t = useT();
  const [room, setRoom] = useState<RoomDetailPublic | null>(null);
  const [roomError, setRoomError] = useState<string | null>(null);
  const [roomLoading, setRoomLoading] = useState(true);
  const [date, setDate] = useState(() => format(new Date(), "yyyy-MM-dd"));
  const [grid, setGrid] = useState<RoomAvailabilityGrid | null>(null);
  const [loading, setLoading] = useState(false);
  const [selection, setSelection] = useState<BookingSlotSelection | null>(null);

  useEffect(() => {
    setRoomLoading(true);
    setRoomError(null);
    void getRoom(roomId)
      .then(setRoom)
      .catch((e) => {
        setRoom(null);
        if (e instanceof ApiError && e.status === 404) {
          setRoomError(t("roomDetail.notFound"));
        } else {
          setRoomError(formatApiError(e));
        }
      })
      .finally(() => setRoomLoading(false));
  }, [roomId, t]);

  const load = useCallback(async () => {
    if (!room) return;
    setLoading(true);
    setSelection(null);
    try {
      const g = await getRoomAvailability(room.id, date);
      setGrid(g);
    } catch {
      setGrid(null);
    } finally {
      setLoading(false);
    }
  }, [room, date]);

  useEffect(() => {
    void load();
  }, [load]);

  const canBook = !!user && user.approval_status === "approved";

  if (roomLoading) return <LoadingState />;
  if (roomError || !room) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8">
        <ErrorState
          title={t("roomDetail.unavailableTitle")}
          message={roomError ?? t("roomDetail.notFound")}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-4 py-8">
      <Link
        href={FIND_ROOM_PATH}
        className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "-ml-2 inline-flex")}
      >
        <ArrowLeft className="mr-1 h-4 w-4" />
        {t("roomDetail.allRooms")}
      </Link>

      <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <RoomImageGallery
            images={room.images}
            thumbnailUrl={room.thumbnail_url}
            alt={room.name}
          />
          <div>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">{room.name}</h1>
              <Badge variant="outline" className="capitalize">
                {room.booking_mode.replace(/_/g, " ")}
              </Badge>
            </div>
            <div className="mt-2 flex flex-wrap gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Users className="h-4 w-4" />
                {t("roomDetail.capacity")} {room.capacity}
              </span>
              {room.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-4 w-4" />
                  {room.location}
                </span>
              )}
            </div>
            {room.description && <p className="mt-4 text-muted-foreground">{room.description}</p>}
          </div>
          <SectionCard title={t("roomDetail.amenities")}>
            <RoomAmenitiesList amenities={room.amenities} />
          </SectionCard>
        </div>

        <div className="space-y-6">
          <SectionCard title={t("roomDetail.availability")}>
            <div className="mb-4 space-y-2">
              <Label htmlFor="book-date">{t("common.date")}</Label>
              <Input
                id="book-date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <AvailabilityGrid
              grid={grid}
              loading={loading}
              selected={selection}
              onSelect={setSelection}
            />
          </SectionCard>
          <SectionCard title={t("roomDetail.bookThisRoom")}>
            <BookingForm
              roomId={room.id}
              bookingDate={date}
              selection={selection}
              canBook={canBook}
              onBooked={() => {
                setSelection(null);
                void load();
              }}
            />
            {!user && (
              <p className="mt-3 text-sm text-muted-foreground">{t("roomDetail.loginToBook")}</p>
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
