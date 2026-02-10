
import { Suspense } from "react";
import DashboardClient from "@/components/dashboard/DashboardClient";
import DeviceGuard from "@/components/auth/DeviceGuard";
import { Loader2 } from "lucide-react";

export default function DashboardPage() {
  return (
    <DeviceGuard>
      <Suspense fallback={<div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>}>
        <DashboardClient />
      </Suspense>
    </DeviceGuard>
  );
}
