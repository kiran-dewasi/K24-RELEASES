'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Skeleton } from "@/components/ui/skeleton";
import { Search, Package, TrendingUp, TrendingDown, Filter } from 'lucide-react';

export default function ItemsListPage() {
    const [items, setItems] = useState<any[]>([]);
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const timeoutId = setTimeout(() => {
            fetchItems();
        }, 300); // Debounce search
        return () => clearTimeout(timeoutId);
    }, [search]);

    const fetchItems = async () => {
        setLoading(true);
        try {
            const query = search ? `?search=${encodeURIComponent(search)}` : '';
            const res = await fetch(`/api/items${query}`);
            if (!res.ok) throw new Error('Failed to fetch items');
            const data = await res.json();
            setItems(data.items || []);
        } catch (error) {
            console.error(error);
            setItems([]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50/50 p-6 md:p-8">
            <div className="max-w-7xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Inventory Items</h1>
                        <p className="text-gray-500 mt-1">Manage stock, track movements, and analyze profitability.</p>
                    </div>
                    <div className="flex gap-2">
                        <button className="flex items-center gap-2 bg-white border border-gray-200 text-gray-700 px-4 py-2.5 rounded-xl hover:bg-gray-50 transition-all shadow-sm font-medium">
                            <Filter size={18} /> Filter
                        </button>
                        <button className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl shadow-lg shadow-blue-600/20 transition-all font-medium flex items-center gap-2">
                            <Package size={18} />
                            Add Item
                        </button>
                    </div>
                </div>

                {/* Search Bar */}
                <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Search className="h-5 w-5 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
                    </div>
                    <input
                        type="text"
                        className="block w-full pl-11 pr-4 py-3.5 bg-white border border-gray-200 rounded-2xl leading-5 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-sm"
                        placeholder="Search items by name, SKU, or category..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>

                {/* Items Grid */}
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {[1, 2, 3, 4, 5, 6].map(i => (
                            <div key={i} className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex gap-4 items-center">
                                        <Skeleton className="h-12 w-12 rounded-xl" />
                                        <div>
                                            <Skeleton className="h-6 w-32 mb-2" />
                                            <Skeleton className="h-4 w-20" />
                                        </div>
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-50">
                                    <div className="space-y-2">
                                        <Skeleton className="h-3 w-16" />
                                        <Skeleton className="h-6 w-24" />
                                    </div>
                                    <div className="space-y-2 flex flex-col items-end">
                                        <Skeleton className="h-3 w-16" />
                                        <Skeleton className="h-6 w-24" />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : items.length === 0 ? (
                    <div className="text-center py-20 bg-white rounded-3xl border border-dashed border-gray-200">
                        <Package className="mx-auto h-12 w-12 text-gray-300 mb-4" />
                        <h3 className="text-lg font-medium text-gray-900">No items found</h3>
                        <p className="text-gray-500">Try adjusting your search query.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {items.map((item) => (
                            <Link
                                key={item.id}
                                href={`/items/${item.id}`}
                                className="group bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-xl hover:shadow-blue-900/5 hover:border-blue-100 transition-all duration-300 relative overflow-hidden"
                            >
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex gap-4 items-center">
                                        <div className="h-12 w-12 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600 group-hover:scale-110 transition-transform duration-300">
                                            <Package size={24} />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-gray-900 line-clamp-1 text-lg group-hover:text-blue-600 transition-colors">
                                                {item.name}
                                            </h3>
                                            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-100 inline-block px-1.5 py-0.5 rounded mt-1">
                                                {item.sku || 'NO SKU'}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-50">
                                    <div>
                                        <p className="text-xs text-gray-400 font-medium mb-1">Stock Level</p>
                                        <div className={`text-lg font-bold flex items-center gap-1.5 ${item.current_stock > 0 ? 'text-gray-900' : 'text-red-500'
                                            }`}>
                                            {item.current_stock?.toLocaleString() || 0}
                                            <span className="text-xs font-normal text-gray-400">{item.unit}</span>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xs text-gray-400 font-medium mb-1">Selling Price</p>
                                        <div className="text-lg font-bold text-gray-900">
                                            ₹{item.sales_rate?.toLocaleString() || 0}
                                        </div>
                                    </div>
                                </div>

                                {/* Hover Indicator */}
                                <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-indigo-500 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-300" />
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
