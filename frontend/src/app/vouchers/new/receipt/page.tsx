
import { Suspense } from "react";
import NewReceiptClient from "@/components/vouchers/NewReceiptClient";
import { Loader2 } from "lucide-react";

export default function NewReceiptPage() {
    return (
        <Suspense fallback={<div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>}>
            <NewReceiptClient />
        </Suspense>
    );
}
