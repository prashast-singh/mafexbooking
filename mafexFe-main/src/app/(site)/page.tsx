"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { LoadingState } from "@/components/shared/LoadingState";
import { getStoredToken } from "@/lib/api/client";
import { FIND_ROOM_PATH } from "@/lib/routes";
import { useAuth } from "@/hooks/use-auth";

export default function HomePage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (loading) return;
    if (user && getStoredToken()) {
      router.replace(FIND_ROOM_PATH);
    } else {
      router.replace("/login");
    }
  }, [user, loading, router]);

  return <LoadingState />;
}
