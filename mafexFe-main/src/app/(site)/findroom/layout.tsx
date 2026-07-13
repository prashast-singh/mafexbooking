import { ProtectedRoute } from "@/components/shared/ProtectedRoute";

export default function FindRoomLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute>{children}</ProtectedRoute>;
}
