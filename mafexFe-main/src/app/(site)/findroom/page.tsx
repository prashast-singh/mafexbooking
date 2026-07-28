import { RoomFilters } from "@/features/rooms/RoomFilters";
import { FindRoomResults } from "@/features/rooms/FindRoomResults";
import { FindRoomHeader } from "@/features/rooms/FindRoomHeader";
import { FindRoomFiltersError } from "@/features/rooms/FindRoomFiltersError";
import { listAmenities } from "@/lib/api/amenities";
import {
  parseRoomListSearchParams,
  recordToSearchParams,
} from "@/lib/utils/room-list-params";
import { formatApiError } from "@/lib/utils/errors";

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
        <FindRoomFiltersError message={formatApiError(e)} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-8">
      <FindRoomHeader />
      <RoomFilters amenities={amenities} />
      <FindRoomResults params={params} searchParamsString={sp.toString()} />
    </div>
  );
}
