'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { InventoryItem, StockMovement } from '@/types/inventory';
import { api } from "@/lib/api";
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { StockMovementTable } from '@/components/inventory/StockMovementTable';
import { ArrowLeft, Edit, Trash, Package, IndianRupee, Activity, Box, Loader2 } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useToast } from "@/components/ui/use-toast";




function InventoryDetailContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { toast } = useToast();

    const itemName = searchParams.get('item') ? decodeURIComponent(searchParams.get('item')!) : '';

    const [item, setItem] = useState<InventoryItem | null>(null);
    const [movements, setMovements] = useState<StockMovement[]>([]);
    const [loading, setLoading] = useState(true);

    const [activeTab, setActiveTab] = useState("overview");

    useEffect(() => {
        const fetchDetails = async () => {
            if (!itemName) return;
            try {
                setLoading(true);
                // Fetch Item Details
                const data = await api.get(`/api/inventory/${encodeURIComponent(itemName)}`);
                setItem(data.item);

                // Fetch Movements
                const mData = await api.get(`/api/inventory/${encodeURIComponent(itemName)}/movements`);
                setMovements(mData.movements || []);

            } catch (error) {
                console.error(error);
                toast({
                    title: "Error",
                    description: "Could not load item details.",
                    variant: "destructive"
                });
                // Fallback or redirect
            } finally {
                setLoading(false);
            }
        };

        if (itemName && itemName !== 'default') fetchDetails();
    }, [itemName]);

    if (itemName === 'default') {
        return <div className="p-8 text-center text-muted-foreground">Select an inventory item to view details.</div>;
    }

    if (loading) return <div className="p-8 text-center">Loading details for {itemName || 'item'}...</div>;
    if (!item) return <div className="p-8 text-center">{itemName ? 'Item not found' : 'No item selected'}</div>;

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 2
        }).format(val);
    };

    return (
        <div className="flex flex-col space-y-6 md:p-8 p-4 pt-6 bg-slate-50 min-h-screen">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <Button variant="outline" size="icon" onClick={() => router.back()}>
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-3">
                            {item.name}
                            <Badge variant={item.status === 'In Stock' ? 'default' : 'destructive'}>
                                {item.status}
                            </Badge>
                        </h1>
                        <p className="text-muted-foreground text-sm flex items-center gap-2 mt-1">
                            Category: <span className="font-medium text-foreground">{item.category}</span>
                            {item.sku && <span className="text-xs bg-slate-200 px-2 py-0.5 rounded">SKU: {item.sku}</span>}
                        </p>
                    </div>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline">
                        <Edit className="mr-2 h-4 w-4" /> Edit Item
                    </Button>
                </div>
            </div>

            {/* Overview Cards */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Current Stock</CardTitle>
                        <Package className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{item.closing_balance} <span className="text-base font-normal text-muted-foreground">{item.units}</span></div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Valued at {formatCurrency(item.value)}
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Average Rate</CardTitle>
                        <IndianRupee className="h-4 w-4 text-green-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{formatCurrency(item.rate)}</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Per {item.units}
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Stock Status</CardTitle>
                        <Activity className="h-4 w-4 text-orange-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-foreground capitalize">
                            {item.status}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Reorder Level: {item.reorder_level} {item.units}
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Tabs Config */}
            <Tabs defaultValue="overview" className="w-full" value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="w-full justify-start border-b rounded-none h-auto p-0 bg-transparent space-x-6">
                    <TabsTrigger
                        value="overview"
                        className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 py-2"
                    >
                        Overview
                    </TabsTrigger>
                    <TabsTrigger
                        value="movements"
                        className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 py-2"
                    >
                        Stock Movements
                    </TabsTrigger>
                    <TabsTrigger
                        value="analytics"
                        disabled
                        className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 py-2"
                    >
                        Analytics (Coming Soon)
                    </TabsTrigger>
                </TabsList>

                <div className="mt-6">
                    <TabsContent value="overview" className="space-y-4">
                        <div className="grid gap-4 md:grid-cols-2">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Item Information</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div className="text-muted-foreground">Item Name</div>
                                        <div className="font-medium">{item.name}</div>

                                        <div className="text-muted-foreground">Category</div>
                                        <div className="font-medium">{item.category}</div>

                                        <div className="text-muted-foreground">Base Unit</div>
                                        <div className="font-medium uppercase">{item.units}</div>

                                        <div className="text-muted-foreground">Parent Group</div>
                                        <div className="font-medium">{item.parent || "-"}</div>
                                    </div>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader>
                                    <CardTitle>Pricing & Valuation</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div className="text-muted-foreground">Standard Cost</div>
                                        <div className="font-medium">-</div>

                                        <div className="text-muted-foreground">Standard Price</div>
                                        <div className="font-medium">-</div>

                                        <div className="text-muted-foreground">Total Value</div>
                                        <div className="font-medium text-lg text-primary">{formatCurrency(item.value)}</div>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </TabsContent>

                    <TabsContent value="movements">
                        <Card>
                            <CardHeader>
                                <CardTitle>Transaction History</CardTitle>
                                <CardDescription>Recent stock in/out movements for this item.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <StockMovementTable movements={movements} />
                            </CardContent>
                        </Card>
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    );
}

export default function InventoryDetailPage() {
    return (
        <Suspense fallback={
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
            </div>
        }>
            <InventoryDetailContent />
        </Suspense>
    );
}
