"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { apiRequest } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface SearchResults {
    ledgers: any[];
    items: any[];
    vouchers: any[];
}

function SearchContent() {
    const searchParams = useSearchParams();
    const query = searchParams.get("q");
    const [results, setResults] = useState<SearchResults>({ ledgers: [], items: [], vouchers: [] });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (query) {
            setLoading(true);
            apiRequest(`/search?q=${query}`)
                .then(data => {
                    setResults({
                        ledgers: data.ledgers || [],
                        items: data.items || [],
                        vouchers: data.vouchers || []
                    });
                    setLoading(false);
                })
                .catch(err => {
                    console.error("Search failed:", err);
                    setLoading(false);
                });
        }
    }, [query]);

    if (!query) return <div className="p-8">Please enter a search term.</div>;
    if (loading) return <div className="p-8">Searching for "{query}"...</div>;

    return (
        <div className="p-8 space-y-8">
            <div>
                <h1 className="text-3xl font-bold">Search Results</h1>
                <p className="text-muted-foreground">Found {results.ledgers.length + results.items.length + results.vouchers.length} results for "{query}"</p>
            </div>

            {/* Ledgers Section */}
            {results.ledgers.length > 0 && (
                <section>
                    <h2 className="text-xl font-semibold mb-4">Parties & Ledgers</h2>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {results.ledgers.map((ledger: any) => (
                            <Card key={ledger.id}>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg">{ledger.name}</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-sm text-muted-foreground">{ledger.parent}</p>
                                    <p className="font-bold mt-2">
                                        Closing: ₹{ledger.closing_balance?.toLocaleString('en-IN') || 0}
                                    </p>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </section>
            )}

            {/* Items Section */}
            {results.items.length > 0 && (
                <section>
                    <h2 className="text-xl font-semibold mb-4">Stock Items</h2>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {results.items.map((item: any) => (
                            <Card key={item.id}>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg">{item.name}</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-sm text-muted-foreground">{item.parent}</p>
                                    <div className="flex justify-between mt-2 font-bold">
                                        <span>{item.closing_balance} {item.units}</span>
                                        <span>₹{item.rate}/-</span>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </section>
            )}

            {/* Vouchers Section */}
            {results.vouchers.length > 0 && (
                <section>
                    <h2 className="text-xl font-semibold mb-4">Transactions</h2>
                    <div className="grid gap-4">
                        {results.vouchers.map((voucher: any) => (
                            <Card key={voucher.id}>
                                <CardContent className="p-4 flex justify-between items-center">
                                    <div>
                                        <div className="font-semibold">{voucher.party_name}</div>
                                        <div className="text-sm text-muted-foreground">
                                            {voucher.voucher_type} #{voucher.voucher_number} • {new Date(voucher.date).toLocaleDateString()}
                                        </div>
                                    </div>
                                    <div className="font-bold">₹{voucher.amount.toLocaleString('en-IN')}</div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </section>
            )}

            {results.ledgers.length === 0 && results.items.length === 0 && results.vouchers.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                    No results found. Try a different search term.
                </div>
            )}
        </div>
    );
}

export default function SearchPage() {
    return (
        <Suspense fallback={<div className="p-8">Loading search...</div>}>
            <SearchContent />
        </Suspense>
    );
}
