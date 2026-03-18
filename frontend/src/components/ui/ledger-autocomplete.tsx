'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { api } from "@/lib/api";

/**
 * Ledger Autocomplete Component
 * 
 * Provides Tally-like autocomplete for party/ledger selection:
 * - Shows suggestions as user types (3+ characters)
 * - User can select existing ledger OR type new name
 * - New ledgers are auto-created when voucher is saved
 * 
 * Usage:
 * <LedgerAutocomplete
 *   value={partyName}
 *   onChange={setPartyName}
 *   onSelect={(ledger) => handleLedgerSelect(ledger)}
 *   placeholder="Customer Name"
 *   ledgerType="customer"  // Optional: filter by type
 * />
 */

interface Ledger {
    id: number;
    name: string;
    group?: string;
    type?: string;
    balance?: number;
    gstin?: string;
}

interface LedgerAutocompleteProps {
    value: string;
    onChange: (value: string) => void;
    onSelect?: (ledger: Ledger | null) => void;
    placeholder?: string;
    ledgerType?: 'customer' | 'supplier' | 'bank' | 'all';
    disabled?: boolean;
    className?: string;
    showBalance?: boolean;
    debounceMs?: number;
}

export function LedgerAutocomplete({
    value,
    onChange,
    onSelect,
    placeholder = "Enter party name...",
    ledgerType,
    disabled = false,
    className = "",
    showBalance = true,
    debounceMs = 300
}: LedgerAutocompleteProps) {
    const [suggestions, setSuggestions] = useState<Ledger[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [showDropdown, setShowDropdown] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const [error, setError] = useState<string | null>(null);

    const inputRef = useRef<HTMLInputElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const debounceTimer = useRef<NodeJS.Timeout | null>(null);

    // Fetch suggestions from API
    const fetchSuggestions = useCallback(async (query: string) => {
        if (query.length < 2) {
            setSuggestions([]);
            setShowDropdown(false);
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const typeParam = ledgerType && ledgerType !== 'all' ? `&ledger_type=${ledgerType}` : '';
            const data = await api.get(`/api/ledgers/search?q=${encodeURIComponent(query)}${typeParam}&limit=10`);
            setSuggestions(data.ledgers || []);
            setShowDropdown(true);
            setSelectedIndex(-1);
        } catch (err) {
            console.error('Ledger search error:', err);
            setError('Failed to search ledgers');
            setSuggestions([]);
        } finally {
            setIsLoading(false);
        }
    }, [ledgerType]);

    // Debounced search
    useEffect(() => {
        if (debounceTimer.current) {
            clearTimeout(debounceTimer.current);
        }

        debounceTimer.current = setTimeout(() => {
            fetchSuggestions(value);
        }, debounceMs);

        return () => {
            if (debounceTimer.current) {
                clearTimeout(debounceTimer.current);
            }
        };
    }, [value, fetchSuggestions, debounceMs]);

    // Handle input change
    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newValue = e.target.value;
        onChange(newValue);

        // Clear any previous selection when typing
        if (onSelect) {
            onSelect(null);
        }
    };

    // Handle ledger selection
    const handleSelect = (ledger: Ledger) => {
        onChange(ledger.name);
        setSuggestions([]);
        setShowDropdown(false);

        if (onSelect) {
            onSelect(ledger);
        }
    };

    // Handle keyboard navigation
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!showDropdown || suggestions.length === 0) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setSelectedIndex(prev =>
                    prev < suggestions.length - 1 ? prev + 1 : prev
                );
                break;
            case 'ArrowUp':
                e.preventDefault();
                setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
                break;
            case 'Enter':
                e.preventDefault();
                if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
                    handleSelect(suggestions[selectedIndex]);
                }
                break;
            case 'Escape':
                setShowDropdown(false);
                setSelectedIndex(-1);
                break;
        }
    };

    // Close dropdown on outside click
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(e.target as Node) &&
                inputRef.current &&
                !inputRef.current.contains(e.target as Node)
            ) {
                setShowDropdown(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Format balance display
    const formatBalance = (balance?: number) => {
        if (balance === undefined || balance === null) return '';
        const absBalance = Math.abs(balance);
        const formatted = absBalance.toLocaleString('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0
        });
        return balance >= 0 ? formatted : `-${formatted}`;
    };

    return (
        <div className={`relative ${className}`}>
            {/* Input Field */}
            <div className="relative">
                <Input
                    ref={inputRef}
                    type="text"
                    value={value}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    onFocus={() => value.length >= 2 && suggestions.length > 0 && setShowDropdown(true)}
                    placeholder={placeholder}
                    disabled={disabled}
                    className={`w-full ${isLoading ? 'pr-10' : ''}`}
                />

                {/* Loading Spinner */}
                {isLoading && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                        <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                )}
            </div>

            {/* Suggestions Dropdown */}
            {showDropdown && (suggestions.length > 0 || value.length >= 2) && (
                <div
                    ref={dropdownRef}
                    className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-64 overflow-y-auto"
                >
                    {/* Existing Ledgers */}
                    {suggestions.map((ledger, index) => (
                        <div
                            key={ledger.id}
                            onClick={() => handleSelect(ledger)}
                            className={`
                px-4 py-3 cursor-pointer border-b border-gray-100 dark:border-gray-700 last:border-b-0
                hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors
                ${selectedIndex === index ? 'bg-blue-50 dark:bg-gray-700' : ''}
              `}
                        >
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className="font-medium text-gray-900 dark:text-white">
                                        {ledger.name}
                                    </div>
                                    <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
                                        {ledger.group && <span>{ledger.group}</span>}
                                        {ledger.gstin && (
                                            <Badge variant="outline" className="text-xs px-1 py-0">
                                                GST
                                            </Badge>
                                        )}
                                    </div>
                                </div>

                                {showBalance && ledger.balance !== undefined && ledger.balance !== 0 && (
                                    <div className={`text-sm font-medium ${ledger.balance >= 0 ? 'text-green-600' : 'text-red-600'
                                        }`}>
                                        {formatBalance(ledger.balance)}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* "Create New" Option */}
                    {value.length >= 2 && !suggestions.some(s =>
                        s.name.toLowerCase() === value.toLowerCase()
                    ) && (
                            <div
                                className="px-4 py-3 cursor-pointer bg-gray-50 dark:bg-gray-900 hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors border-t border-gray-200 dark:border-gray-600"
                                onClick={() => {
                                    setShowDropdown(false);
                                    // Keep the typed value - ledger will be auto-created on save
                                }}
                            >
                                <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                    </svg>
                                    <span>Create new: <strong>"{value}"</strong></span>
                                </div>
                                <div className="text-xs text-gray-500 mt-1">
                                    Ledger will be auto-created when you save
                                </div>
                            </div>
                        )}

                    {/* No Results */}
                    {suggestions.length === 0 && value.length >= 2 && !isLoading && (
                        <div className="px-4 py-3 text-gray-500 dark:text-gray-400 text-sm">
                            No existing ledgers found. Type to create new.
                        </div>
                    )}
                </div>
            )}

            {/* Error Message */}
            {error && (
                <div className="text-red-500 text-xs mt-1">{error}</div>
            )}
        </div>
    );
}

export default LedgerAutocomplete;
