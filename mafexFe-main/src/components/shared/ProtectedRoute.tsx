"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { LoadingState } from "@/components/shared/LoadingState";
import { getStoredToken } from "@/lib/api/client";
import { useAuth } from "@/hooks/use-auth";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!getStoredToken()) {
      router.replace("/login");
    }
  }, [loading, router]);

  if (loading) return <LoadingState />;
  if (!getStoredToken()) return null;
  return <>{children}</>;
}
