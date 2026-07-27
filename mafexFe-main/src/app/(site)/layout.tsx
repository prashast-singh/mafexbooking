import { AppHeader } from "@/components/layout/AppHeader";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { HouseRulesGate } from "@/components/shared/HouseRulesGate";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <AppHeader />
      <main className="min-h-[calc(100dvh-3.5rem)]">{children}</main>
      <SiteFooter />
      <HouseRulesGate />
    </>
  );
}
