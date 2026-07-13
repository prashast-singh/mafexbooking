import { AppHeader } from "@/components/layout/AppHeader";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <AppHeader />
      <main className="min-h-[calc(100dvh-3.5rem)]">{children}</main>
    </>
  );
}
