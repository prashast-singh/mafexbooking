"use client";

import Image from "next/image";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
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
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const main = list[active] ?? list[0];
  const hasMultiple = list.length > 1;

  const openAt = useCallback((index: number) => {
    setActive(index);
    setLightboxOpen(true);
  }, []);

  const goPrev = useCallback(() => {
    if (list.length < 2) return;
    setActive((i) => (i - 1 + list.length) % list.length);
  }, [list.length]);

  const goNext = useCallback(() => {
    if (list.length < 2) return;
    setActive((i) => (i + 1) % list.length);
  }, [list.length]);

  useEffect(() => {
    if (!lightboxOpen || !hasMultiple) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goNext();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [lightboxOpen, hasMultiple, goPrev, goNext]);

  if (list.length === 0) {
    return (
      <div className="flex aspect-[16/10] w-full items-center justify-center rounded-lg border bg-muted text-sm text-muted-foreground">
        No photos yet
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => openAt(active)}
        className="relative aspect-[16/10] w-full cursor-zoom-in overflow-hidden rounded-lg border bg-muted text-left"
        aria-label={`View larger photo of ${alt}`}
      >
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
      </button>
      {hasMultiple && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {list.map((img, i) => (
            <button
              key={img.id}
              type="button"
              onClick={() => openAt(i)}
              className={cn(
                "relative h-16 w-24 shrink-0 overflow-hidden rounded-md border-2 transition-colors",
                i === active ? "border-primary" : "border-transparent opacity-70 hover:opacity-100",
              )}
              aria-label={`View photo ${i + 1} of ${list.length}`}
            >
              <Image src={img.url} alt="" fill className="object-cover" sizes="96px" unoptimized />
            </button>
          ))}
        </div>
      )}

      <Dialog open={lightboxOpen} onOpenChange={setLightboxOpen}>
        <DialogContent
          className="max-h-[90vh] w-full max-w-5xl gap-0 overflow-hidden border-0 bg-black/95 p-0 text-white ring-0 sm:max-w-5xl"
          showCloseButton
        >
          <DialogTitle className="sr-only">{alt}</DialogTitle>
          <DialogDescription className="sr-only">
            Enlarged room photo{hasMultiple ? `. Image ${active + 1} of ${list.length}.` : "."}
          </DialogDescription>
          <div className="relative flex min-h-[50vh] items-center justify-center p-10 sm:min-h-[70vh]">
            {main?.url && (
              <Image
                src={main.url}
                alt={alt}
                fill
                className="object-contain p-4"
                sizes="90vw"
                unoptimized
                priority
              />
            )}
            {hasMultiple && (
              <>
                <Button
                  type="button"
                  variant="secondary"
                  size="icon"
                  className="absolute top-1/2 left-2 z-10 -translate-y-1/2"
                  onClick={goPrev}
                  aria-label="Previous image"
                >
                  <ChevronLeft className="h-5 w-5" />
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="icon"
                  className="absolute top-1/2 right-2 z-10 -translate-y-1/2"
                  onClick={goNext}
                  aria-label="Next image"
                >
                  <ChevronRight className="h-5 w-5" />
                </Button>
                <p className="absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-black/60 px-3 py-1 text-xs text-white">
                  {active + 1} / {list.length}
                </p>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
