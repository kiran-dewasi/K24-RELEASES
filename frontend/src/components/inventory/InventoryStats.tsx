'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Package, IndianRupee, AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react';
import { InventorySummary } from '@/types/inventory';

interface InventoryStatsProps {
    summary: InventorySummary;
    loading?: boolean;
}

export function InventoryStats({ summary, loading }: InventoryStatsProps) {
    if (loading) {
        return (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {[1, 2, 3, 4].map((i) => (
                    <Card key={i} className="animate-pulse">
                        <CardHeader className="h-20 bg-muted/50" />
                        <CardContent className="h-12" />
                    </Card>
                ))}
            </div>
        );
    }

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Total Items</CardTitle>
                    <Package className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{summary.totalItems}</div>
                    <p className="text-xs text-muted-foreground">
                        Active items in inventory
                    </p>
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Total Stock Value</CardTitle>
                    <IndianRupee className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">
                        ₹{summary.totalValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </div>
                    <p className="text-xs text-muted-foreground">
                        Current valuation
                    </p>
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Low Stock Items</CardTitle>
                    <AlertTriangle className="h-4 w-4 text-orange-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold text-orange-600">{summary.lowStockCount}</div>
                    <p className="text-xs text-muted-foreground">
                        Items below reorder level
                    </p>
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Out of Stock</CardTitle>
                    <TrendingDown className="h-4 w-4 text-red-500" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold text-red-600">{summary.outOfStockCount}</div>
                    <p className="text-xs text-muted-foreground">
                        Items with 0 quantity
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
