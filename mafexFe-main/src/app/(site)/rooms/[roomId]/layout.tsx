import { ProtectedRoute } from "@/components/shared/ProtectedRoute";

export default function RoomDetailLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute>{children}</ProtectedRoute>;
}
