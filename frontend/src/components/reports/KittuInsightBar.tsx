"use client";

import { Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useState } from "react";

export function KittuInsightBar({ context }: { context: string }) {
    const [query, setQuery] = useState("");

    const suggestions = [
        "Why is net profit down?",
        "Show top expense categories",
        "Compare with last quarter"
    ];

    return (
        <div className="bg-gradient-to-r from-primary/5 via-primary/10 to-transparent rounded-lg border border-primary/20 p-1 flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 md:border-r border-primary/20 min-w-fit">
                <div className="h-6 w-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center">
                    <Sparkles className="h-3.5 w-3.5" />
                </div>
                <span className="text-sm font-semibold text-primary hidden md:inline-block">KITTU Insights</span>
            </div>

            <div className="flex-1 flex items-center gap-2 px-2">
                <Input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="h-8 border-none bg-transparent shadow-none focus-visible:ring-0 placeholder:text-muted-foreground/70"
                    placeholder={`Ask about ${context}...`}
                />
            </div>

            <div className="hidden lg:flex items-center gap-2 pr-2">
                {suggestions.map((s, i) => (
                    <button
                        key={i}
                        onClick={() => setQuery(s)}
                        className="text-xs px-2 py-1 rounded bg-background/50 hover:bg-background border border-transparent hover:border-border transition-colors text-muted-foreground trancate max-w-[150px]"
                    >
                        {s}
                    </button>
                ))}
            </div>

            <Button size="icon" className="h-8 w-8 rounded-md shrink-0">
                <ArrowRight className="h-4 w-4" />
            </Button>
        </div>
    );
}
