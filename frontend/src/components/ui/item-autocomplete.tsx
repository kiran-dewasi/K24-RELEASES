'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { apiClient } from '@/lib/api-config';
import { Package, ChevronRight, AlertCircle } from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface StockItem {
    id: number;
    name: string;
    alias?: string;
    unit: string;
    selling_price: number;
    cost_price: number;
    mrp?: number;
    gst_rate: number;
    hsn_code?: string;
    stock: number;
    stock_group?: string;
}

interface ItemAutocompleteProps {
    /** The current text value displayed in the input */
    value: string;
    /** Called on every keystroke */
    onChange: (value: string) => void;
    /** Called when user picks an item from the dropdown */
    onSelect?: (item: StockItem | null) => void;
    placeholder?: string;
    disabled?: boolean;
    className?: string;
    /** How long to debounce API calls (ms) */
    debounceMs?: number;
    /** Show stock quantity badge in dropdown? */
    showStock?: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helper — format currency ₹
// ─────────────────────────────────────────────────────────────────────────────

function fmtCurrency(n: number) {
    return `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function ItemAutocomplete({
    value,
    onChange,
    onSelect,
    placeholder = 'Type item name to search…',
    disabled = false,
    className = '',
    debounceMs = 250,
    showStock = true,
}: ItemAutocompleteProps) {
    const [suggestions, setSuggestions] = useState<StockItem[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [showDrop, setShowDrop] = useState(false);
    const [activeIdx, setActiveIdx] = useState(-1);
    const [noResults, setNoResults] = useState(false);

    const inputRef = useRef<HTMLInputElement>(null);
    const dropRef = useRef<HTMLDivElement>(null);
    const timerRef = useRef<NodeJS.Timeout | null>(null);

    // ── Fetch from backend ────────────────────────────────────────────────
    const fetchItems = useCallback(async (q: string) => {
        if (q.trim().length < 1) {
            setSuggestions([]);
            setShowDrop(false);
            setNoResults(false);
            return;
        }

        setIsLoading(true);
        setNoResults(false);
        try {
            const res = await apiClient(`/api/items/search?q=${encodeURIComponent(q)}&limit=10`);
            if (res.ok) {
                const data = await res.json();
                const items: StockItem[] = data.items || [];
                setSuggestions(items);
                setShowDrop(true);
                setActiveIdx(-1);
                setNoResults(items.length === 0);
            } else {
                setSuggestions([]);
                setNoResults(true);
            }
        } catch {
            setSuggestions([]);
            setNoResults(false); // network error — don't show "no results"
        } finally {
            setIsLoading(false);
        }
    }, []);

    // ── Debounce ──────────────────────────────────────────────────────────
    useEffect(() => {
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => fetchItems(value), debounceMs);
        return () => { if (timerRef.current) clearTimeout(timerRef.current); };
    }, [value, fetchItems, debounceMs]);

    // ── Input change ──────────────────────────────────────────────────────
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        onChange(e.target.value);
        if (onSelect) onSelect(null); // clear any previous selection
    };

    // ── Pick item ─────────────────────────────────────────────────────────
    const handleSelect = (item: StockItem) => {
        onChange(item.name);
        setSuggestions([]);
        setShowDrop(false);
        setNoResults(false);
        if (onSelect) onSelect(item);
    };

    // ── Keyboard nav ──────────────────────────────────────────────────────
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!showDrop || suggestions.length === 0) return;
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setActiveIdx(i => Math.min(i + 1, suggestions.length - 1));
                break;
            case 'ArrowUp':
                e.preventDefault();
                setActiveIdx(i => Math.max(i - 1, -1));
                break;
            case 'Enter':
                e.preventDefault();
                if (activeIdx >= 0) handleSelect(suggestions[activeIdx]);
                break;
            case 'Escape':
                setShowDrop(false);
                setActiveIdx(-1);
                break;
        }
    };

    // ── Close on outside click ────────────────────────────────────────────
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (
                dropRef.current && !dropRef.current.contains(e.target as Node) &&
                inputRef.current && !inputRef.current.contains(e.target as Node)
            ) {
                setShowDrop(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    // ── Stock colour ──────────────────────────────────────────────────────
    const stockColor = (qty: number) => {
        if (qty <= 0) return 'text-red-500';
        if (qty < 10) return 'text-orange-500';
        return 'text-emerald-600';
    };

    // ─────────────────────────────────────────────────────────────────────
    return (
        <div className={`relative ${className}`}>
            {/* ── Input ── */}
            <div className="relative">
                <input
                    ref={inputRef}
                    type="text"
                    value={value}
                    onChange={handleChange}
                    onKeyDown={handleKeyDown}
                    onFocus={() => value.length >= 1 && suggestions.length > 0 && setShowDrop(true)}
                    placeholder={placeholder}
                    disabled={disabled}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-8 text-sm"
                />

                {/* Spinner */}
                {isLoading && (
                    <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
                        <div className="w-3.5 h-3.5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                )}

                {/* Package icon when idle */}
                {!isLoading && (
                    <Package className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
                )}
            </div>

            {/* ── Dropdown ── */}
            {showDrop && (
                <div
                    ref={dropRef}
                    className="absolute z-50 left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-xl max-h-72 overflow-y-auto"
                >
                    {suggestions.length > 0 ? (
                        <>
                            {/* Header hint */}
                            <div className="px-3 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100 bg-gray-50">
                                {suggestions.length} item{suggestions.length !== 1 ? 's' : ''} found — ↑↓ to navigate · Enter to select
                            </div>

                            {suggestions.map((item, idx) => (
                                <div
                                    key={item.id}
                                    onMouseDown={() => handleSelect(item)}
                                    className={`
                                        px-3 py-2.5 cursor-pointer border-b border-gray-50 last:border-0
                                        hover:bg-blue-50 transition-colors flex items-center gap-3
                                        ${activeIdx === idx ? 'bg-blue-50' : ''}
                                    `}
                                >
                                    {/* Icon */}
                                    <div className="flex-shrink-0 w-7 h-7 rounded-md bg-indigo-100 flex items-center justify-center">
                                        <Package className="w-3.5 h-3.5 text-indigo-600" />
                                    </div>

                                    {/* Details */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between gap-2">
                                            <span className="font-medium text-sm text-gray-900 truncate">{item.name}</span>
                                            <span className="flex-shrink-0 text-sm font-semibold text-blue-700">
                                                {fmtCurrency(item.selling_price)}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                                            {/* Unit */}
                                            <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                                                {item.unit}
                                            </span>
                                            {/* GST */}
                                            {item.gst_rate > 0 && (
                                                <span className="text-xs text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">
                                                    GST {item.gst_rate}%
                                                </span>
                                            )}
                                            {/* HSN */}
                                            {item.hsn_code && (
                                                <span className="text-xs text-gray-400">
                                                    HSN {item.hsn_code}
                                                </span>
                                            )}
                                            {/* Stock */}
                                            {showStock && (
                                                <span className={`text-xs font-medium ${stockColor(item.stock)}`}>
                                                    {item.stock <= 0
                                                        ? '⚠ Out of stock'
                                                        : `${item.stock} ${item.unit} in stock`}
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    <ChevronRight className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" />
                                </div>
                            ))}
                        </>
                    ) : noResults ? (
                        <div className="flex items-center gap-2 px-4 py-3 text-sm text-gray-500">
                            <AlertCircle className="w-4 h-4 text-orange-400" />
                            <span>No items found for <strong>&quot;{value}&quot;</strong>. You can still type a custom description.</span>
                        </div>
                    ) : null}
                </div>
            )}
        </div>
    );
}

export default ItemAutocomplete;
