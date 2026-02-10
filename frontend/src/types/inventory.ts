export interface InventoryItem {
    name: string;
    parent?: string;
    category: string;
    units: string;
    closing_balance: number;
    value: number;
    rate: number;
    status: "In Stock" | "Low Stock" | "Out of Stock";
    reorder_level: number;
    last_updated: string;
    sku?: string;
}

export interface InventorySummary {
    totalItems: number;
    totalValue: number;
    lowStockCount: number;
    outOfStockCount: number;
    timestamp: string;
}

export interface StockMovement {
    date: string;
    type: "In" | "Out";
    quantity: number;
    rate: number;
    amount: number;
    reference?: string;
    party?: string;
    item_name?: string;
}
