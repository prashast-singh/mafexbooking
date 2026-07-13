"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SectionCard } from "@/components/shared/SectionCard";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { LoadingState } from "@/components/shared/LoadingState";
import {
  addRoomAdmin,
  createBookableUnit,
  deleteRoomAdmin,
  deleteBookableUnit,
  deleteRoom,
  deleteRoomImage,
  detachRoomAmenity,
  attachRoomAmenity,
  attachRoomTag,
  detachRoomTag,
  listAdminUsers,
  listRoomAdmins,
  updateBookableUnit,
  updateRoom,
  uploadRoomImage,
  type RoomAdminMappingOut,
} from "@/lib/api/admin";
import { listAmenities } from "@/lib/api/amenities";
import { listTags } from "@/lib/api/tags";
import { getRoom } from "@/lib/api/rooms";
import type {
  AdminUserOut,
  AmenityOut,
  TagOut,
  BookableUnitPublic,
  BookableUnitType,
  BookingMode,
  RoomDetailPublic,
  RoomImageBrief,
} from "@/lib/types/api";
import { mediaUrl } from "@/lib/utils/asset-url";
import { formatApiError } from "@/lib/utils/errors";
import { apiTimeToInput, inputTimeToApi } from "@/lib/utils/time-format";
import { isValidTimeRange } from "@/lib/utils/time-params";

export default function AdminRoomDetailPage() {
  const params = useParams();
  const router = useRouter();
  const roomId = Number.parseInt(String(params.roomId), 10);

  const [room, setRoom] = useState<RoomDetailPublic | null>(null);
  const [allAmenities, setAllAmenities] = useState<AmenityOut[]>([]);
  const [allTags, setAllTags] = useState<TagOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteRoomOpen, setDeleteRoomOpen] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [capacity, setCapacity] = useState(1);
  const [bookingMode, setBookingMode] = useState<BookingMode>("hybrid");
  const [isActive, setIsActive] = useState(true);
  const [windowStart, setWindowStart] = useState("08:00");
  const [windowEnd, setWindowEnd] = useState("20:00");

  const [unitName, setUnitName] = useState("");
  const [unitType, setUnitType] = useState<BookableUnitType>("table");
  const [unitCap, setUnitCap] = useState(4);
  const [unitBookingMode, setUnitBookingMode] = useState<"direct" | "request">("direct");

  const [roomAdmins, setRoomAdmins] = useState<RoomAdminMappingOut[]>([]);
  const [adminSearch, setAdminSearch] = useState("");
  const [adminSearchResults, setAdminSearchResults] = useState<AdminUserOut[]>([]);
  const [adminSearchLoading, setAdminSearchLoading] = useState(false);

  const load = useCallback(async () => {
    if (!Number.isFinite(roomId)) return;
    setLoading(true);
    try {
      const [r, am, tags, ra] = await Promise.all([
        getRoom(roomId),
        listAmenities(),
        listTags(),
        listRoomAdmins(roomId),
      ]);
      setRoom(r);
      setAllAmenities(am);
      setAllTags(tags);
      setRoomAdmins(ra);
      setName(r.name);
      setDescription(r.description ?? "");
      setLocation(r.location ?? "");
      setCapacity(r.capacity);
      setBookingMode(r.booking_mode as BookingMode);
      setIsActive(r.is_active);
      setWindowStart(apiTimeToInput(r.availability_window_start, "08:00"));
      setWindowEnd(apiTimeToInput(r.availability_window_end, "20:00"));
    } catch (e) {
      toast.error(formatApiError(e));
      setRoom(null);
    } finally {
      setLoading(false);
    }
  }, [roomId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const query = adminSearch.trim();
    if (query.length < 2) {
      setAdminSearchResults([]);
      return;
    }
    const timer = window.setTimeout(() => {
      setAdminSearchLoading(true);
      void listAdminUsers({ q: query, limit: 10 })
        .then((users) => {
          const assigned = new Set(roomAdmins.map((ra) => ra.user_id));
          setAdminSearchResults(users.filter((u) => !assigned.has(u.id)));
        })
        .catch((e) => toast.error(formatApiError(e)))
        .finally(() => setAdminSearchLoading(false));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [adminSearch, roomAdmins]);

  async function saveRoom() {
    if (!isValidTimeRange(windowStart, windowEnd)) {
      toast.error("Availability end must be after start.");
      return;
    }
    try {
      await updateRoom(roomId, {
        name,
        description: description || null,
        location: location || null,
        capacity,
        booking_mode: bookingMode,
        availability_window_start: inputTimeToApi(windowStart),
        availability_window_end: inputTimeToApi(windowEnd),
        is_active: isActive,
      });
      toast.success("Room updated.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function toggleAmenity(id: number, checked: boolean) {
    try {
      if (checked) {
        await attachRoomAmenity(roomId, id);
        toast.success("Amenity linked.");
      } else {
        await detachRoomAmenity(roomId, id);
        toast.success("Amenity removed.");
      }
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function toggleTag(id: number, checked: boolean) {
    try {
      if (checked) {
        await attachRoomTag(roomId, id);
        toast.success("Tag linked.");
      } else {
        await detachRoomTag(roomId, id);
        toast.success("Tag removed.");
      }
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function onUploadImage(file: File | null) {
    if (!file) return;
    try {
      await uploadRoomImage(roomId, file);
      toast.success("Image uploaded.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function removeImage(img: RoomImageBrief) {
    try {
      await deleteRoomImage(roomId, img.id);
      toast.success("Image removed.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function addUnit() {
    try {
      await createBookableUnit(roomId, {
        name: unitName,
        type: unitType,
        booking_mode: unitBookingMode,
        capacity: unitCap,
        is_active: true,
      });
      toast.success("Unit created.");
      setUnitName("");
      setUnitCap(4);
      setUnitBookingMode("direct");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function addRoomAdminUser(user: AdminUserOut) {
    try {
      await addRoomAdmin(roomId, user.id);
      toast.success("Room admin added.");
      setAdminSearch("");
      setAdminSearchResults([]);
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function removeRoomAdminUser(userId: number) {
    try {
      await deleteRoomAdmin(roomId, userId);
      toast.success("Room admin removed.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function toggleUnit(u: BookableUnitPublic) {
    try {
      await updateBookableUnit(u.id, { is_active: !u.is_active });
      toast.success("Unit updated.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function changeUnitBookingMode(u: BookableUnitPublic, booking_mode: "direct" | "request") {
    if (u.booking_mode === booking_mode) return;
    try {
      await updateBookableUnit(u.id, { booking_mode });
      toast.success("Unit booking mode updated.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function removeUnit(id: number) {
    try {
      await deleteBookableUnit(id);
      toast.success("Unit deleted.");
      void load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  async function confirmDeleteRoom() {
    try {
      await deleteRoom(roomId);
      toast.success("Room deleted.");
      router.replace("/admin/rooms");
    } catch (e) {
      toast.error(formatApiError(e));
    }
  }

  if (!Number.isFinite(roomId)) {
    return <p className="p-6 text-sm text-destructive">Invalid room.</p>;
  }

  if (loading || !room) return <LoadingState />;

  return (
    <div className="space-y-8 p-6">
      <div className="flex flex-wrap items-center gap-4">
        <Link
          href="/admin/rooms"
          className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
        >
          ← Rooms
        </Link>
        <h1 className="text-xl font-semibold">{room.name}</h1>
      </div>

      <SectionCard title="Details">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1 sm:col-span-2">
            <Label htmlFor="r-name">Name</Label>
            <Input id="r-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1 sm:col-span-2">
            <Label htmlFor="r-desc">Description</Label>
            <Input id="r-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="r-loc">Location</Label>
            <Input id="r-loc" value={location} onChange={(e) => setLocation(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="r-cap">Capacity</Label>
            <Input
              id="r-cap"
              type="number"
              min={1}
              value={capacity}
              onChange={(e) => setCapacity(Number.parseInt(e.target.value, 10) || 1)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="r-mode">Booking mode</Label>
            <select
              id="r-mode"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              value={bookingMode}
              onChange={(e) => setBookingMode(e.target.value as BookingMode)}
            >
              <option value="full_room_only">Full room only</option>
              <option value="tables_only">Tables only</option>
              <option value="hybrid">Hybrid</option>
              <option value="sections_only">Sections only</option>
            </select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="r-win-start">Available from</Label>
            <Input
              id="r-win-start"
              type="time"
              value={windowStart}
              onChange={(e) => setWindowStart(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="r-win-end">Available until</Label>
            <Input
              id="r-win-end"
              type="time"
              value={windowEnd}
              onChange={(e) => setWindowEnd(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Active (visible for booking when approved catalog rules apply)
          </label>
        </div>
        <Button className="mt-4" onClick={() => void saveRoom()}>
          Save details
        </Button>
      </SectionCard>

      <SectionCard title="Amenities">
        <p className="mb-3 text-sm text-muted-foreground">Toggle to link or unlink from this room.</p>
        <div className="flex flex-wrap gap-4">
          {allAmenities.map((a) => {
            const on = room.amenities.some((x) => x.id === a.id);
            return (
              <label key={a.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={on}
                  onChange={(e) => void toggleAmenity(a.id, e.target.checked)}
                />
                {a.name}
              </label>
            );
          })}
        </div>
      </SectionCard>

      <SectionCard title="Tags">
        <p className="mb-3 text-sm text-muted-foreground">
          Tagged users only see rooms that share at least one of their tags. Untagged rooms are visible only to users
          without tags.
        </p>
        <div className="flex flex-wrap gap-4">
          {allTags.map((t) => {
            const on = (room.tags ?? []).some((x) => x.id === t.id);
            return (
              <label key={t.id} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={on} onChange={(e) => void toggleTag(t.id, e.target.checked)} />
                {t.name}
              </label>
            );
          })}
          {allTags.length === 0 && <p className="text-sm text-muted-foreground">No tags defined yet.</p>}
        </div>
      </SectionCard>

      <SectionCard title="Images">
        <div className="mb-4">
          <Label htmlFor="img-up">Upload</Label>
          <Input
            id="img-up"
            type="file"
            accept="image/*"
            className="mt-1 max-w-sm"
            onChange={(e) => void onUploadImage(e.target.files?.[0] ?? null)}
          />
        </div>
        <ul className="space-y-2">
          {room.images.map((img) => (
            <li key={img.id} className="flex items-center justify-between gap-4 rounded border px-3 py-2 text-sm">
              <span className="truncate font-mono text-xs">{mediaUrl(img.file_url)}</span>
              <Button size="sm" variant="destructive" onClick={() => void removeImage(img)}>
                Remove
              </Button>
            </li>
          ))}
          {room.images.length === 0 && <p className="text-sm text-muted-foreground">No images yet.</p>}
        </ul>
      </SectionCard>

      <SectionCard title="Bookable units">
        <div className="mb-4 grid gap-3 sm:grid-cols-4">
          <div className="space-y-1 sm:col-span-2">
            <Label>Name</Label>
            <Input value={unitName} onChange={(e) => setUnitName(e.target.value)} placeholder="Table A" />
          </div>
          <div className="space-y-1">
            <Label>Booking</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              value={unitBookingMode}
              onChange={(e) => setUnitBookingMode(e.target.value as "direct" | "request")}
            >
              <option value="direct">Direct</option>
              <option value="request">Request</option>
            </select>
          </div>
          <div className="space-y-1">
            <Label>Type</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              value={unitType}
              onChange={(e) => setUnitType(e.target.value as BookableUnitType)}
            >
              <option value="full_room">Full room</option>
              <option value="half_room">Half room</option>
              <option value="section">Section</option>
              <option value="table">Table</option>
            </select>
          </div>
          <div className="space-y-1">
            <Label>Capacity</Label>
            <Input
              type="number"
              min={1}
              value={unitCap}
              onChange={(e) => setUnitCap(Number.parseInt(e.target.value, 10) || 1)}
            />
          </div>
          <Button className="sm:col-span-4" onClick={() => void addUnit()} disabled={!unitName.trim()}>
            Add unit
          </Button>
        </div>
        <ul className="space-y-2">
          {room.bookable_units.map((u) => (
            <li
              key={u.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded border px-3 py-2 text-sm"
            >
              <span>
                {u.name}{" "}
                <span className="text-muted-foreground">
                  ({u.type}, {u.booking_mode === "request" ? "request approval" : "direct"}, cap {u.capacity})
                </span>
              </span>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  className="flex h-8 rounded-md border border-input bg-transparent px-2 text-xs"
                  value={u.booking_mode}
                  onChange={(e) => void changeUnitBookingMode(u, e.target.value as "direct" | "request")}
                >
                  <option value="direct">Direct</option>
                  <option value="request">Request</option>
                </select>
                <Button size="sm" variant="outline" onClick={() => void toggleUnit(u)}>
                  {u.is_active ? "Deactivate" : "Activate"}
                </Button>
                <Button size="sm" variant="destructive" onClick={() => void removeUnit(u.id)}>
                  Delete
                </Button>
              </div>
            </li>
          ))}
          {room.bookable_units.length === 0 && (
            <p className="text-sm text-muted-foreground">No units — add at least one for bookings.</p>
          )}
        </ul>
      </SectionCard>

      <SectionCard title="Room admins">
        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="room-admin-search">Search by email or name</Label>
            <Input
              id="room-admin-search"
              type="search"
              placeholder="e.g. singhpr4@students.uni-marburg.de"
              value={adminSearch}
              onChange={(e) => setAdminSearch(e.target.value)}
            />
            {adminSearchLoading && (
              <p className="text-sm text-muted-foreground">Searching users...</p>
            )}
            {!adminSearchLoading && adminSearch.trim().length >= 2 && adminSearchResults.length === 0 && (
              <p className="text-sm text-muted-foreground">No matching users found.</p>
            )}
            {adminSearchResults.length > 0 && (
              <div className="rounded-lg border">
                <div className="divide-y">
                  {adminSearchResults.map((user) => (
                    <div key={user.id} className="flex items-center justify-between gap-3 p-3 text-sm">
                      <div>
                        <p className="font-medium">{user.full_name}</p>
                        <p className="text-muted-foreground">{user.email}</p>
                      </div>
                      <Button size="sm" onClick={() => void addRoomAdminUser(user)}>
                        Add
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          {roomAdmins.length === 0 ? (
            <p className="text-sm text-muted-foreground">No room admins yet.</p>
          ) : (
            <div className="rounded-lg border">
              <div className="divide-y">
                {roomAdmins.map((ra) => (
                  <div key={ra.user_id} className="flex items-center justify-between gap-3 p-3 text-sm">
                    <div>
                      <p className="font-medium">{ra.user_full_name}</p>
                      <p className="text-muted-foreground">{ra.user_email}</p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void removeRoomAdminUser(ra.user_id)}
                    >
                      Remove
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </SectionCard>

      <div className="border-t pt-6">
        <Button variant="destructive" onClick={() => setDeleteRoomOpen(true)}>
          Delete room
        </Button>
      </div>

      <ConfirmDialog
        open={deleteRoomOpen}
        onOpenChange={setDeleteRoomOpen}
        title="Delete this room?"
        description="This cannot be undone."
        confirmLabel="Delete"
        destructive
        onConfirm={confirmDeleteRoom}
      />
    </div>
  );
}
