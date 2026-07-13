"use client";

import Image from "next/image";
import { useState } from "react";

import { cn } from "@/lib/utils";
import type { RoomImageBrief } from "@/lib/types/api";
import { mediaUrl } from "@/lib/utils/asset-url";

export function RoomImageGallery({
  images,
  alt,
  thumbnailUrl,
}: {
  images: RoomImageBrief[];
  alt: string;
  thumbnailUrl: string | null;
}) {
  const sorted = [...images].sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
  const thumb = mediaUrl(thumbnailUrl);
  const fromSorted = sorted
    .map((img) => ({ id: img.id, url: mediaUrl(img.file_url) }))
    .filter((x): x is { id: number; url: string } => Boolean(x.url));
  const list =
    fromSorted.length > 0 ? fromSorted : thumb ? [{ id: 0, url: thumb }] : [];

  const [active, setActive] = useState(0);
  const main = list[active];

  if (list.length === 0) {
    return (
      <div className="flex aspect-[16/10] w-full items-center justify-center rounded-lg border bg-muted text-sm text-muted-foreground">
        No photos yet
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="relative aspect-[16/10] w-full overflow-hidden rounded-lg border bg-muted">
        {main?.url && (
          <Image
            src={main.url}
            alt={alt}
            fill
            className="object-cover"
            sizes="(max-width: 1024px) 100vw, 66vw"
            priority
            unoptimized
          />
        )}
      </div>
      {list.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {list.map((img, i) => (
            <button
              key={img.id}
              type="button"
              onClick={() => setActive(i)}
              className={cn(
                "relative h-16 w-24 shrink-0 overflow-hidden rounded-md border-2 transition-colors",
                i === active ? "border-primary" : "border-transparent opacity-70 hover:opacity-100",
              )}
            >
              <Image src={img.url} alt="" fill className="object-cover" sizes="96px" unoptimized />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
