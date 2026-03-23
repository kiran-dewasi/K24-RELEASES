import InventoryDetailPage from "@/components/pages/InventoryDetailPage"

// For static export, we need at least one path
export async function generateStaticParams() {
    // Return a dummy path that will serve as fallback
    return [{ itemId: '404' }]
}

export default function InventoryItemPage() {
    return <InventoryDetailPage />
}
