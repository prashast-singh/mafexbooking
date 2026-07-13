import { RoomFilters } from "@/features/rooms/RoomFilters";
import { FindRoomResults } from "@/features/rooms/FindRoomResults";
import { listAmenities } from "@/lib/api/amenities";
import { PageHeader } from "@/components/shared/PageHeader";
import { ErrorState } from "@/components/shared/ErrorState";
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
        <ErrorState title="Could not load filters" message={formatApiError(e)} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-8">
      <PageHeader
        title="Meeting rooms"
        description="Pick a date and time range and unit type to see what you can book."
      />
      <RoomFilters amenities={amenities} />
      <FindRoomResults params={params} searchParamsString={sp.toString()} />
    </div>
  );
}
