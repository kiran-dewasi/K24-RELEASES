
import { Suspense } from "react";
import InvoicesPageClient from "@/components/invoices/InvoicesPageClient";
import { Loader2 } from "lucide-react";

export default function InvoicesPage() {
    return (
        <Suspense fallback={<div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>}>
            <InvoicesPageClient />
        </Suspense>
    );
}
