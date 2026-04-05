'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { api } from "@/lib/api";
import { InventoryTable } from '@/components/inventory/InventoryTable';
import { InventoryStats } from '@/components/inventory/InventoryStats';
import { InventoryFilters } from '@/components/inventory/InventoryFilters';
import { InventoryItem, InventorySummary } from '@/types/inventory';
import { Button } from '@/components/ui/button';
import { Plus, RefreshCw, FileDown, FileUp, Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useToast } from "@/components/ui/use-toast";
import InventoryDetailPage from '@/components/pages/InventoryDetailPage';
import { downloadReportFile } from '@/lib/fileDownload';

function InventoryContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const { toast } = useToast();
    const itemParam = searchParams.get('item');

    // If ?item= is set, show detail page
    if (itemParam) {
        return <InventoryDetailPage />;
    }

    return <InventoryListPage />;
}

function InventoryListPage() {
    const router = useRouter();
    const { toast } = useToast();

    const [items, setItems] = useState<InventoryItem[]>([]);
    const [summary, setSummary] = useState<InventorySummary>({
        totalItems: 0,
        totalValue: 0,
        lowStockCount: 0,
        outOfStockCount: 0,
        timestamp: new Date().toISOString()
    });

    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [exportingInventory, setExportingInventory] = useState(false);

    // Filters
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [categoryFilter, setCategoryFilter] = useState('all');
    const [categories, setCategories] = useState<string[]>([]);

    const fetchInventory = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (searchQuery) params.append("search", searchQuery);
            if (statusFilter !== 'all') params.append("status", statusFilter);
            if (categoryFilter !== 'all') params.append("category", categoryFilter);

            const [itemsData, summaryData] = await Promise.all([
                api.get(`/api/inventory?${params.toString()}`),
                api.get('/api/inventory/summary')
            ]);

            setItems(itemsData.items || []);
            const uniqueCats = Array.from(new Set((itemsData.items || []).map((i: any) => i.category || 'General')));
            setCategories(uniqueCats as string[]);

            setSummary(summaryData);

        } catch (error) {
            console.error("Failed to fetch inventory:", error);
            toast({
                title: "Error",
                description: "Failed to load inventory data. Please try again.",
                variant: "destructive",
            });
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        const timer = setTimeout(() => {
            fetchInventory();
        }, 300);
        return () => clearTimeout(timer);
    }, [searchQuery, statusFilter, categoryFilter]);

    const handleRefresh = () => {
        setRefreshing(true);
        fetchInventory();
    };

    const handleClearFilters = () => {
        setSearchQuery('');
        setStatusFilter('all');
        setCategoryFilter('all');
    };

    const handleInventoryExport = async () => {
        setExportingInventory(true);
        try {
            await downloadReportFile({
                slug: 'balance-sheet',
                format: 'excel'
            });
        } catch (err: any) {
            toast({
                title: 'Export failed',
                description: err?.message || 'Could not generate export. Is the backend running?',
                variant: 'destructive',
            });
        } finally {
            setExportingInventory(false);
        }
    };

    return (
        <div className="flex flex-col space-y-6 md:p-8 p-4 pt-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Inventory Management</h1>
                    <p className="text-muted-foreground">Track stock levels, valuations, and movements across all items.</p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
                        <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                        Sync
                    </Button>
                    <Button variant="outline" size="sm">
                        <FileUp className="mr-2 h-4 w-4" />
                        Import
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleInventoryExport} disabled={exportingInventory} id="btn-inventory-export">
                        {exportingInventory
                            ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            : <FileDown className="mr-2 h-4 w-4" />}
                        Export
                    </Button>
                    <Button size="sm" onClick={() => router.push('/inventory/new')} className="bg-primary text-primary-foreground shadow hover:bg-primary/90">
                        <Plus className="mr-2 h-4 w-4" /> Add Item
                    </Button>
                </div>
            </div>

            <InventoryStats summary={summary} loading={loading && !items.length} />

            <div className="space-y-4">
                <InventoryFilters
                    searchQuery={searchQuery}
                    onSearchChange={setSearchQuery}
                    statusFilter={statusFilter}
                    onStatusFilterChange={setStatusFilter}
                    categoryFilter={categoryFilter}
                    onCategoryChange={setCategoryFilter}
                    onClearFilters={handleClearFilters}
                    categories={categories}
                />

                <InventoryTable items={items} isLoading={loading} />
            </div>
        </div>
    );
}

export default function Page() {
    return (
        <Suspense fallback={
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
            </div>
        }>
            <InventoryContent />
        </Suspense>
    );
}
