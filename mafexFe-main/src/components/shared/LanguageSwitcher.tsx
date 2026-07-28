"use client";

import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import { useLocale } from "@/i18n/use-t";
import type { Locale } from "@/i18n/config";

export function LanguageSwitcher({ className }: { className?: string }) {
  const { locale, setLocale, t } = useLocale();

  function select(next: Locale) {
    if (next === locale) return;
    setLocale(next);
  }

  return (
    <div
      className={cn("inline-flex items-center gap-0.5 rounded-md border p-0.5", className)}
      role="group"
      aria-label={t("nav.language")}
    >
      <button
        type="button"
        onClick={() => select("en")}
        className={cn(
          buttonVariants({ variant: locale === "en" ? "secondary" : "ghost", size: "sm" }),
          "h-7 min-w-9 px-2 text-xs font-semibold",
        )}
        aria-pressed={locale === "en"}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => select("de")}
        className={cn(
          buttonVariants({ variant: locale === "de" ? "secondary" : "ghost", size: "sm" }),
          "h-7 min-w-9 px-2 text-xs font-semibold",
        )}
        aria-pressed={locale === "de"}
      >
        DE
      </button>
    </div>
  );
}
