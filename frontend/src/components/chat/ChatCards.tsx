/**
 * Chat Cards - Interactive UI components for KITTU chat
 * 
 * These cards provide rich, interactive experiences beyond simple text responses:
 * - Party Selector: Search and select customers/vendors
 * - Item Selector: Add products to transactions
 * - Voucher Draft: Preview and confirm voucher creation
 * - Confirmation: Approve/reject actions
 */

import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Check, X, Plus, Minus } from "lucide-react";
import { useState } from "react";

// ============================================================================
// PARTY SELECTOR CARD
// ============================================================================

interface Party {
    id?: string;
    name: string;
}

interface PartySelectorProps {
    parties: Party[];
    onSelect: (party: Party) => void;
    onCancel: () => void;
}

export function PartySelectorCard({ parties, onSelect, onCancel }: PartySelectorProps) {
    const [search, setSearch] = useState("");

    const filteredParties = parties.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <Card className="mt-4 border-[#E6E1D6] shadow-lg animate-in fade-in slide-in-from-top-4">
            <CardHeader className="bg-gradient-to-r from-[#F5F2EB] to-white pb-3">
                <CardTitle className="text-[#1A1A1A] text-lg">Select Party</CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
                <div className="relative mb-3">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                        placeholder="Search parties..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="pl-10"
                    />
                </div>
                <div className="max-h-48 overflow-y-auto space-y-2">
                    {filteredParties.length === 0 ? (
                        <p className="text-sm text-gray-500 text-center py-4">No parties found</p>
                    ) : (
                        filteredParties.map((party, idx) => (
                            <button
                                key={idx}
                                onClick={() => onSelect(party)}
                                className="w-full text-left px-4 py-2 text-sm border border-[#E6E1D6] rounded-lg hover:bg-[#F5F2EB] transition-colors"
                            >
                                {party.name}
                            </button>
                        ))
                    )}
                </div>
            </CardContent>
            <CardFooter className="bg-gray-50 justify-end">
                <Button variant="ghost" onClick={onCancel} className="text-gray-600">
                    Cancel
                </Button>
            </CardFooter>
        </Card>
    );
}

// ============================================================================
// ITEM SELECTOR CARD
// ============================================================================

interface Item {
    name: string;
    rate?: number;
}

interface SelectedItem extends Item {
    quantity: number;
}

interface ItemSelectorProps {
    items: Item[];
    onConfirm: (selectedItems: SelectedItem[]) => void;
    onCancel: () => void;
}

export function ItemSelectorCard({ items, onConfirm, onCancel }: ItemSelectorProps) {
    const [search, setSearch] = useState("");
    const [selected, setSelected] = useState<SelectedItem[]>([]);

    const filteredItems = items.filter(i =>
        i.name.toLowerCase().includes(search.toLowerCase())
    );

    const addItem = (item: Item) => {
        const existing = selected.find(s => s.name === item.name);
        if (existing) {
            setSelected(selected.map(s =>
                s.name === item.name ? { ...s, quantity: s.quantity + 1 } : s
            ));
        } else {
            setSelected([...selected, { ...item, quantity: 1 }]);
        }
    };

    const updateQuantity = (itemName: string, delta: number) => {
        setSelected(selected.map(s =>
            s.name === itemName ? { ...s, quantity: Math.max(0, s.quantity + delta) } : s
        ).filter(s => s.quantity > 0));
    };

    return (
        <Card className="mt-4 border-[#E6E1D6] shadow-lg animate-in fade-in slide-in-from-top-4">
            <CardHeader className="bg-gradient-to-r from-[#F5F2EB] to-white pb-3">
                <CardTitle className="text-[#1A1A1A] text-lg">Add Items</CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                        placeholder="Search items..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="pl-10"
                    />
                </div>

                {/* Available Items */}
                <div className="max-h-32 overflow-y-auto space-y-1">
                    {filteredItems.map((item, idx) => (
                        <button
                            key={idx}
                            onClick={() => addItem(item)}
                            className="w-full text-left px-3 py-2 text-sm border border-[#E6E1D6] rounded-lg hover:bg-[#F5F2EB] transition-colors flex justify-between items-center"
                        >
                            <span>{item.name}</span>
                            {item.rate && <span className="text-gray-500">₹{item.rate}</span>}
                        </button>
                    ))}
                </div>

                {/* Selected Items */}
                {selected.length > 0 && (
                    <div className="border-t pt-3">
                        <p className="text-xs font-semibold text-gray-600 mb-2 uppercase">Selected</p>
                        <div className="space-y-2">
                            {selected.map((item, idx) => (
                                <div key={idx} className="flex items-center justify-between bg-[#F5F2EB] px-3 py-2 rounded-lg">
                                    <span className="text-sm">{item.name}</span>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => updateQuantity(item.name, -1)}
                                            className="h-6 w-6 rounded bg-white hover:bg-gray-100 flex items-center justify-center"
                                        >
                                            <Minus className="h-3 w-3" />
                                        </button>
                                        <span className="text-sm w-8 text-center">{item.quantity}</span>
                                        <button
                                            onClick={() => updateQuantity(item.name, 1)}
                                            className="h-6 w-6 rounded bg-white hover:bg-gray-100 flex items-center justify-center"
                                        >
                                            <Plus className="h-3 w-3" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
            <CardFooter className="bg-gray-50 justify-end gap-2">
                <Button variant="ghost" onClick={onCancel} className="text-gray-600">
                    Cancel
                </Button>
                <Button
                    onClick={() => onConfirm(selected)}
                    disabled={selected.length === 0}
                    className="bg-[#D96C46] hover:bg-[#C05A35]"
                >
                    Add ({selected.length})
                </Button>
            </CardFooter>
        </Card>
    );
}

// ============================================================================
// FOLLOW-UP QUESTION CARD
// ============================================================================

interface FollowUpProps {
    question: string;
    missingSlots: string[];
    onResponse: (response: string) => void;
}

export function FollowUpCard({ question, missingSlots, onResponse }: FollowUpProps) {
    const [input, setInput] = useState("");

    const handleSubmit = () => {
        if (input.trim()) {
            onResponse(input);
            setInput("");
        }
    };

    return (
        <Card className="mt-4 border-[#E6E1D6] shadow-lg animate-in fade-in slide-in-from-top-4">
            <CardHeader className="bg-gradient-to-r from-[#FFF5F0] to-white pb-3">
                <CardTitle className="text-[#1A1A1A] text-lg flex items-center gap-2">
                    <span className="text-2xl">💬</span>
                    <span>I need more info</span>
                </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
                <p className="text-[#282828] mb-3">{question}</p>
                <Input
                    placeholder="Your answer..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                    className="border-[#E6E1D6]"
                />
                {missingSlots.length > 1 && (
                    <p className="text-xs text-gray-500 mt-2">
                        Still needed: {missingSlots.slice(1).join(", ")}
                    </p>
                )}
            </CardContent>
            <CardFooter className="bg-gray-50 justify-end">
                <Button
                    onClick={handleSubmit}
                    disabled={!input.trim()}
                    className="bg-[#D96C46] hover:bg-[#C05A35]"
                >
                    Submit
                </Button>
            </CardFooter>
        </Card>
    );
}
