import { notFound } from "next/navigation";

import { RoomDetailClient } from "@/features/rooms/RoomDetailClient";

type PageProps = { params: Promise<{ roomId: string }> };

export default async function RoomDetailPage({ params }: PageProps) {
  const { roomId } = await params;
  const id = Number.parseInt(roomId, 10);
  if (!Number.isFinite(id)) notFound();

  return <RoomDetailClient roomId={id} />;
}
