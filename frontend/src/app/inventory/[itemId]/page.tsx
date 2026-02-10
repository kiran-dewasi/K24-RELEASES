import InventoryDetailPage from "@/components/pages/InventoryDetailPage";

export async function generateStaticParams() {
    return [{ itemId: 'default' }];
}

export const dynamicParams = false;

export default function Page() {
    return <InventoryDetailPage />;
}
