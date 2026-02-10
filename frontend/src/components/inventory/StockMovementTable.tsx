'use client';

import React from 'react';
import { StockMovement } from '@/types/inventory';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { ArrowDownLeft, ArrowUpRight } from "lucide-react"

interface StockMovementTableProps {
    movements: StockMovement[];
    isLoading?: boolean;
}

export function StockMovementTable({ movements, isLoading }: StockMovementTableProps) {
    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 2
        }).format(val);
    };

    const formatDate = (dateStr: string) => {
        try {
            // Parse YYYYMMDD
            if (dateStr.length === 8) {
                const y = dateStr.substring(0, 4);
                const m = dateStr.substring(4, 6);
                const d = dateStr.substring(6, 8);
                return new Date(`${y}-${m}-${d}`).toLocaleDateString('en-IN', {
                    day: 'numeric', month: 'short', year: 'numeric'
                });
            }
            return new Date(dateStr).toLocaleDateString();
        } catch {
            return dateStr;
        }
    };

    if (isLoading) {
        return <div className="text-center p-8 text-muted-foreground">Loading history...</div>
    }

    if (movements.length === 0) {
        return <div className="text-center p-8 text-muted-foreground border rounded-lg">No stock movements found for this period.</div>
    }

    return (
        <div className="rounded-md border bg-white shadow-sm overflow-hidden">
            <Table>
                <TableHeader className="bg-muted/50">
                    <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Particulars</TableHead>
                        <TableHead className="text-right">Quantity</TableHead>
                        <TableHead className="text-right">Rate</TableHead>
                        <TableHead className="text-right">Value</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {movements.map((move, index) => (
                        <TableRow key={index} className="hover:bg-muted/5">
                            <TableCell className="font-medium text-xs text-muted-foreground">
                                {formatDate(move.date)}
                            </TableCell>
                            <TableCell>
                                <div className="flex items-center gap-2">
                                    {move.type === 'In' ? (
                                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                                            <ArrowDownLeft className="mr-1 h-3 w-3" /> In
                                        </Badge>
                                    ) : (
                                        <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                                            <ArrowUpRight className="mr-1 h-3 w-3" /> Out
                                        </Badge>
                                    )}
                                </div>
                            </TableCell>
                            <TableCell>
                                <div className="flex flex-col">
                                    {move.item_name && <span className="text-sm font-semibold text-primary/80">{move.item_name}</span>}
                                    <span className="text-sm font-medium">{move.party || "Adjustment"}</span>
                                    <span className="text-xs text-muted-foreground">{move.reference || "No Ref"}</span>
                                </div>
                            </TableCell>
                            <TableCell className="text-right font-medium">
                                <span className={move.type === 'In' ? 'text-green-600' : 'text-red-600'}>
                                    {move.type === 'In' ? '+' : '-'}{Math.abs(move.quantity)}
                                </span>
                            </TableCell>
                            <TableCell className="text-right text-muted-foreground text-sm">
                                {formatCurrency(move.rate)}
                            </TableCell>
                            <TableCell className="text-right font-medium">
                                {formatCurrency(move.amount)}
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
