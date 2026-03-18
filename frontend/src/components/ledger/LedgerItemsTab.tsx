"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Search, Package, TrendingUp } from "lucide-react";
import { formatDateForDisplay } from "@/lib/date-utils";

interface LedgerItem {
    item_name: string;
    total_qty: number;
    total_amount: number;
    last_date: string;
    avg_rate: number;
}

interface LedgerItemsTabProps {
    ledgerId: number;
}

export function LedgerItemsTab({ ledgerId }: LedgerItemsTabProps) {
    const [items, setItems] = useState<LedgerItem[]>([]);
    const [filteredItems, setFilteredItems] = useState<LedgerItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");

    useEffect(() => {
        const fetchItems = async () => {
            setLoading(true);
            try {
                const data = await api.get(`/api/ledgers/${ledgerId}/items`);
                setItems(data.items || []);
                setFilteredItems(data.items || []);
            } catch (error) {
                console.error("Failed to fetch items", error);
            } finally {
                setLoading(false);
            }
        };

        fetchItems();
    }, [ledgerId]);

    useEffect(() => {
        if (!search) {
            setFilteredItems(items);
        } else {
            const lower = search.toLowerCase();
            setFilteredItems(items.filter(i =>
                i.item_name.toLowerCase().includes(lower)
            ));
        }
    }, [search, items]);

    const formatCurrency = (val: number) => {
        return val.toLocaleString('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 2
        });
    };

    if (loading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading items analysis...</div>;

    if (items.length === 0) {
        return (
            <div className="p-12 text-center border-2 border-dashed rounded-lg bg-muted/10">
                <Package className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                <p className="text-muted-foreground font-medium">No inventory items found for this ledger.</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Search Bar */}
            <div className="flex items-center gap-4 p-4 bg-muted/20 rounded-lg border">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search Items..."
                        className="pl-9 bg-white"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
            </div>

            <div className="rounded-md border bg-white overflow-hidden">
                <Table>
                    <TableHeader className="bg-muted/50">
                        <TableRow>
                            <TableHead>Item Name</TableHead>
                            <TableHead>Last Traded</TableHead>
                            <TableHead className="text-right">Total Quantity</TableHead>
                            <TableHead className="text-right">Avg Rate</TableHead>
                            <TableHead className="text-right">Total Amount</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {filteredItems.map((item, idx) => (
                            <TableRow key={idx} className="hover:bg-muted/10">
                                <TableCell className="font-medium">
                                    <div className="flex items-center gap-2">
                                        <Package className="h-4 w-4 text-blue-500" />
                                        {item.item_name}
                                    </div>
                                </TableCell>
                                <TableCell className="text-muted-foreground">
                                    {item.last_date ? formatDateForDisplay(new Date(item.last_date)) : "-"}
                                </TableCell>
                                <TableCell className="text-right font-mono">
                                    {item.total_qty} <span className="text-xs text-muted-foreground">units</span>
                                </TableCell>
                                <TableCell className="text-right font-mono text-muted-foreground">
                                    {formatCurrency(item.avg_rate)}
                                </TableCell>
                                <TableCell className="text-right font-mono font-medium text-foreground">
                                    {formatCurrency(item.total_amount)}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}
