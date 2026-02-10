
import { Suspense } from "react";
import NewPaymentClient from "@/components/vouchers/NewPaymentClient";
import { Loader2 } from "lucide-react";

export default function NewPaymentPage() {
    return (
        <Suspense fallback={<div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>}>
            <NewPaymentClient />
        </Suspense>
    );
}
