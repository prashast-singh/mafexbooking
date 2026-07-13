/**
 * Join API origin (strip /api/v1) with a path like /storage/room_images/x.jpg
 */
export function mediaUrl(pathOrUrl: string | null | undefined): string | undefined {
  if (!pathOrUrl) return undefined;
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  const origin = base.replace(/\/api\/v1\/?$/, "");
  return `${origin}${pathOrUrl.startsWith("/") ? "" : "/"}${pathOrUrl}`;
}
