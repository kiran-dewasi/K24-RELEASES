import LedgerProfilePage from "@/components/pages/LedgerProfilePage";

export async function generateStaticParams() {
    return [{ ledger_id: 'default' }];
}

export const dynamicParams = false;

export default function Page() {
    return <LedgerProfilePage />;
}
