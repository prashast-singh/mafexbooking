import { apiFetch } from "@/lib/api/client";
import type { TagOut } from "@/lib/types/api";

export async function listTags() {
  return apiFetch<TagOut[]>("/tags");
}
