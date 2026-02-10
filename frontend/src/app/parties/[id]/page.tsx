import PartyProfilePage from "@/components/pages/PartyPage";

export async function generateStaticParams() {
    return [{ id: 'default' }];
}

export const dynamicParams = false;

export default function Page() {
    return <PartyProfilePage />;
}
