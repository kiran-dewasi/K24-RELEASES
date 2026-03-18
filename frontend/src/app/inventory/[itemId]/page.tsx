"use client"
import { useParams } from "next/navigation"
import InventoryDetailPage from "@/components/pages/InventoryDetailPage"

export default function InventoryItemPage() {
    const params = useParams()
    const itemName = decodeURIComponent(params.itemId as string)
    return <InventoryDetailPage />
}
