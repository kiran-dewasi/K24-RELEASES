import LedgerProfilePage from "@/components/pages/LedgerProfilePage";
import { Suspense } from "react";
import { Loader2 } from "lucide-react";

export async function generateStaticParams() {
    return [{ ledger_id: 'default' }];
}

export const dynamicParams = false;

export default function Page() {
    return (
        <Suspense fallback={
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
            </div>
        }>
            <LedgerProfilePage />
        </Suspense>
    );
}
