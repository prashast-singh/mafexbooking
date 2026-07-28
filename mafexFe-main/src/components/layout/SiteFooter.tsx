"use client";

import Image from "next/image";
import { Facebook, Instagram, Linkedin, Youtube } from "lucide-react";

import { useT } from "@/i18n/use-t";

const socialLinks = [
  {
    href: "https://www.linkedin.com/company/marburger-institut-f%C3%BCr-innovationsforschung-und-existenzgr%C3%BCndungsf%C3%B6rderung-mafex/",
    label: "MAFEX on LinkedIn",
    Icon: Linkedin,
  },
  {
    href: "https://www.instagram.com/mafexmarburg/",
    label: "MAFEX on Instagram",
    Icon: Instagram,
  },
  {
    href: "https://www.youtube.com/channel/UCCYYr5nvvA18hI-hpPhQtDA",
    label: "Universität Marburg on YouTube",
    Icon: Youtube,
  },
  {
    href: "https://www.facebook.com/PhilippsUniversitaet",
    label: "Philipps-Universität on Facebook",
    Icon: Facebook,
  },
] as const;

export function SiteFooter() {
  const t = useT();

  return (
    <footer className="border-t bg-zinc-950 text-zinc-300">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-8 sm:grid-cols-[auto_1fr_auto] sm:items-start">
        <a
          href="https://www.uni-marburg.de"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block shrink-0"
          aria-label="Philipps-Universität Marburg"
        >
          <Image
            src="/uni-marburg-logo.png"
            alt="Universität Marburg"
            width={220}
            height={72}
            className="h-14 w-auto object-contain"
            unoptimized
          />
        </a>

        <div className="space-y-2 text-sm">
          <p className="font-medium text-zinc-100">{t("footer.orgName")}</p>
          <p>
            Hans-Meerwein-Straße 6
            <br />
            35043 Marburg
          </p>
          <p>
            {t("footer.phone")}:{" "}
            <a href="tel:+4964212821753" className="hover:text-white hover:underline">
              +49 6421/28-21753
            </a>
          </p>
          <p>
            <a href="mailto:mafex@uni-marburg.de" className="hover:text-white hover:underline">
              mafex@uni-marburg.de
            </a>
          </p>
          <div className="pt-2">
            <p className="mb-2 text-zinc-400">{t("footer.social")}</p>
            <div className="flex flex-wrap items-center gap-3">
              {socialLinks.map(({ href, label, Icon }) => (
                <a
                  key={href}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={label}
                  title={label}
                  className="rounded-md p-1.5 text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-white"
                >
                  <Icon className="h-5 w-5" />
                </a>
              ))}
            </div>
          </div>
        </div>

        <div className="text-sm sm:text-right">
          <a
            href="https://www.uni-marburg.de/de/impressum"
            target="_blank"
            rel="noopener noreferrer"
            className="underline-offset-4 hover:text-white hover:underline"
          >
            {t("footer.impressum")}
          </a>
        </div>
      </div>
    </footer>
  );
}
