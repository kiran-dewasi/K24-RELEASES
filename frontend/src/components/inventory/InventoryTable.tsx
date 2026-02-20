'use client';

import React from 'react';
import { InventoryItem } from '@/types/inventory';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { MoreHorizontal, Pencil, Trash, Eye, History } from "lucide-react"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Checkbox } from "@/components/ui/checkbox"

interface InventoryTableProps {
    items: InventoryItem[];
    isLoading?: boolean;
}

export function InventoryTable({ items, isLoading }: InventoryTableProps) {
    const router = useRouter();

    const getStatusColor = (status: string) => {
        switch (status.toLowerCase()) {
            case 'in stock': return 'bg-green-100 text-green-800 hover:bg-green-200';
            case 'low stock': return 'bg-orange-100 text-orange-800 hover:bg-orange-200';
            case 'out of stock': return 'bg-red-100 text-red-800 hover:bg-red-200';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 2
        }).format(val);
    };

    if (isLoading) {
        return <div className="p-8 text-center text-muted-foreground">Loading inventory...</div>;
    }

    if (items.length === 0) {
        return <div className="p-12 text-center border rounded-lg bg-muted/10">
            <h3 className="text-lg font-medium text-foreground">No items found</h3>
            <p className="text-muted-foreground mt-1">Try adjusting your filters or search query.</p>
        </div>
    }

    return (
        <div className="rounded-md border bg-white shadow-sm overflow-hidden">
            <Table>
                <TableHeader className="bg-muted/50">
                    <TableRow>
                        <TableHead className="w-[50px] text-center">#</TableHead>
                        <TableHead>Item Name</TableHead>
                        <TableHead>Category</TableHead>
                        <TableHead className="text-right">Stock</TableHead>
                        <TableHead className="text-right">Rate</TableHead>
                        <TableHead className="text-right">Value</TableHead>
                        <TableHead className="text-center">Status</TableHead>
                        <TableHead className="w-[80px]"></TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {items.map((item, index) => (
                        <TableRow key={item.name} className="hover:bg-muted/5 group transition-colors">
                            <TableCell className="text-center text-muted-foreground text-xs">
                                {index + 1}
                            </TableCell>
                            <TableCell>
                                <div className="flex flex-col">
                                    <span
                                        className="font-medium text-foreground cursor-pointer hover:text-primary transition-colors"
                                        onClick={() => router.push(`/inventory?item=${encodeURIComponent(item.name)}`)}
                                    >
                                        {item.name}
                                    </span>
                                    {item.sku && <span className="text-xs text-muted-foreground">{item.sku}</span>}
                                </div>
                            </TableCell>
                            <TableCell>
                                <Badge variant="outline" className="font-normal text-xs bg-slate-50">
                                    {item.category}
                                </Badge>
                            </TableCell>
                            <TableCell className="text-right font-medium">
                                {item.closing_balance} <span className="text-muted-foreground text-xs font-normal">{item.units}</span>
                            </TableCell>
                            <TableCell className="text-right text-muted-foreground">
                                {formatCurrency(item.rate)}
                            </TableCell>
                            <TableCell className="text-right font-bold text-foreground">
                                {formatCurrency(item.value)}
                            </TableCell>
                            <TableCell className="text-center">
                                <Badge className={cn("capitalize shadow-none font-medium", getStatusColor(item.status))}>
                                    {item.status}
                                </Badge>
                            </TableCell>
                            <TableCell>
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button variant="ghost" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <span className="sr-only">Open menu</span>
                                            <MoreHorizontal className="h-4 w-4" />
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                        <DropdownMenuItem onClick={() => router.push(`/inventory?item=${encodeURIComponent(item.name)}`)}>
                                            <Eye className="mr-2 h-4 w-4" /> View Details
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => router.push(`/inventory?item=${encodeURIComponent(item.name)}&tab=movements`)}>
                                            <History className="mr-2 h-4 w-4" /> History
                                        </DropdownMenuItem>
                                        <DropdownMenuSeparator />
                                        <DropdownMenuItem>
                                            <Pencil className="mr-2 h-4 w-4" /> Edit
                                        </DropdownMenuItem>
                                        <DropdownMenuItem className="text-red-600">
                                            <Trash className="mr-2 h-4 w-4" /> Delete
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
