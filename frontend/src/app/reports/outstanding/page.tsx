
import { Suspense } from "react";
import OutstandingReportClient from "@/components/reports/OutstandingReportClient";
import { Loader2 } from "lucide-react";

export default function OutstandingReportPage() {
    return (
        <Suspense fallback={<div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>}>
            <OutstandingReportClient />
        </Suspense>
    );
}
