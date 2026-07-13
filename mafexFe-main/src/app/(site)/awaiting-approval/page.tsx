"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { FIND_ROOM_PATH } from "@/lib/routes";
import { useAuth } from "@/hooks/use-auth";

export default function AwaitingApprovalPage() {
  const { user, loading, logout, refresh } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (user.approval_status === "approved") {
      router.replace(FIND_ROOM_PATH);
    }
  }, [loading, user, router]);

  if (loading || !user) return <LoadingState />;

  if (user.approval_status === "rejected") {
    return (
      <div className="mx-auto max-w-lg px-4 py-12">
        <PageHeader
          title="Account not approved"
          description="Your signup was reviewed and could not be approved. Contact your administrator if you think this is a mistake."
        />
        <Button variant="outline" onClick={() => logout()}>
          Log out
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg px-4 py-12">
      <PageHeader
        title="Awaiting approval"
        description="An administrator needs to approve your account before you can book rooms. You can still browse the catalog."
      />
      <div className="flex flex-wrap gap-2">
        <Link href={FIND_ROOM_PATH} className={cn(buttonVariants())}>
          Browse rooms
        </Link>
        <Button variant="outline" onClick={() => void refresh()}>
          Refresh status
        </Button>
        <Button variant="ghost" onClick={() => logout()}>
          Log out
        </Button>
      </div>
    </div>
  );
}
