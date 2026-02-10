
import { Suspense } from "react";
import NewSalesClient from "@/components/vouchers/NewSalesClient";
import { Loader2 } from "lucide-react";

export default function NewSalesInvoicePage() {
    return (
        <Suspense fallback={<div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>}>
            <NewSalesClient />
        </Suspense>
    );
}
