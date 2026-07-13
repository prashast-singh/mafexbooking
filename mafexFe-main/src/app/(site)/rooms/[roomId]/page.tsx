import { notFound } from "next/navigation";

import { RoomDetailClient } from "@/features/rooms/RoomDetailClient";
import { getRoom } from "@/lib/api/rooms";
import { ApiError } from "@/lib/api/client";

type PageProps = { params: Promise<{ roomId: string }> };

export default async function RoomDetailPage({ params }: PageProps) {
  const { roomId } = await params;
  const id = Number.parseInt(roomId, 10);
  if (!Number.isFinite(id)) notFound();

  try {
    const room = await getRoom(id);
    return <RoomDetailClient room={room} />;
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
}
