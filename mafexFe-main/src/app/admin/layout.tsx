import { AdminSidebar } from "@/components/layout/AdminSidebar";
import { AdminRoute } from "@/components/shared/AdminRoute";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminRoute>
      <div className="flex min-h-screen">
        <AdminSidebar />
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </AdminRoute>
  );
}
