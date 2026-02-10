
import { Suspense } from "react";
import DayBookClient from "@/components/daybook/DayBookClient";
import { Loader2 } from "lucide-react";

export default function DayBookPage() {
    return (
        <Suspense fallback={<div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>}>
            <DayBookClient />
        </Suspense>
    );
}
