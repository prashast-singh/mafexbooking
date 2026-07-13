import { apiFetch } from "@/lib/api/client";
import type { AmenityOut } from "@/lib/types/api";

export async function listAmenities() {
  return apiFetch<AmenityOut[]>("/amenities", { auth: false });
}
