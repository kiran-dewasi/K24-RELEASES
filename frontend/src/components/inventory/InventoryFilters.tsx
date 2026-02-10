'use client';

import React from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search, X, Filter } from 'lucide-react';

interface InventoryFiltersProps {
    searchQuery: string;
    onSearchChange: (value: string) => void;
    statusFilter: string;
    onStatusFilterChange: (value: string) => void;
    categoryFilter: string;
    onCategoryChange: (value: string) => void;
    onClearFilters: () => void;
    categories: string[];
}

export function InventoryFilters({
    searchQuery,
    onSearchChange,
    statusFilter,
    onStatusFilterChange,
    categoryFilter,
    onCategoryChange,
    onClearFilters,
    categories
}: InventoryFiltersProps) {
    return (
        <div className="flex flex-col sm:flex-row gap-4 py-4">
            <div className="relative flex-1">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                    placeholder="Search items by name, SKU..."
                    value={searchQuery}
                    onChange={(e) => onSearchChange(e.target.value)}
                    className="pl-8"
                />
            </div>

            <Select value={statusFilter} onValueChange={onStatusFilterChange}>
                <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Stock Status" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="in_stock">In Stock</SelectItem>
                    <SelectItem value="low_stock">Low Stock</SelectItem>
                    <SelectItem value="out_of_stock">Out of Stock</SelectItem>
                </SelectContent>
            </Select>

            <Select value={categoryFilter} onValueChange={onCategoryChange}>
                <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    {categories.map((cat) => (
                        <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                </SelectContent>
            </Select>

            <Button variant="ghost" onClick={onClearFilters} className="px-3" title="Clear Filters">
                <X className="h-4 w-4" />
            </Button>
        </div>
    );
}
